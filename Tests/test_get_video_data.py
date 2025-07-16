import logging
import os
from dotenv import load_dotenv
from logger import setup_logging
from get_video_data import (
    get_video_ids,
    get_meta_data,
    duur_naar_seconden_transformeren,
    video_ids_naar_youtube_urls,
    clean_text,
    get_and_clean_captions,
    test_signature_extraction
)

# Set up logging and load environment variables
setup_logging()
load_dotenv()

def test_get_video_ids():
    """
    Test the get_video_ids function
    """
    logging.info("Testing get_video_ids function...")

    video_ids = get_video_ids()

    if video_ids:
        logging.info(f"Successfully retrieved {len(video_ids)} video IDs")
        logging.info(f"First few video IDs: {video_ids[:3]}")
        return True
    else:
        logging.error("Failed to retrieve video IDs")
        return False

def test_get_meta_data(video_id):
    """
    Test the get_meta_data function

    Args:
        video_id (str): YouTube video ID to test
    """
    logging.info(f"Testing get_meta_data function with video ID: {video_id}")

    metadata = get_meta_data(video_id)

    if metadata:
        logging.info(f"Successfully retrieved metadata for video ID: {video_id}")
        logging.info(f"Metadata: {metadata}")
        return True
    else:
        logging.error(f"Failed to retrieve metadata for video ID: {video_id}")
        return False

def test_get_and_clean_captions(video_id):
    """
    Test the get_and_clean_captions function

    Args:
        video_id (str): YouTube video ID to test
    """
    logging.info(f"Testing get_and_clean_captions function with video ID: {video_id}")

    captions = get_and_clean_captions(video_id)

    if captions:
        logging.info(f"Successfully retrieved and cleaned captions for video ID: {video_id}")
        preview = captions[:100] + "..." if len(captions) > 100 else captions
        logging.info(f"First 100 characters: {preview}")
        return True
    else:
        logging.error(f"Failed to retrieve and clean captions for video ID: {video_id}")
        return False

def main():
    """
    Main function to run all tests
    """
    logging.info("Starting tests for get_video_data.py")

    # Test get_video_ids
    if test_get_video_ids():
        logging.info("get_video_ids test passed")
    else:
        logging.error("get_video_ids test failed")
        return

    # Get a video ID to use for further tests
    video_ids = get_video_ids()
    if not video_ids:
        logging.error("No video IDs available for further tests")
        return

    test_video_id = video_ids[0]
    logging.info(f"Using video ID {test_video_id} for further tests")

    # Test get_meta_data
    if test_get_meta_data(test_video_id):
        logging.info("get_meta_data test passed")
    else:
        logging.error("get_meta_data test failed")

    # Test get_and_clean_captions
    if test_get_and_clean_captions(test_video_id):
        logging.info("get_and_clean_captions test passed")
    else:
        logging.error("get_and_clean_captions test failed")

    # Test signature extraction
    if test_signature_extraction():
        logging.info("test_signature_extraction test passed")
    else:
        logging.error("test_signature_extraction test failed")

    logging.info("All tests completed")

if __name__ == "__main__":
    main()
