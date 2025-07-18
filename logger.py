import logging
import sys

def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    logging.basicConfig(
        handlers=[logging.StreamHandler()],
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
