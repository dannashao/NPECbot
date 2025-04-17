import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Default thresholds
DEFAULT_THRESHOLDS = {
    'temperature': {'min': 15, 'max': 30},
    'humidity': {'min': 0.3, 'max': 0.9},
    'light': {'min': 1000, 'max': 3000}
}

# Default error rate threshold (percentage)
DEFAULT_ERROR_RATE = 5.0

# Default alert frequency in minutes
DEFAULT_ALERT_FREQUENCY = 60

# Data directory
DATA_DIR = 'data'

# Whitelisted usernames (comma-separated)
WHITELISTED_USERS = os.getenv('WHITELISTED_USERS', '').split(',')

# Login code from .env
LOGIN_CODE = os.getenv('TEMP_CODE', '')

# Login expiration time in minutes
LOGIN_EXPIRATION = 10

# Maximum number of login attempts
MAX_LOGIN_ATTEMPTS = 3 