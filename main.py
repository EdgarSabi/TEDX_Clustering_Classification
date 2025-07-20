import logging
from datetime import datetime
from dotenv import load_dotenv
from logger import setup_logging
from setup_connections import connect_to_database
from get_video_data import get_video_ids, get_meta_data, delete_caption_file
from setup_database import (
    insert_video_to_new_schema,
    insert_tijd_to_new_schema,
    insert_categorie_to_new_schema,
    insert_populariteit_to_new_schema
)

setup_logging()
load_dotenv()

def main():

    logging.info("Starting the application")

    try:
        with connect_to_database() as connection:
            video_ids = get_video_ids()
            if not video_ids:
                logging.error("Failed to retrieve video IDs. Exiting.")
                return
            logging.info(f"Retrieved {len(video_ids)} video IDs")

            for video_id in video_ids:
                logging.info(f"Processing video ID: {video_id}")

                # Check if video already exists in database
                existing_record = None
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT video_key, transcript FROM Dim_Video WHERE video_id = %s", (video_id,))
                        existing_record = cursor.fetchone()
                except Exception as e:
                    logging.warning(f"Error checking if video exists in database: {e}. Will proceed with normal caption retrieval.")

                video_data = get_meta_data(video_id, existing_record, connection)
                if not video_data:
                    logging.error(f"Failed to retrieve metadata for video ID {video_id}. Skipping.")
                    continue

                video_key = insert_video_to_new_schema(video_data, connection)
                if not video_key:
                    logging.error(f"Failed to insert video data for video ID {video_id}. Skipping.")
                    continue

                # Delete caption file if we retrieved new captions (not skipped)
                if video_data[8] != "CAPTION_SKIPPED":
                    if delete_caption_file(video_id):
                        logging.info(f"Deleted caption file for video ID: {video_id} after database insertion")
                    else:
                        logging.warning(f"Failed to delete caption file for video ID: {video_id} or file didn't exist")

                upload_date = video_data[2]
                tijd_key = insert_tijd_to_new_schema(upload_date, connection)
                if not tijd_key:
                    logging.error(f"Could not find or create tijd_key for date {upload_date}. Skipping video.")
                    continue

                category_id = video_data[7]
                category_name = f"Category {category_id}"

                categorie_key = insert_categorie_to_new_schema(category_id, category_name, connection)
                if not categorie_key:
                    logging.error(f"Could not find or create categorie_key for category_id {category_id}. Skipping video.")
                    continue


                success = insert_populariteit_to_new_schema(
                    video_data, video_key, tijd_key, categorie_key, connection
                )
                if not success:
                    logging.warning(f"Failed to insert popularity data for video ID {video_id}, but continuing processing.")

                logging.info(f"Completed processing for video ID: {video_id}")
                print(f"✅ Updated information for video ID: {video_id} - Title: {video_data[1]}")
                print(f"   Views: {video_data[3]}, Likes: {video_data[5]}, Comments: {video_data[4]}")
                print(f"   Views per day: {video_data[3] / max((datetime.now() - datetime.strptime(video_data[2], '%Y-%m-%d')).days, 1):.2f}")
                print(f"   Engagement rate: {(video_data[5] + video_data[4]) / max(video_data[3], 1):.4f}")

        logging.info("All videos processed successfully")

    except Exception as e:
        logging.error(f"An error occurred during processing: {e}")
    finally:
        if connection:
            connection.close()
            logging.info("Database connection closed")

if __name__ == "__main__":
    main()
