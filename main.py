import logging
from dotenv import load_dotenv
from logger import setup_logging
from setup_connections import connect_to_database
from get_video_data import get_video_ids, get_meta_data
from setup_database import (
    setup_new_database_schema,
    insert_video_to_new_schema,
    insert_tijd_to_new_schema,
    insert_categorie_to_new_schema,
    insert_tags_to_new_schema,
    insert_populariteit_to_new_schema
)

setup_logging()
load_dotenv()

def main():

    logging.info("Starting the application")

    logging.info("Setting up new database schema")
    setup_new_database_schema()
    logging.info("New database schema setup completed")


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

            # Insert video data into Dim_Video
            video_key = insert_video_to_new_schema(video_data, connection)
            if not video_key:
                logging.error(f"Failed to insert video data for video ID {video_id}. Skipping.")
                continue

            # Insert time data into Dim_Tijd
            upload_date = video_data[2]  # Index 2 contains the upload date
            tijd_key = insert_tijd_to_new_schema(upload_date, connection)
            if not tijd_key:
                logging.error(f"Failed to insert time data for video ID {video_id}. Skipping.")
                continue

            # Extract category information from video_data
            category_id = video_data[7]  # Index 7 contains the category_id
            # We don't have category names in the API response, so we'll use a generic name based on ID
            category_name = f"Category {category_id}"

            # Insert category data into Dim_Categorie
            categorie_key = insert_categorie_to_new_schema(category_id, category_name, connection)
            if not categorie_key:
                logging.error(f"Failed to insert category data for video ID {video_id}. Skipping.")
                continue

            # Extract tags from video_data and insert them
            tags = video_data[8]  # Index 8 contains the tags list
            if not insert_tags_to_new_schema(video_key, tags, connection):
                logging.warning(f"Failed to insert tags for video ID {video_id}, but continuing processing.")

            # Insert popularity data into Feit_VideoPopulariteit
            success = insert_populariteit_to_new_schema(
                video_data, video_key, tijd_key, categorie_key, connection
            )
            if not success:
                logging.error(f"Failed to insert popularity data for video ID {video_id}. Skipping.")
                continue

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
