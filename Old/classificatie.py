import joblib
import re
import logging

def bewerk_tekst(tekst):
    tekst = re.sub(r'\([^)]*\)', '', tekst)
    tekst = tekst.lower()
    tekst = re.sub(r'\n+', ' ', tekst)
    tekst = re.sub(r'[^a-z\s]', '', tekst)
    tekst = tekst.strip()

    return tekst

def laad_nlp_model(nlp_model):
    return joblib.load(nlp_model)

def classificeer_transcript(transcript, class_model, nlp_model):
    transcript_vector = nlp_model.transform(transcript)

    voorspellingen = class_model.predict(transcript_vector)

    geclassificeerde_resultaten = []
    for tekst, label in zip(transcript, voorspellingen):
        geclassificeerde_resultaten.append((tekst, label))
        logging.info(f"Tekst: {transcript[:50]}... | Classificatie: {'Populair' if label == 1 else 'Niet Populair'}")

    return geclassificeerde_resultaten



