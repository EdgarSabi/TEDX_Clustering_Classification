import joblib
import re
import string


def preprocess_text(text):
    """
    Preprocess text for classification by:
    - Converting to lowercase
    - Removing punctuation
    - Removing extra whitespace
    
    Args:
        text (str): The text to preprocess
        
    Returns:
        str: The preprocessed text
    """
    if text is None:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove punctuation
    text = text.translate(str.maketrans('', '', string.punctuation))
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def predict_transcript_popularity(transcript, model_path='models/classification.joblib',
                                  vectorizer_path='models/tfidf_vectorizer.joblib'):
    try:
        # Laad de opgeslagen modellen
        model = joblib.load(model_path)
        vectorizer = joblib.load(vectorizer_path)

        # Voorbewerking van de transcript
        cleaned_transcript = preprocess_text(transcript)
        
        if not cleaned_transcript:
            return {
                'is_popular': False,
                'confidence': 0.0
            }

        # Transform de text met de geladen vectorizer
        transcript_features = vectorizer.transform([cleaned_transcript])

        # Voorspel het label
        prediction = model.predict(transcript_features)[0]
        probability = model.predict_proba(transcript_features)[0]

        return {
            'is_popular': bool(prediction),
            'confidence': float(probability[1]) if prediction == 1 else float(probability[0])
        }

    except Exception as e:
        print(f"Error predicting transcript popularity: {e}")
        return None
