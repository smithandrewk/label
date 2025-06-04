import logging

# Configure logging
logging.basicConfig(
    filename='debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
# Get a logger for the app
logger = logging.getLogger('label')

def log(msg):
    logger.info(msg)