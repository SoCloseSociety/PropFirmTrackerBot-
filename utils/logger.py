import logging
import os
import sys
from datetime import datetime

# Color codes
COLORS = {
    'RESET': '\033[0m',
    'RED': '\033[91m',
    'GREEN': '\033[92m',
    'YELLOW': '\033[93m',
    'BLUE': '\033[94m',
    'MAGENTA': '\033[95m',
    'CYAN': '\033[96m',
    'WHITE': '\033[97m',
    'BOLD': '\033[1m',
    'DIM': '\033[2m',
}

TAG_COLORS = {
    'STARTUP': f"{COLORS['BOLD']}{COLORS['GREEN']}",
    'SCRAPE': f"{COLORS['CYAN']}",
    'ALERT': f"{COLORS['YELLOW']}",
    'PAYMENT': f"{COLORS['GREEN']}",
    'REFERRAL': f"{COLORS['MAGENTA']}",
    'AI': f"{COLORS['BLUE']}",
    'ERROR': f"{COLORS['RED']}",
    'WARN': f"{COLORS['YELLOW']}",
    'DB': f"{COLORS['DIM']}{COLORS['WHITE']}",
    'BOT': f"{COLORS['BOLD']}{COLORS['CYAN']}",
    'SCHEDULER': f"{COLORS['BLUE']}",
    'TEST': f"{COLORS['MAGENTA']}",
}

TAG_EMOJIS = {
    'STARTUP': '🚀',
    'SCRAPE': '🔍',
    'ALERT': '🔔',
    'PAYMENT': '💰',
    'REFERRAL': '👥',
    'AI': '🧠',
    'ERROR': '❌',
    'WARN': '⚠️',
    'DB': '💾',
    'BOT': '🤖',
    'SCHEDULER': '⏰',
    'TEST': '🧪',
}

_loggers = {}

def setup_logger(name='PropFirmTracker', level='INFO', log_file=None):
    if name in _loggers:
        return _loggers[name]
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers = []
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    _loggers[name] = logger
    return logger

def get_logger(name='PropFirmTracker'):
    if name not in _loggers:
        return setup_logger(name)
    return _loggers[name]

def _format_message(message, tag=None, level='INFO'):
    timestamp = datetime.now().strftime('%H:%M:%S')
    if tag:
        emoji = TAG_EMOJIS.get(tag, '📌')
        color = TAG_COLORS.get(tag, COLORS['WHITE'])
        return f"{COLORS['DIM']}{timestamp}{COLORS['RESET']} {color}[{emoji} {tag}]{COLORS['RESET']} {message}"
    level_colors = {
        'INFO': COLORS['WHITE'],
        'WARNING': COLORS['YELLOW'],
        'ERROR': COLORS['RED'],
        'DEBUG': COLORS['DIM'],
    }
    color = level_colors.get(level, COLORS['WHITE'])
    return f"{COLORS['DIM']}{timestamp}{COLORS['RESET']} {color}{message}{COLORS['RESET']}"

def log_info(message, tag=None):
    logger = get_logger()
    logger.info(_format_message(message, tag=tag, level='INFO'))

def log_warn(message, tag=None):
    logger = get_logger()
    logger.warning(_format_message(message, tag=tag, level='WARNING'))

def log_error(message, tag=None):
    logger = get_logger()
    logger.error(_format_message(message, tag=tag, level='ERROR'))

def log_debug(message, tag=None):
    logger = get_logger()
    logger.debug(_format_message(message, tag=tag, level='DEBUG'))
