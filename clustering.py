import joblib
import logging
import pandas as pd
from setup_connections import connect_to_database
from sklearn.preprocessing import StandardScaler

def verkrijg_clustering_metadata():
    connection = connect_to_database()
    query = "SELECT video_id, aantal_views, aantal_reacties, aantal_likes FROM populariteit"

    try:
        df = pd.read_sql(query, connection)
        df['likes_views_ratio'] = df['aantal_likes'] / df['aantal_views']
        df['likes_views_ratio'] = df['likes_views_ratio'].fillna(0)
        logging.info(f"Likes views ratio: {df['likes_views_ratio']}")
        return df
    finally:
        if connection:
            connection.close()

def clusteren_van_data(data):
    scaler = StandardScaler()
    features = data[['aantal_views', 'aantal_reacties', 'aantal_likes', 'likes_views_ratio']]

    if features.empty:
        logging.error("Onvoldoende gegevens voor het clusteren van features.")
        raise ValueError("Onvoldoende gegevens voor het clusteren van features.")

    scaled_features = scaler.fit_transform(features)

    kmeans = joblib.load("clustering_model.pkl")

    data['cluster_label'] = kmeans.predict(scaled_features)

    return data[['video_id', 'cluster_label']]
