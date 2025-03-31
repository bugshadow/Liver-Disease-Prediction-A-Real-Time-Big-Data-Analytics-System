from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, from_json
from pyspark.sql.types import StructType, StructField, IntegerType, StringType, FloatType
from pyspark.ml.classification import RandomForestClassificationModel
from pyspark.ml.feature import VectorAssembler, StandardScaler
import sys
import logging
from tabulate import tabulate

# Désactiver les logs Spark dans la console
logging.getLogger('pyspark').setLevel(logging.ERROR)  # N'afficher que les erreurs critiques
logging.getLogger('org.apache.spark').setLevel(logging.ERROR)  # Désactiver les logs Spark
logging.getLogger('kafka').setLevel(logging.ERROR)  # Désactiver les logs Kafka

# Rediriger les logs Spark vers /dev/null (pas de sortie console)
handler = logging.StreamHandler(open('/dev/null', 'w'))  # Sous Linux/Unix
# Si sous Windows, utilisez : handler = logging.StreamHandler(open('nul', 'w'))
handler.setLevel(logging.ERROR)
logging.getLogger('pyspark').addHandler(handler)
logging.getLogger('org.apache.spark').addHandler(handler)
logging.getLogger('kafka').addHandler(handler)

# Configuration du logging personnalisé dans un fichier
log_file = "/root/BigData_Project/prediction_logs.txt"
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LiverPredictionLogger")

# Pour ajouter des couleurs dans la console
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    RESET = '\033[0m'

# Initialisation de la session Spark avec Kafka
spark = SparkSession.builder \
    .appName("RealTimeLiverPredictionWithKafka") \
    .master("local[*]") \
    .config("spark.sql.streaming.checkpointLocation", "/tmp/spark-checkpoints") \
    .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
    .getOrCreate()

# Schéma des données Kafka
schema = StructType([
    StructField("Age", IntegerType(), True),
    StructField("Gender", StringType(), True),
    StructField("Total_Bilirubin", FloatType(), True),
    StructField("Direct_Bilirubin", FloatType(), True),
    StructField("Alkphos", IntegerType(), True),
    StructField("Sgpt", IntegerType(), True),
    StructField("Sgot", IntegerType(), True),
    StructField("Total_Proteins", FloatType(), True),
    StructField("Albumin", FloatType(), True),
    StructField("A_G_Ratio", FloatType(), True),
    StructField("Result", IntegerType(), True)
])

# Lecture du flux Kafka
df_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "liver-data") \
    .option("failOnDataLoss", "false") \
    .load()

# Conversion des données Kafka
df_stream = df_stream.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.*")

# Chargement des données historiques (local)
original_data = spark.read.csv("file:///root/BigData_Project/liver_dataset_train.csv", schema=schema, header=True)

# Nettoyage et transformations
numeric_columns = ["Total_Bilirubin", "Direct_Bilirubin", "Alkphos", "Sgpt", "Sgot", "Total_Proteins", "Albumin", "A_G_Ratio"]
for column in numeric_columns:
    mean_val = original_data.select(col(column)).agg({"*": "mean"}).collect()[0][0]
    df_stream = df_stream.fillna({column: mean_val})
    original_data = original_data.fillna({column: mean_val})

df_stream = df_stream.withColumn("Gender_numeric", when(col("Gender") == "Female", 0).otherwise(1))
original_data = original_data.withColumn("Gender_numeric", when(col("Gender") == "Female", 0).otherwise(1))

feature_columns = ["Age", "Gender_numeric", "Total_Bilirubin", "Direct_Bilirubin", "Alkphos", "Sgpt", "Sgot", "Total_Proteins", "Albumin", "A_G_Ratio"]
assembler = VectorAssembler(inputCols=feature_columns, outputCol="features_raw", handleInvalid="skip")
df_stream_assembled = assembler.transform(df_stream)
original_data_assembled = assembler.transform(original_data)

scaler = StandardScaler(inputCol="features_raw", outputCol="features_scaled", withStd=True, withMean=True)
scaler_model = scaler.fit(original_data_assembled)
df_stream_scaled = scaler_model.transform(df_stream_assembled)

# Chargement du modèle (local)
model_path = "file:///root/BigData_Project/best_model_randomforest"
rf_model = RandomForestClassificationModel.load(model_path)

# Prédiction
predictions = rf_model.transform(df_stream_scaled)

# Préparation des résultats avec diagnostic (1 = non malade, 2 = malade)
output_df = predictions.select(
    col("Age"), col("Gender"), col("Total_Bilirubin"), col("Direct_Bilirubin"), col("Alkphos"),
    col("Sgpt"), col("Sgot"), col("Total_Proteins"), col("Albumin"), col("A_G_Ratio"),
    col("Result"), col("prediction"),
    when(col("prediction") == 2, "Malade du foie").otherwise("Non malade du foie").alias("diagnosis")
)

# Fonction pour écrire dans PostgreSQL et retourner le statut
def write_to_postgres(batch_df, batch_id):
    try:
        for row in batch_df.collect():
            log_message = (f"Batch {batch_id} - Data to write: Age={row['Age']}, Gender={row['Gender']}, "
                           f"Total_Bilirubin={row['Total_Bilirubin']}, Direct_Bilirubin={row['Direct_Bilirubin']}, "
                           f"Alkphos={row['Alkphos']}, Sgpt={row['Sgpt']}, Sgot={row['Sgot']}, "
                           f"Total_Proteins={row['Total_Proteins']}, Albumin={row['Albumin']}, "
                           f"A_G_Ratio={row['A_G_Ratio']}, Result={row['Result']}, Prediction={row['prediction']}, "
                           f"Diagnosis={row['diagnosis']}")
            logger.info(log_message)

        batch_df.write \
            .format("jdbc") \
            .option("url", "jdbc:postgresql://localhost:5432/liver_db") \
            .option("dbtable", "predictions") \
            .option("user", "postgres") \
            .option("password", "omarbh") \
            .option("driver", "org.postgresql.Driver") \
            .mode("append") \
            .save()

        logger.info(f"Batch {batch_id} - Successfully written to PostgreSQL")
        return True
    except Exception as e:
        logger.error(f"Batch {batch_id} - Error writing to PostgreSQL: {str(e)}")
        return False

# Fonction pour afficher les prédictions dans un tableau avec tabulate
def print_predictions(batch_df, batch_id):
    # Écrire dans PostgreSQL et obtenir le statut
    postgres_success = write_to_postgres(batch_df, batch_id)
    status_msg = f"{Colors.GREEN}Saved{Colors.RESET}" if postgres_success else f"{Colors.RED}Failed{Colors.RESET}"

    # Récupérer les lignes du batch
    rows = batch_df.collect()
    if not rows:
        print(f"Batch {batch_id}: No data to display")
        return

    # Préparer les données pour le tableau
    table_data = []
    for row in rows:
        color = Colors.RED if row["prediction"] == 2 else Colors.GREEN  # 2 = malade, 1 = non malade
        table_data.append([
            f"{color}{row['Age']}{Colors.RESET}",
            f"{color}{row['Gender']}{Colors.RESET}",
            f"{color}{row['prediction']}{Colors.RESET}",
            f"{color}{row['diagnosis']}{Colors.RESET}",
            status_msg
        ])

    # Définir les en-têtes
    headers = ["Age", "Gender", "Prediction", "Diagnosis", "PostgreSQL Status"]

    # Afficher le tableau avec tabulate
    print(f"\nBatch {batch_id} Predictions:")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

# Sauvegarde locale des prédictions (CSV)
query_file = output_df.writeStream \
    .outputMode("append") \
    .format("csv") \
    .option("path", "file:///root/BigData_Project/predictions_local") \
    .option("checkpointLocation", "/tmp/kafka-checkpoints-file") \
    .trigger(processingTime="10 seconds") \
    .start()

# Affichage en console avec tableau
query_console = output_df.writeStream \
    .outputMode("append") \
    .foreachBatch(print_predictions) \
    .option("checkpointLocation", "/tmp/kafka-checkpoints-console") \
    .trigger(processingTime="10 seconds") \
    .start()

# Attendre la fin des streams
query_file.awaitTermination()
query_console.awaitTermination()
