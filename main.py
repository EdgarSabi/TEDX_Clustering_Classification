import logging
from dotenv import load_dotenv
from logger import setup_logging
from setup_connections import connect_to_database
from get_video_data import get_video_ids, get_meta_data, get_and_clean_captions
from setup_database import (
    insert_video_dimensie, 
    insert_tijd_dimensie, 
    insert_transcript, 
    insert_populariteit,
    update_label_in_db
)
from popularity_analysis import analyze_popularity
from initialize_database import initialize_database

setup_logging()
load_dotenv()

def main():

    logging.info("Starting the application")

    logging.info("Initializing database tables")
    if not initialize_database():
        logging.error("Failed to initialize database tables. Exiting.")
        return
    logging.info("Database tables initialized successfully")


    connection = connect_to_database()
    if not connection:
        logging.error("Failed to connect to the database. Exiting.")
        return
    logging.info("Successfully connected to the database")

    try:
        # Get video IDs from the server
        logging.info("Retrieving video IDs from the server")
        video_ids = get_video_ids()
        if not video_ids:
            logging.error("Failed to retrieve video IDs. Exiting.")
            return
        logging.info(f"Retrieved {len(video_ids)} video IDs")

        # Process all videos
        logging.info(f"Processing all {len(video_ids)} videos")

        # Process each video
        for video_id in video_ids:
            logging.info(f"Processing video ID: {video_id}")

            # Get metadata from YouTube API
            video_data = get_meta_data(video_id)
            if not video_data:
                logging.error(f"Failed to retrieve metadata for video ID {video_id}. Skipping.")
                continue

            # Insert video dimension data
            insert_video_dimensie(video_data, connection)

            # Insert time dimension data
            upload_date = video_data[2]  # Index 2 contains the upload date
            tijd_id = insert_tijd_dimensie(upload_date, connection)
            if not tijd_id:
                logging.error(f"Failed to insert time dimension for video ID {video_id}. Skipping.")
                continue

            # Get and clean captions
            captions = get_and_clean_captions(video_id)
            if captions:
                # Insert transcript data
                insert_transcript(video_id, captions, connection)

                # Analyze popularity
                popularity_label = analyze_popularity(video_id, captions)
                logging.info(f"Video ID {video_id} analyzed as: {popularity_label}")

                # Update label in the database
                update_label_in_db(video_id, popularity_label, connection)
            else:
                logging.warning(f"No captions available for video ID {video_id}")

            # Insert popularity data
            insert_populariteit(video_data, tijd_id, connection)

            logging.info(f"Completed processing for video ID: {video_id}")

        logging.info("All videos processed successfully")

    except Exception as e:
        logging.error(f"An error occurred during processing: {e}")
    finally:
        if connection:
            connection.close()
            logging.info("Database connection closed")

if __name__ == "__main__":
    main()
