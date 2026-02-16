import logging
import os
import sys

# Ensure logs directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "communication.log")

def get_pta_logger():
    """
    Returns a configured logger for PTA communication transparency.
    Logs to logs/communication.log and is unbuffered (flushed immediately).
    """
    logger = logging.getLogger("pta_communication")
    
    # Avoid adding handlers multiple times
    if logger.hasHandlers():
        return logger
        
    logger.setLevel(logging.INFO)
    
    # File Handler
    file_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Simple Format: Timestamp - Actor - Message
    formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.propagate = False # Do not propagate to root logger (avoid stdout)
    
    return logger

def log_event(actor: str, message: str):
    """
    Helper to log an event in a consistent format.
    Actors: USER, PTA, SYSTEM
    """
    logger = get_pta_logger()
    logger.info(f"[{actor}] {message}")
    
    # Force flush to ensure tail -f works in real-time
    for handler in logger.handlers:
        handler.flush()
