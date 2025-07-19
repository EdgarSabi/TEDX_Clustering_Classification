import joblib
import re
import logging
from enum import Enum

class Sentiment(Enum):
    NEGATIVE = False
    POSITIVE = True

def preprocess_text(text):

    if not text:
        logging.warning("Empty text provided for cleaning")
        return "No text to clean"

    text = re.sub(r'^WEBVTT.*?\n\n', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}.*?\n', '', text)
    text = re.sub(r'\[[^\]]*\]', ' ', text)
    text = re.sub(r'\([^)]*\)', ' ', text)
    text = re.sub(r'<[^>]*>', ' ', text)
    text = text.lower()
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r'\d+', ' ', text)
    text = ' '.join(text.split())

    return text.strip()


def predict_sentiment(transcript, model_path='models/classification.joblib',
                      vectorizer_path='models/nlp_model.joblib'):
    try:
        # Load the saved models
        model = joblib.load(model_path)
        vectorizer = joblib.load(vectorizer_path)

        # Preprocess the transcript
        cleaned_transcript = preprocess_text(transcript)

        if not cleaned_transcript:
            return {
                'sentiment': False,
                'confidence': 0.0
            }

        # Transform the text using the loaded vectorizer
        transcript_features = vectorizer.transform([cleaned_transcript])

        # Make prediction
        prediction = model.predict(transcript_features)[0]
        probabilities = model.predict_proba(transcript_features)[0]

        confidence = float(probabilities[1] if prediction == 1 else probabilities[0])
        sentiment = Sentiment.POSITIVE if prediction == 1 else Sentiment.NEGATIVE
        sentiment_label = 'Positief' if prediction == 1 else 'Negatief'

        return {
                'sentiment': sentiment,
                'sentiment_label': sentiment_label,
                'confidence': confidence
            }
    except Exception as e:
        logging.error(f"Error predicting sentiment: {e}")
        return None



def batch_predict_sentiment(transcripts, model_path='models/classification.joblib',
                            vectorizer_path='models/nlp_model.joblib'):
    try:
        model = joblib.load(model_path)
        vectorizer = joblib.load(vectorizer_path)

        cleaned_transcripts = [preprocess_text(t) for t in transcripts]

        features = vectorizer.transform(cleaned_transcripts)

        predictions = model.predict(features)
        probabilities = model.predict_proba(features)

        results = []
        for pred, prob in zip(predictions, probabilities):
            confidence = float(prob[1] if pred == 1 else prob[0])
            sentiment = Sentiment.POSITIVE if pred == 1 else Sentiment.NEGATIVE
            sentiment_label = 'Positief' if pred == 1 else 'Negatief'

            results.append({
                'sentiment': sentiment,
                'sentiment_label': sentiment_label,
                'confidence': confidence
            })

        return results

    except Exception as e:
        logging.error(f"Error in batch sentiment prediction: {e}")
        return None

