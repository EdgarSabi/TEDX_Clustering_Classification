import logging

def setup_logging():
    logging.basicConfig(
        handlers=[logging.StreamHandler()],
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
