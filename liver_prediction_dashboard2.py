import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import time
import os
import json
from kafka import KafkaConsumer
from datetime import datetime
from collections import deque
import base64

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Tableau de Bord Galactique : Prédictions et Kafka",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS pour un design futuriste et spectaculaire
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');
    .main {
        background: linear-gradient(145deg, #0a0a23 0%, #1a1a3d 100%);
        font-family: 'Orbitron', sans-serif;
        color: #e0e0ff;
        overflow: hidden;
        position: relative;
    }
    .sidebar .sidebar-content {
        background: #0a0a23;
        color: #e0e0ff;
        box-shadow: 0 0 20px rgba(255, 46, 99, 0.3);
    }
    .stButton>button {
        background: linear-gradient(45deg, #ff006e, #8338ec);
        color: #FFFFFF;
        border-radius: 25px;
        padding: 12px 30px;
        font-weight: 700;
        border: none;
        transition: all 0.4s ease;
        box-shadow: 0 5px 15px rgba(255, 0, 110, 0.5);
        animation: glowButton 1.5s infinite alternate;
    }
    .stButton>button:hover {
        transform: scale(1.1) translateY(-5px);
        box-shadow: 0 10px 25px rgba(255, 0, 110, 0.8);
    }
    .title {
        color: #ff006e;
        font-size: 60px;
        font-weight: 700;
        text-align: center;
        text-shadow: 0 0 20px rgba(255, 0, 110, 0.8), 0 0 40px rgba(255, 0, 110, 0.5);
        animation: neonGlow 1.5s infinite alternate;
    }
    .subtitle {
        color: #a0a0cc;
        font-size: 26px;
        text-align: center;
        margin-bottom: 40px;
        animation: fadeIn 2s ease-in-out;
    }
    @keyframes neonGlow {
        from { text-shadow: 0 0 10px #ff006e, 0 0 20px #ff006e; }
        to { text-shadow: 0 0 20px #ff006e, 0 0 40px #ff006e; }
    }
    @keyframes glowButton {
        from { box-shadow: 0 5px 15px rgba(255, 0, 110, 0.5); }
        to { box-shadow: 0 10px 25px rgba(255, 0, 110, 0.8); }
    }
    @keyframes fadeIn {
        0% { opacity: 0; transform: translateY(-20px); }
        100% { opacity: 1; transform: translateY(0); }
    }
    .metric-card {
        background: rgba(20, 20, 40, 0.9);
        padding: 25px;
        border-radius: 20px;
        box-shadow: 0 5px 20px rgba(255, 0, 110, 0.3);
        text-align: center;
        border: 2px solid #ff006e;
        transition: all 0.3s ease;
    }
    .metric-card:hover {
        transform: scale(1.08);
        box-shadow: 0 10px 30px rgba(255, 0, 110, 0.5);
    }
    .download-btn {
        background: linear-gradient(45deg, #3a86ff, #00d4ff);
        color: #FFFFFF !important;
        padding: 12px 25px;
        border-radius: 15px;
        text-decoration: none;
        display: inline-block;
        margin-top: 15px;
        transition: all 0.3s ease;
    }
    .download-btn:hover {
        background: linear-gradient(45deg, #2a6fd6, #00b4d8);
        transform: scale(1.05);
    }
    .section-header {
        color: #8338ec;
        font-size: 32px;
        text-shadow: 0 0 10px rgba(131, 56, 236, 0.5);
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# Chemins et configurations
PREDICTIONS_PATH = "/root/BigData_Project/predictions_local"
KAFKA_TOPIC = "liver-data"
KAFKA_BROKER = "localhost:9092"

# Initialisation du consommateur Kafka
consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    auto_offset_reset="earliest",
    value_deserializer=lambda x: None if not x else json.loads(x.decode('utf-8', errors='ignore')),
    consumer_timeout_ms=1000
)

# Cache pour les données Kafka (limité à 100 entrées)
kafka_cache = deque(maxlen=100)

# Fonction pour charger les prédictions Spark
def load_latest_predictions():
    files = list(Path(PREDICTIONS_PATH).glob("part-*.csv"))
    if not files:
        return pd.DataFrame()
    latest_file = max(files, key=os.path.getctime)
    df = pd.read_csv(latest_file, header=None, names=[
        "Age", "Gender", "Total_Bilirubin", "Direct_Bilirubin", "Alkphos",
        "Sgpt", "Sgot", "Total_Proteins", "Albumin", "A_G_Ratio", "Result",
        "prediction", "diagnosis"
    ])
    return df

# Fonction pour mettre à jour le cache Kafka
def update_kafka_cache():
    try:
        for message in consumer:
            if message.value is not None:
                kafka_cache.append(message.value)
            if len(kafka_cache) >= kafka_cache.maxlen:
                break
    except Exception as e:
        st.error(f"Erreur Kafka : {str(e)}")
    return pd.DataFrame(list(kafka_cache)) if kafka_cache else pd.DataFrame()

# Fonction pour générer un lien de téléchargement CSV
def get_csv_download_link(df, filename):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}" class="download-btn">Télécharger {filename}</a>'
    return href

# Sidebar pour les filtres et options
with st.sidebar:
    st.header("Commandes Galactiques")
    age_range = st.slider("Âge", 0, 100, (17, 74), key="age_slider")
    gender_filter = st.multiselect("Genre", ["Male", "Female"], default=["Male", "Female"], key="gender_filter")
    diagnosis_filter = st.multiselect("Diagnostic", ["Malade du foie", "Non malade du foie"], default=["Malade du foie", "Non malade du foie"], key="diagnosis_filter")

# Titre et sous-titre animés
st.markdown('<div class="title">Tableau de Bord Galactique</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Exploration Dynamique en Temps Réel</div>', unsafe_allow_html=True)

# Conteneur principal
placeholder = st.empty()

# Compteur pour clés uniques
iteration = 0

# Options de visualisations
vis_options = {
    "Donut": "Graphique en Anneau",
    "Area": "Aire Empilée",
    "Radar": "Radar",
    "Funnel": "Entonnoir",
    "Scatter": "Dispersion Animée",
    "Bar": "Barres Empilées",
    "Box": "Boîte",
    "Violin": "Violon",
    "Treemap": "Treemap"
}

# Boucle de mise à jour en temps réel
while True:
    iteration += 1
    with placeholder.container():
        # Initialisation d'un cache pour suivre les valeurs précédentes
        if "prev_total" not in st.session_state:
            st.session_state.prev_total = 0
        if "prev_sick" not in st.session_state:
            st.session_state.prev_sick = 0

        # Charger les données
        df_predictions = load_latest_predictions()
        df_kafka = update_kafka_cache()

        # Section 1 : Prédictions Spark Streaming
        st.markdown('<div class="section-header">Prédictions Spark</div>', unsafe_allow_html=True)
        if not df_predictions.empty:
            df_pred_filtered = df_predictions[
                (df_predictions["Age"].between(age_range[0], age_range[1])) &
                (df_predictions["Gender"].isin(gender_filter)) &
                (df_predictions["diagnosis"].isin(diagnosis_filter))
            ]

            # Intégrer les données Kafka si disponibles
            if not df_kafka.empty:
                kafka_subset = df_kafka[["Age", "Gender", "Total_Bilirubin", "Direct_Bilirubin", "Alkphos", "Sgpt", "Sgot", "Total_Proteins", "Albumin", "A_G_Ratio"]]
                kafka_subset["Result"] = 1  # Valeur par défaut (à ajuster selon votre logique)
                kafka_subset["prediction"] = 1  # Valeur par défaut
                kafka_subset["diagnosis"] = kafka_subset["prediction"].apply(lambda x: "Non malade du foie" if x == 1 else "malade du foie")
                df_pred_filtered = pd.concat([df_pred_filtered, kafka_subset], ignore_index=True)

            # Calcul des métriques
            total_pred = len(df_pred_filtered)
            sick_pred = len(df_pred_filtered[df_pred_filtered["diagnosis"] == "Malade du foie"])

            # Calcul des deltas par rapport aux valeurs précédentes
            delta_total = total_pred - st.session_state.prev_total
            delta_sick = sick_pred - st.session_state.prev_sick

            # Mise à jour des valeurs précédentes
            st.session_state.prev_total = total_pred
            st.session_state.prev_sick = sick_pred

            # Sélection des visualisations pour Spark
            spark_vis = st.multiselect("Choisir les visualisations Spark", list(vis_options.values()), default=["Graphique en Anneau", "Aire Empilée", "Radar"], key=f"spark_vis_{iteration}")
            col1, col2, col3 = st.columns(3)

            for i, vis in enumerate(spark_vis[:3]):  # Limité à 3 pour la mise en page
                with [col1, col2, col3][i]:
                    if vis == "Graphique en Anneau":
                        diagnosis_counts = df_pred_filtered["diagnosis"].value_counts().reset_index()
                        diagnosis_counts.columns = ["Diagnosis", "Count"]
                        fig = px.pie(diagnosis_counts, values="Count", names="Diagnosis", hole=0.4, title="Diagnostics", color_discrete_sequence=["#ff006e", "#8338ec"])
                    elif vis == "Aire Empilée":
                        fig = px.area(df_pred_filtered, x=df_pred_filtered.index, y=["Total_Bilirubin", "Sgpt", "Sgot"], title="Indicateurs", color_discrete_sequence=["#ff006e", "#8338ec", "#3a86ff"])
                    elif vis == "Radar":
                        mean_values = df_pred_filtered[["Total_Bilirubin", "Sgpt", "Sgot", "Albumin"]].mean()
                        fig = go.Figure(go.Scatterpolar(r=mean_values.values, theta=mean_values.index, fill='toself', name="Moyennes", line_color="#ff006e"))
                        fig.update_layout(polar=dict(bgcolor="rgba(20,20,40,0.8)", radialaxis=dict(visible=True)), title="Profil Moyen")
                    elif vis == "Entonnoir":
                        funnel_data = df_pred_filtered["diagnosis"].value_counts().reset_index()
                        funnel_data.columns = ["Diagnosis", "Count"]
                        fig = px.funnel(funnel_data, x="Count", y="Diagnosis", title="Entonnoir des Diagnostics", color_discrete_sequence=["#ff006e"])
                    fig.update_layout(height=400, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(20,20,40,0.8)", font=dict(color="#e0e0ff"))
                    st.plotly_chart(fig, use_container_width=True, key=f"spark_{vis}{iteration}")

            # Métriques et téléchargement
            col4, col5, col6 = st.columns(3)
            with col4:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Total des Cas", total_pred, delta=f"{delta_total:+d}")
                st.markdown('</div>', unsafe_allow_html=True)
            with col5:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Cas Malades", sick_pred, delta=f"{delta_sick:+d}")
                st.markdown('</div>', unsafe_allow_html=True)
            with col6:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Taux Malade", f"{(sick_pred/total_pred)*100:.2f}%" if total_pred > 0 else "0%", delta=f"{((sick_pred/total_pred)*100 - (st.session_state.prev_sick/st.session_state.prev_total)*100):+.2f}%" if st.session_state.prev_total > 0 else "0%")
                st.markdown(get_csv_download_link(df_pred_filtered, "predictions.csv"), unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("Aucune prédiction disponible.")

        # Section 2 : Données Kafka en Temps Réel
        st.markdown('<div class="section-header">Flux Kafka Live</div>', unsafe_allow_html=True)
        if not df_kafka.empty:
            kafka_vis = st.multiselect("Choisir les visualisations Kafka", list(vis_options.values()), default=["Dispersion Animée", "Barres Empilées", "Boîte"], key=f"kafka_vis{iteration}")
            col7, col8, col9 = st.columns(3)

            for i, vis in enumerate(kafka_vis[:3]):  # Limité à 3 pour la mise en page
                with [col7, col8, col9][i]:
                    if vis == "Dispersion Animée":
                        df_kafka["Timestamp"] = [datetime.now().strftime("%H:%M:%S") for _ in range(len(df_kafka))]
                        fig = px.scatter(df_kafka, x="Total_Bilirubin", y="Sgpt", size="Age", color="Gender", animation_frame="Timestamp", title="Dispersion", color_discrete_sequence=["#ff006e", "#8338ec"])
                    elif vis == "Barres Empilées":
                        fig = px.bar(df_kafka, x=df_kafka.index, y=["Total_Bilirubin", "Direct_Bilirubin"], title="Bilirubine", color_discrete_sequence=["#ff006e", "#8338ec"])
                    elif vis == "Boîte":
                        fig = px.box(df_kafka, y=["Total_Bilirubin", "Sgpt", "Sgot"], title="Distribution", color_discrete_sequence=["#ff006e", "#8338ec", "#3a86ff"])
                    elif vis == "Violon":
                        fig = px.violin(df_kafka, y="Total_Bilirubin", box=True, points="all", title="Violon Bilirubine", color_discrete_sequence=["#ff006e"])
                    elif vis == "Treemap":
                        treemap_data = df_kafka.groupby("Gender").agg({"Total_Bilirubin": "mean", "Sgpt": "mean"}).reset_index()
                        fig = px.treemap(treemap_data, path=["Gender"], values="Total_Bilirubin", title="Treemap", color_discrete_sequence=["#ff006e", "#8338ec"])
                    fig.update_layout(height=400, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(20,20,40,0.8)", font=dict(color="#e0e0ff"))
                    st.plotly_chart(fig, use_container_width=True, key=f"kafka_{vis}_{iteration}")

            # Tableau et téléchargement
            st.subheader("Dernières Données Kafka")
            st.dataframe(
                df_kafka.style.set_properties(**{
                    'background-color': 'rgba(20,20,40,0.8)',
                    'color': '#e0e0ff',
                    'border': '1px solid #ff006e'
                }),
                height=250
            )
            st.markdown(get_csv_download_link(df_kafka, "kafka_data.csv"), unsafe_allow_html=True)
        else:
            st.warning("Aucune donnée Kafka disponible.")

        # Mise à jour toutes les 2 secondes
        time.sleep(2)

# Fermeture du consommateur (non atteint dans la boucle infinie)
consumer.close()
