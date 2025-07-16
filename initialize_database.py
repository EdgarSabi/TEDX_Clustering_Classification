import logging
import psycopg2
from setup_connections import connect_to_database
from logger import setup_logging

# Set up logging
setup_logging()

def initialize_database():
    """
    Initialize the database by creating all required tables if they don't exist.
    
    This function creates the following tables:
    - video: Stores video metadata
    - tijd: Stores time dimension data
    - transcript: Stores video transcripts
    - populariteit: Stores popularity metrics
    
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    connection = connect_to_database()
    if not connection:
        logging.error("Failed to connect to the database. Cannot initialize tables.")
        return False
    
    try:
        with connection.cursor() as cursor:
            # Create video table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS video (
                    video_id VARCHAR(255) PRIMARY KEY,
                    titel VARCHAR(255),
                    uploaddatum DATE,
                    categorie VARCHAR(255),
                    duur_in_seconden INTEGER,
                    populariteit VARCHAR(255)
                );
            """)
            
            # Create tijd table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tijd (
                    tijd_id SERIAL PRIMARY KEY,
                    dag VARCHAR(255),
                    maand INTEGER,
                    jaar INTEGER,
                    UNIQUE(dag, maand, jaar)
                );
            """)
            
            # Create transcript table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transcript (
                    transcript_id SERIAL PRIMARY KEY,
                    video_id VARCHAR(255) REFERENCES video(video_id),
                    transcript TEXT
                );
            """)
            
            # Create populariteit table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS populariteit (
                    populariteit_id SERIAL PRIMARY KEY,
                    video_id VARCHAR(255) REFERENCES video(video_id),
                    tijd_id INTEGER REFERENCES tijd(tijd_id),
                    aantal_views INTEGER,
                    aantal_reacties INTEGER,
                    aantal_likes INTEGER
                );
            """)
            
            connection.commit()
            logging.info("Database tables initialized successfully")
            return True
            
    except Exception as e:
        logging.error(f"Error initializing database tables: {e}")
        connection.rollback()
        return False
    finally:
        connection.close()

if __name__ == "__main__":
    initialize_database()