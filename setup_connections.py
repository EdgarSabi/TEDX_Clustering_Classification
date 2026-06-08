import os
import logging
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def connect_to_database():
    try:
        logging.info("Verbinden met Supabase/PostgreSQL...")

        connection = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT", "5432"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            sslmode=os.getenv("DB_SSLMODE", "require"),
        )

        logging.info("Databaseverbinding gelukt.")
        return connection

    except psycopg2.DatabaseError as error:
        logging.error(f"Database connection error: {error}")
        return None
