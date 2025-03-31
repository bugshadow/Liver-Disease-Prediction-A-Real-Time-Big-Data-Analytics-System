from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, from_json
from pyspark.sql.types import StructType, StructField, IntegerType, StringType, FloatType
from pyspark.ml.classification import RandomForestClassificationModel
from pyspark.ml.feature import VectorAssembler, StandardScaler
import sys

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

# Préparation des résultats avec diagnostic
output_df = predictions.select(
    col("Age"), col("Gender"), col("Total_Bilirubin"), col("Direct_Bilirubin"), col("Alkphos"),
    col("Sgpt"), col("Sgot"), col("Total_Proteins"), col("Albumin"), col("A_G_Ratio"),
    col("Result"), col("prediction"),
    when(col("prediction") == 1, "Malade du foie").otherwise("Non malade du foie").alias("diagnosis")
)

# Fonction pour afficher avec couleurs et messages explicites
def print_predictions(batch_df, batch_id):
    for row in batch_df.collect():
        if row["prediction"] == 1:
            print(f"{Colors.RED}Patient MALADE DU FOIE (prediction=1): Age={row['Age']}, Gender={row['Gender']}, Diagnosis={row['diagnosis']}{Colors.RESET}")
        else:
            print(f"{Colors.GREEN}Patient NON MALADE (prediction=0): Age={row['Age']}, Gender={row['Gender']}, Diagnosis={row['diagnosis']}{Colors.RESET}")

# Sauvegarde locale des prédictions
query_file = output_df.writeStream \
    .outputMode("append") \
    .format("csv") \
    .option("path", "file:///root/BigData_Project/predictions_local") \
    .option("checkpointLocation", "/tmp/kafka-checkpoints-file") \
    .trigger(processingTime="10 seconds") \
    .start()

# Affichage en console avec couleurs
query_console = output_df.writeStream \
    .outputMode("append") \
    .foreachBatch(print_predictions) \
    .trigger(processingTime="10 seconds") \
    .option("checkpointLocation", "/tmp/kafka-checkpoints-console") \
    .start()

# Attendre la fin des deux streams
query_file.awaitTermination()
query_console.awaitTermination()
