from pyspark.sql import SparkSession
from pyspark.ml.classification import RandomForestClassifier, LogisticRegression, DecisionTreeClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.sql.functions import col, when

# Codes ANSI pour les couleurs dans le terminal
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"

# 1. Initialisation de la session Spark en mode local
spark = SparkSession.builder \
    .appName("Comparison of ML Models for Liver Disease") \
    .master("local[*]") \
    .getOrCreate()

# 2. Chargement des données préparées
data = spark.read.parquet("file:///root/BigData_Project/prepared_data")

# 3. Vérification des valeurs uniques dans la colonne Result
print(f"{BLUE}Vérification des valeurs uniques dans 'Result' :{RESET}")
data.groupBy("Result").count().show()

# 4. Transformation des labels pour garantir {0, 1} (si nécessaire)
# Hypothèse : Si Result contient 2, on le convertit en 0 (ajustez selon vos données)
data = data.withColumn("Result", when(col("Result") == 2, 0).otherwise(col("Result")))
print(f"{BLUE}Labels corrigés pour être en {0, 1} :{RESET}")
data.groupBy("Result").count().show()

# 5. Séparation en ensembles d'entraînement et de test (70% train, 30% test)
train_data, test_data = data.randomSplit([0.7, 0.3], seed=42)

# 6. Liste des modèles à entraîner (sans GradientBoostedTrees)
models = [
    ("RandomForest", RandomForestClassifier(labelCol="Result", featuresCol="features_scaled", numTrees=100, maxDepth=30, seed=42)),
    ("LogisticRegression", LogisticRegression(labelCol="Result", featuresCol="features_scaled", maxIter=100)),
    ("DecisionTree", DecisionTreeClassifier(labelCol="Result", featuresCol="features_scaled", maxDepth=30, seed=42))
]

# 7. Évaluateur pour mesurer l'accuracy
evaluator = MulticlassClassificationEvaluator(
    labelCol="Result",
    predictionCol="prediction",
    metricName="accuracy"
)

# 8. Dictionnaire pour stocker les résultats
results = {}

# 9. Entraînement et évaluation de chaque modèle
for model_name, model in models:
    print(f"{BLUE}Entraînement du modèle : {model_name}{RESET}")
    
    # Entraînement
    trained_model = model.fit(train_data)
    
    # Prédictions
    train_predictions = trained_model.transform(train_data)
    test_predictions = trained_model.transform(test_data)
    
    # Calcul des accuracies
    train_accuracy = evaluator.evaluate(train_predictions)
    test_accuracy = evaluator.evaluate(test_predictions)
    
    # Stockage des résultats
    results[model_name] = {
        "train_accuracy": train_accuracy,
        "test_accuracy": test_accuracy,
        "gap": train_accuracy - test_accuracy
    }
    
    # Affichage immédiat des résultats
    print(f"{GREEN}Accuracy sur entraînement ({model_name}) : {train_accuracy:.4f}{RESET}")
    print(f"{BLUE}Accuracy sur test ({model_name}) : {test_accuracy:.4f}{RESET}")
    if train_accuracy - test_accuracy > 0.1:
        print(f"{RED}Attention : Possible overfitting détecté pour {model_name} (écart > 10%).{RESET}")
    else:
        print(f"{GREEN}Pas de signe évident d'overfitting pour {model_name}.{RESET}")
    print("---")

# 10. Identification du meilleur modèle (basé sur l'accuracy de test)
best_model_name = max(results, key=lambda k: results[k]["test_accuracy"])
best_test_accuracy = results[best_model_name]["test_accuracy"]

# 11. Sauvegarde des résultats dans un fichier
output_file = "/root/BigData_Project/model_comparison.txt"
with open(output_file, "w") as f:
    f.write("Comparaison des modèles\n")
    f.write("====================\n\n")
    for model_name, metrics in results.items():
        f.write(f"Modèle : {model_name}\n")
        f.write(f"Accuracy sur entraînement : {metrics['train_accuracy']:.4f}\n")
        f.write(f"Accuracy sur test : {metrics['test_accuracy']:.4f}\n")
        f.write(f"Écart : {metrics['gap']:.4f}\n")
        if metrics["gap"] > 0.1:
            f.write("Résultat : Possible overfitting détecté (écart > 10%).\n")
        else:
            f.write("Résultat : Pas de signe évident d'overfitting.\n")
        f.write("---\n")
    f.write("\nMeilleur modèle basé sur l'accuracy de test :\n")
    f.write(f"Modèle : {best_model_name}\n")
    f.write(f"Accuracy sur test : {best_test_accuracy:.4f}\n")

print(f"{BLUE}Résultats sauvegardés dans '{output_file}'{RESET}")

# 12. Sauvegarde du meilleur modèle (optionnel)
for model_name, model in models:
    if model_name == best_model_name:
        trained_model = model.fit(train_data)  # Réentraîner pour sauvegarde
        trained_model.write().overwrite().save(f"file:///root/BigData_Project/best_model_{model_name.lower()}")
        print(f"{GREEN}Meilleur modèle ({model_name}) sauvegardé dans 'best_model_{model_name.lower()}'{RESET}")

# Arrêt de la session Spark
spark.stop()
