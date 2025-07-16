import paramiko
import logging
import os
from logger import setup_logging

# Set up logging
setup_logging()

def connect_to_server():
    """
    Connect to the server via SSH and list directories in /data/video using SFTP
    """
    try:
        # SSH connection parameters
        hostname = '145.97.16.170'
        username = 's1146363'
        password = 's1146363'

        # Create SSH client
        logging.info(f"Connecting to server {hostname} with username {username}")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to the server
        ssh_client.connect(hostname=hostname, username=username, password=password)
        logging.info("Successfully connected to the server")

        # Create SFTP client
        sftp_client = ssh_client.open_sftp()
        logging.info("SFTP connection established")

        # List directories in /data/video using listdir
        path = '/data/video'
        logging.info(f"Listing directories in {path}")

        # Get all items in the directory using listdir
        folders = sftp_client.listdir(path)

        # Print folder names as strings
        logging.info("Items in /data/video:")
        for folder in folders:
            print(folder)

        # Close the connections
        sftp_client.close()
        ssh_client.close()
        logging.info("SSH and SFTP connections closed")

        return folders

    except Exception as e:
        logging.error(f"Error connecting to server: {e}")
        return None

if __name__ == "__main__":
    connect_to_server()
