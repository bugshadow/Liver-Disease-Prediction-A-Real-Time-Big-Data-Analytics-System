from pyspark.sql import SparkSession
from pyspark.ml.classification import RandomForestClassificationModel
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.sql.functions import col, when
from pyspark.sql.types import StructType, StructField, IntegerType, StringType, FloatType

# 1. Initialisation de la session Spark en mode local
spark = SparkSession.builder \
    .appName("Prediction with Saved RandomForest Model") \
    .master("local[*]") \
    .getOrCreate()

# 2. Définition du schéma pour la nouvelle ligne de données
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

# 3. Création d'un DataFrame avec la nouvelle ligne
new_data = [(62, "Male", 7.3, 4.1, 490, 60, 68, 7.0, 3.3, 0.89, 1)]
new_df = spark.createDataFrame(new_data, schema=schema)

# 4. Chargement des données préparées pour récupérer les moyennes et le scaler
prepared_data = spark.read.parquet("file:///root/BigData_Project/prepared_data")
original_data = spark.read.csv("file:///root/BigData_Project/liver_dataset_train.csv", schema=schema, header=True)

# 5. Nettoyage des données (remplissage des valeurs manquantes avec les moyennes du dataset original)
numeric_columns = ["Total_Bilirubin", "Direct_Bilirubin", "Alkphos", "Sgpt", "Sgot", 
                  "Total_Proteins", "Albumin", "A_G_Ratio"]

for column in numeric_columns:
    mean_val = original_data.select(col(column)).agg({"*": "mean"}).collect()[0][0]
    new_df = new_df.fillna({column: mean_val})
    original_data = original_data.fillna({column: mean_val})

# Conversion de Gender en numérique pour new_df et original_data
new_df = new_df.withColumn("Gender_numeric", when(col("Gender") == "Female", 0).otherwise(1))
original_data = original_data.withColumn("Gender_numeric", when(col("Gender") == "Female", 0).otherwise(1))

# 6. Sélection des features pour le modèle
feature_columns = ["Age", "Gender_numeric", "Total_Bilirubin", "Direct_Bilirubin", 
                  "Alkphos", "Sgpt", "Sgot", "Total_Proteins", "Albumin", "A_G_Ratio"]

# 7. Création du vecteur de features avec VectorAssembler
assembler = VectorAssembler(inputCols=feature_columns, outputCol="features_raw", handleInvalid="skip")
new_df_assembled = assembler.transform(new_df)
original_data_assembled = assembler.transform(original_data)

# 8. Normalisation des features avec StandardScaler
scaler = StandardScaler(inputCol="features_raw", outputCol="features_scaled", withStd=True, withMean=True)
scaler_model = scaler.fit(original_data_assembled)
new_df_scaled = scaler_model.transform(new_df_assembled)

# 9. Chargement du modèle sauvegardé
model_path = "file:///root/BigData_Project/best_model_randomforest"
rf_model = RandomForestClassificationModel.load(model_path)

# 10. Prédiction sur la nouvelle ligne
prediction = rf_model.transform(new_df_scaled)

# 11. Affichage du résultat dans le terminal
print("Nouvelle ligne après prétraitement :")
new_df_scaled.select("features_scaled", "Result").show(truncate=False)
print("Prédiction :")
prediction.select("features_scaled", "Result", "prediction").show(truncate=False)

# 12. Extraction de la prédiction
pred_value = prediction.select("prediction").collect()[0][0]
diagnosis = "Malade du foie" if pred_value == 1 else "Non malade du foie"

# 13. Sauvegarde du résultat dans un fichier texte
output_file = "/root/BigData_Project/prediction_result.txt"
with open(output_file, "w") as f:
    f.write(f"Données d'entrée : {new_data[0]}\n")
    f.write(f"Prédiction du modèle : {pred_value}\n")
    f.write(f"Diagnostic : {diagnosis}\n")
    f.write(f"Resultat fourni (pour vérification) : {new_data[0][-1]}\n")

print(f"Résultat sauvegardé dans '{output_file}'")

# Arrêt de la session Spark
spark.stop()
