"""
Logger Module
Configures and provides logging functionality
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
try:
    import colorlog
except Exception:
    colorlog = None


def setup_logger(name='vape-tagger', log_dir='./logs', level='INFO', verbose=False):
    """
    Set up a logger with colored console output and file logging
    
    Args:
        name: Logger name
        log_dir: Directory to store log files
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        verbose: Enable verbose logging
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory
    log_dir_path = Path(log_dir)
    log_dir_path.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    
    # Set level
    if verbose:
        log_level = logging.DEBUG
    else:
        log_level = getattr(logging, level.upper(), logging.INFO)
    
    logger.setLevel(log_level)
    
    # Clear existing handlers
    logger.handlers = []
    
    # Console handler with color when available, otherwise plain stream handler
    if colorlog:
        console_handler = colorlog.StreamHandler(sys.stdout)
    else:
        console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if colorlog:
        console_format = colorlog.ColoredFormatter(
            '%(log_color)s%(levelname)-8s%(reset)s %(blue)s[%(name)s]%(reset)s %(message)s',
            datefmt=None,
            reset=True,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
    else:
        console_format = logging.Formatter('%(levelname)-8s [%(name)s] %(message)s')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_dir_path / f'{name}_{timestamp}.log'
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    logger.info(f"Logger initialized - Log file: {log_file}")
    
    return logger
