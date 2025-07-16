import joblib
import logging
import pandas as pd
import re
from sklearn.preprocessing import StandardScaler
from setup_connections import connect_to_database

def get_clustering_metadata():
    """
    Retrieve metadata from the database for clustering
    
    Returns:
        pandas.DataFrame: DataFrame containing video metadata for clustering
    """
    connection = connect_to_database()
    if not connection:
        logging.error("Failed to connect to database")
        return None
        
    query = "SELECT video_id, aantal_views, aantal_reacties, aantal_likes FROM populariteit"

    try:
        df = pd.read_sql(query, connection)
        df['likes_views_ratio'] = df['aantal_likes'] / df['aantal_views']
        df['likes_views_ratio'] = df['likes_views_ratio'].fillna(0)
        logging.info(f"Likes views ratio calculated for {len(df)} videos")
        return df
    except Exception as e:
        logging.error(f"Error retrieving clustering metadata: {e}")
        return None
    finally:
        if connection:
            connection.close()

def cluster_data(data):
    """
    Cluster video data using a pre-trained KMeans model
    
    Args:
        data (pandas.DataFrame): DataFrame containing video metadata
        
    Returns:
        pandas.DataFrame: DataFrame with cluster labels added
    """
    try:
        scaler = StandardScaler()
        features = data[['aantal_views', 'aantal_reacties', 'aantal_likes', 'likes_views_ratio']]

        if features.empty:
            logging.error("Insufficient data for clustering features.")
            raise ValueError("Insufficient data for clustering features.")

        scaled_features = scaler.fit_transform(features)

        # Load the pre-trained clustering model
        kmeans = joblib.load("clustering_model.pkl")

        # Predict cluster labels
        data['cluster_label'] = kmeans.predict(scaled_features)
        
        # Add a column to indicate if the cluster is considered popular
        popular_clusters = [0]  # Assuming cluster 0 is the popular cluster
        data['cluster_populariteit'] = data['cluster_label'].apply(
            lambda x: 1 if x in popular_clusters else 0)

        logging.info(f"Clustered {len(data)} videos into {len(data['cluster_label'].unique())} clusters")
        return data
    except Exception as e:
        logging.error(f"Error clustering data: {e}")
        return None

def clean_text(text):
    """
    Clean and preprocess text data
    
    Args:
        text (str): Text to clean
        
    Returns:
        str: Cleaned text
    """
    text = re.sub(r'\([^)]*\)', '', text)  # Remove text within parentheses
    text = text.lower()  # Convert to lowercase
    text = re.sub(r'\n+', ' ', text)  # Replace multiple newlines with a single space
    text = re.sub(r'[^a-z\s]', '', text)  # Remove all characters except lowercase letters and spaces
    text = text.strip()  # Strip leading and trailing whitespace

    return text

def load_nlp_model(nlp_model_path):
    """
    Load a pre-trained NLP model
    
    Args:
        nlp_model_path (str): Path to the NLP model file
        
    Returns:
        object: Loaded NLP model
    """
    try:
        return joblib.load(nlp_model_path)
    except Exception as e:
        logging.error(f"Error loading NLP model: {e}")
        return None

def classify_transcript(transcript, class_model_path, nlp_model_path):
    """
    Classify a transcript using pre-trained models
    
    Args:
        transcript (str): Transcript text to classify
        class_model_path (str): Path to the classification model file
        nlp_model_path (str): Path to the NLP model file
        
    Returns:
        str: Classification result ('populair' or 'niet populair')
    """
    try:
        # Load models
        class_model = joblib.load(class_model_path)
        nlp_model = load_nlp_model(nlp_model_path)
        
        if not class_model or not nlp_model:
            logging.error("Failed to load models for classification")
            return 'niet populair'  # Default to not popular if models can't be loaded
        
        # Convert transcript to list if it's a string
        transcript_list = [transcript] if isinstance(transcript, str) else transcript
        
        # Transform transcript using NLP model
        transcript_vector = nlp_model.transform(transcript_list)
        
        # Predict classification
        predictions = class_model.predict(transcript_vector)
        
        # Log results
        for i, (text, label) in enumerate(zip(transcript_list, predictions)):
            text_preview = text[:50] + "..." if len(text) > 50 else text
            logging.info(f"Text {i+1}: {text_preview} | Classification: {'Populair' if label == 1 else 'Niet Populair'}")
        
        # Return 'populair' if any prediction is 1, otherwise 'niet populair'
        return 'populair' if 1 in predictions else 'niet populair'
    except Exception as e:
        logging.error(f"Error classifying transcript: {e}")
        return 'niet populair'  # Default to not popular if an error occurs

def analyze_popularity(video_id, transcript):
    """
    Analyze the popularity of a video based on clustering and transcript classification
    
    Args:
        video_id (str): YouTube video ID
        transcript (str): Cleaned transcript text
        
    Returns:
        str: Popularity label ('populair' or 'niet populair')
    """
    try:
        # Get clustering metadata
        metadata = get_clustering_metadata()
        if metadata is None or video_id not in metadata['video_id'].values:
            logging.warning(f"No clustering metadata available for video ID {video_id}")
            # If no clustering data is available, rely solely on transcript classification
            return classify_transcript(transcript, "Old/classificatie_model.pkl", "Old/nlp_model.pkl")
        
        # Cluster the data
        clustered_data = cluster_data(metadata)
        if clustered_data is None:
            logging.warning(f"Clustering failed for video ID {video_id}")
            # If clustering fails, rely solely on transcript classification
            return classify_transcript(transcript, "Old/classificatie_model.pkl", "Old/nlp_model.pkl")
        
        # Get the cluster popularity value for this video
        cluster_value = clustered_data.loc[clustered_data['video_id'] == video_id, 'cluster_populariteit'].values
        is_popular_cluster = cluster_value[0] if len(cluster_value) > 0 else 0
        
        # Classify the transcript
        classification = classify_transcript(transcript, "Old/classificatie_model.pkl", "Old/nlp_model.pkl")
        is_popular_classification = classification == 'populair'
        
        logging.info(f"Video ID {video_id} - Cluster popularity: {is_popular_cluster}, Classification: {classification}")
        
        # If either the cluster or the classification indicates popularity, consider the video popular
        if is_popular_cluster == 1 or is_popular_classification:
            return 'populair'
        else:
            return 'niet populair'
    except Exception as e:
        logging.error(f"Error analyzing popularity for video ID {video_id}: {e}")
        return 'niet populair'  # Default to not popular if an error occurs