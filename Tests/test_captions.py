import logging
from get_video_data import get_video_ids, get_and_clean_captions
from logger import setup_logging

# Set up logging
setup_logging()

def test_captions():
    """
    Test the functionality to get and clean captions
    """
    logging.info("Testing caption retrieval and cleaning...")
    
    # Get video IDs
    video_ids = get_video_ids()
    
    if not video_ids:
        logging.error("Failed to retrieve video IDs")
        return
    
    logging.info(f"Retrieved {len(video_ids)} video IDs")
    
    # Test with the first video ID
    test_video_id = video_ids[0]
    logging.info(f"Testing with video ID: {test_video_id}")
    
    # Get and clean captions
    captions = get_and_clean_captions(test_video_id)
    
    if captions:
        logging.info(f"Successfully retrieved and cleaned captions for {test_video_id}")
        logging.info(f"First 100 characters of cleaned captions: {captions[:100]}...")
        logging.info("Test passed!")
    else:
        logging.error(f"Failed to retrieve captions for {test_video_id}")
        logging.error("Test failed!")

if __name__ == "__main__":
    test_captions()