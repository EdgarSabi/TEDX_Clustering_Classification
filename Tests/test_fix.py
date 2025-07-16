import logging
from main import main
from logger import setup_logging

# Set up logging
setup_logging()

def test_fix():
    """
    Test the fix for the 'relation "tijd" does not exist' error
    """
    logging.info("Testing fix for 'relation \"tijd\" does not exist' error")
    
    try:
        main()
        logging.info("Test passed! The application ran without the 'relation \"tijd\" does not exist' error.")
    except Exception as e:
        logging.error(f"Test failed! Error: {e}")

if __name__ == "__main__":
    test_fix()