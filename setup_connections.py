import psycopg2
import os
import paramiko
import logging
from dotenv import load_dotenv
from logger import setup_logging

setup_logging()
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
        logging.debug("Debugging Database Connectie:")
        logging.debug(f"Database Name: {dbname}")
        logging.debug(f"Host: {host}")
        logging.debug(f"User: {user}")
        return connection
    except psycopg2.DatabaseError as error:
        logging.info(f"Database connection error: {error}")
        return None

# def connect_to_server():
#     """
#     Connect to the server via SSH
#
#     Returns:
#         paramiko.SSHClient: SSH client connected to the server, or None if connection failed
#     """
#     logging.info("Verbinden met de server voor lezen...")
#     client = paramiko.SSHClient()
#     client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#     try:
#         client.connect(ssh_host, int(ssh_port), user, password)
#         logging.debug("Debugging SSH Connectie:")
#         logging.debug(f"SSH Host: {ssh_host}")
#         logging.debug(f"SSH Port: {ssh_port}")
#         logging.debug(f"SSH Username: {user}")
#         return client
#     except paramiko.AuthenticationException as error:
#         logging.error(f"Authentication error: {error}")
#         return None
#     except paramiko.SSHException as error:
#         logging.error(f"SSH connection error: {error}")
#         return None
#     except Exception as error:
#         logging.error(f"Unexpected error connecting to server: {error}")
#         return None
