import logging
from get_metadata import get_metadata
from logger import setup_logging

# Set up logging
setup_logging()

def test_get_metadata():
    """
    Test the get_metadata function to ensure it works correctly
    """
    logging.info("Testing get_metadata function...")
    
    # Call the get_metadata function
    folders = get_metadata()
    
    # Check if folders were retrieved successfully
    if folders:
        logging.info(f"Successfully retrieved {len(folders)} folders")
        logging.info("Test passed!")
    else:
        logging.error("Failed to retrieve folders")
        logging.error("Test failed!")

if __name__ == "__main__":
    test_get_metadata()