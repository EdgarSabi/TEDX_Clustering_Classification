import logging
from main import main
from logger import setup_logging

# Set up logging
setup_logging()

def test_main():
    """
    Test the main function from main.py
    """
    logging.info("Testing main function...")
    
    try:
        main()
        logging.info("Main function executed successfully!")
    except Exception as e:
        logging.error(f"Error executing main function: {e}")
        logging.error("Test failed!")

if __name__ == "__main__":
    test_main()