import psycopg2
import os
import logging
from dotenv import load_dotenv

load_dotenv()

dbname = os.getenv('DB_NAME')
host = os.getenv('DB_HOST')
user = os.getenv('DB_USER')
password = os.getenv('DB_PASSWORD')
ssh_host = os.getenv('SERVER_HOST')
ssh_port = os.getenv('PORT')

def connect_to_database():
    try:
        logging.info("Verbinden met de database...")
        connection = psycopg2.connect(
            dbname=dbname,
            host=host,
            user=user,
            password=password
        )
        logging.debug(
            f"Database connection details:\n"
            f"  Database Name: {dbname}\n"
            f"  Host: {host}\n"
            f"  User: {user}"
        )
        return connection
    except psycopg2.DatabaseError as error:
        logging.info(f"Database connection error: {error}")
        return None

