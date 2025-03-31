from kafka import KafkaProducer
import json
import time
import random

# Configuration du broker Kafka
KAFKA_BROKER = "localhost:9092"  # Remplacez par l'adresse correcte si nécessaire (ex. hadoop-master:9092)

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Plages de valeurs basées sur votre dataset
AGE_RANGE = (17, 74)  # Min et max observés
GENDER_OPTIONS = ["Male", "Female"]
TOTAL_BILIRUBIN_RANGE = (0.6, 10.9)
DIRECT_BILIRUBIN_RANGE = (0.1, 5.5)
ALKPHOS_RANGE = (145, 699)
SGPT_RANGE = (14, 168)  # Certaines valeurs manquantes, min/max ajustés
SGOT_RANGE = (11, 441)
TOTAL_PROTEINS_RANGE = (5.5, 8.1)
ALBUMIN_RANGE = (2.3, 4.4)
A_G_RATIO_RANGE = (0.4, 1.3)
RESULT_OPTIONS = [1, 2]  # Résultat binaire

# Boucle infinie pour générer et envoyer des données
while True:
    liver_data = {
        "Age": random.randint(AGE_RANGE[0], AGE_RANGE[1]),
        "Gender": random.choice(GENDER_OPTIONS),
        "Total_Bilirubin": round(random.uniform(TOTAL_BILIRUBIN_RANGE[0], TOTAL_BILIRUBIN_RANGE[1]), 1),
        "Direct_Bilirubin": round(random.uniform(DIRECT_BILIRUBIN_RANGE[0], DIRECT_BILIRUBIN_RANGE[1]), 1),
        "Alkphos": random.randint(ALKPHOS_RANGE[0], ALKPHOS_RANGE[1]),
        "Sgpt": random.randint(SGPT_RANGE[0], SGPT_RANGE[1]),
        "Sgot": random.randint(SGOT_RANGE[0], SGOT_RANGE[1]),
        "Total_Proteins": round(random.uniform(TOTAL_PROTEINS_RANGE[0], TOTAL_PROTEINS_RANGE[1]), 1),
        "Albumin": round(random.uniform(ALBUMIN_RANGE[0], ALBUMIN_RANGE[1]), 1),
        "A_G_Ratio": round(random.uniform(A_G_RATIO_RANGE[0], A_G_RATIO_RANGE[1]), 1),
        "Result": random.choice(RESULT_OPTIONS)
    }
    
    # Envoi dans le topic Kafka
    producer.send('liver-data', value=liver_data)
    print(f"Envoi: {liver_data}")
    
    # Pause pour simuler un flux en temps réel
    time.sleep(1)

# Note : Ce script tourne indéfiniment. Utilisez Ctrl+C pour l'arrêter.
