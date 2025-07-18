import logging

import numpy as np
import joblib
import pandas as pd
from datetime import datetime
from sklearn.preprocessing import LabelEncoder

def predict_cluster_label(video_data, scaler_path='models/scaler.joblib', model_path='models/clustering_model.joblib'):
    try:
        # Laad de opgeslagen modellen
        scaler = joblib.load(scaler_path)
        kmeans = joblib.load(model_path)

        # Bereken de features
        views = video_data[3]
        likes = video_data[5]
        comments = video_data[4]
        duration = video_data[6]  # Duration in seconds
        upload_date = datetime.strptime(video_data[2], '%Y-%m-%d')
        days_since_upload = max((datetime.now() - upload_date).days, 1)
        
        # Encode duration using LabelEncoder
        label_encoder = LabelEncoder()
        # We need to create a list/array with the duration to fit_transform
        duration_encoded = label_encoder.fit_transform([duration])[0]

        # Maak feature vector
        features = pd.DataFrame([[
            views / days_since_upload,  # views_per_day
            (likes + comments) / max(views, 1),  # engagement_ratio
            0,  # views_relative_to_category (wordt later bijgewerkt)
            duration_encoded,  # duration_encoded (using LabelEncoder)
            comments / max(likes, 1)  # comment_like_ratio
        ]], columns=['views_per_day', 'engagement_ratio',
                     'views_relative_to_category', 'duration_encoded',
                     'comment_like_ratio'])

        # Schaal de features
        scaled_features = scaler.transform(features)

        # Voorspel cluster
        cluster_label = kmeans.predict(scaled_features)[0]
        
        # Log the raw cluster output
        logging.info(f"Raw cluster output: {cluster_label}")
        
        # Convert integer to boolean: 0 -> False, 1 -> True
        rating = bool(cluster_label == 1)

        return rating

    except Exception as e:
        logging.error(f"Error predicting cluster label: {e}")
        return None
