"""
Structured Logger Initialization using Loguru

Configures console and file logger with level filtering and formatted outputs.
"""
import sys
from pathlib import Path

# Ensure project root is always on sys.path before any project imports
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from loguru import logger
from config.settings import settings

def setup_logger():
    """Initializes and configures the Loguru logger instance."""
    logger.remove()
    
    # Console handler
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL.upper(),
        enqueue=True
    )
    
    return logger

app_logger = setup_logger()
