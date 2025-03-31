from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, mean
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.sql.types import StructType, StructField, IntegerType, StringType, FloatType

# 1. Initialisation de la session Spark en mode local
spark = SparkSession.builder \
    .appName("Pandemic Data Preparation") \
    .master("local[*]") \
    .getOrCreate()

# 2. Définition du schéma pour le dataset
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

# 3. Chargement des données depuis le système de fichiers local
df = spark.read.csv("file:///root/BigData_Project/liver_dataset_train.csv", 
                    schema=schema, 
                    header=True)

# 4. Nettoyage des données
numeric_columns = ["Total_Bilirubin", "Direct_Bilirubin", "Alkphos", "Sgpt", "Sgot", 
                  "Total_Proteins", "Albumin", "A_G_Ratio"]

for column in numeric_columns:
    mean_val = df.select(mean(col(column)).alias("mean")).collect()[0]["mean"]
    df = df.fillna({column: mean_val})

df = df.withColumn("Gender_numeric", when(col("Gender") == "Female", 0).otherwise(1))

# 5. Sélection des features pour le modèle
feature_columns = ["Age", "Gender_numeric", "Total_Bilirubin", "Direct_Bilirubin", 
                  "Alkphos", "Sgpt", "Sgot", "Total_Proteins", "Albumin", "A_G_Ratio"]

# 6. Création d'un vecteur de features avec VectorAssembler
assembler = VectorAssembler(inputCols=feature_columns, outputCol="features_raw", 
                           handleInvalid="skip")
df_features = assembler.transform(df)

# 7. Normalisation des features avec StandardScaler
scaler = StandardScaler(inputCol="features_raw", outputCol="features_scaled",
                       withStd=True, withMean=True)
scaler_model = scaler.fit(df_features)
df_scaled = scaler_model.transform(df_features)

# 8. Sélection finale des colonnes pour le modèle
final_df = df_scaled.select("features_scaled", "Result")

# 9. Affichage du résultat (optionnel pour vérification)
final_df.show(truncate=False)

# 10. Sauvegarde des données préparées localement en Parquet
final_df.write.mode("overwrite") \
    .parquet("file:///root/BigData_Project/prepared_data")

# Arrêt de la session Spark
spark.stop()
