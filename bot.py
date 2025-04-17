import os
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import config

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# Remove httpx logging
logging.getLogger('httpx').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# User states
user_states = {}
user_thresholds = {}
user_alert_frequencies = {}
login_attempts = {}

class CSVHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app
        self.last_processed = None
        logger.info("CSVHandler initialized")

    async def on_created(self, event):
        if event.is_directory or not event.src_path.endswith('.csv'):
            return
        logger.info(f"New CSV file detected: {event.src_path}")
        await self.process_file(event.src_path)

    async def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith('.csv'):
            return
        logger.info(f"CSV file modified: {event.src_path}")
        await self.process_file(event.src_path)

    async def process_file(self, file_path):
        try:
            logger.info(f"Starting to process file: {file_path}")
            df = pd.read_csv(file_path)
            logger.info(f"Successfully read CSV file with {len(df)} rows")
            logger.info(f"DataFrame columns: {df.columns.tolist()}")
            logger.info(f"Sample data:\n{df.head()}")
            
            current_time = datetime.now()
            
            # Get all authenticated users with valid sessions
            authenticated_users = []
            for uid, state in user_states.items():
                if state.get('authenticated'):
                    if 'expires' in state:
                        if datetime.now() <= state['expires']:
                            authenticated_users.append(uid)
                        else:
                            logger.info(f"User {uid}'s session has expired")
                            state['authenticated'] = False
                    else:
                        authenticated_users.append(uid)
            
            if not authenticated_users:
                logger.info("No authenticated users found, skipping threshold checks")
                return
                
            logger.info(f"Found {len(authenticated_users)} authenticated users: {authenticated_users}")
            
            # Process file for each authenticated user
            for user_id in authenticated_users:
                thresholds = user_thresholds.get(user_id, config.DEFAULT_THRESHOLDS)
                logger.info(f"Checking thresholds for user {user_id}: {thresholds}")
                
                alerts = []
                
                # Check temperature
                temp_out_of_range = (df['Temperature'] < thresholds['temperature']['min']) | (df['Temperature'] > thresholds['temperature']['max'])
                if temp_out_of_range.any():
                    out_of_range_values = df[temp_out_of_range]['Temperature'].tolist()
                    logger.info(f"Temperature alert triggered for user {user_id}. Values out of range: {out_of_range_values}")
                    logger.info(f"Temperature range: {thresholds['temperature']['min']} - {thresholds['temperature']['max']}")
                    alerts.append(f"⚠️ Temperature out of range! Values: {out_of_range_values}")
                
                # Check humidity
                hum_out_of_range = (df['Humidity'] < thresholds['humidity']['min']) | (df['Humidity'] > thresholds['humidity']['max'])
                if hum_out_of_range.any():
                    out_of_range_values = df[hum_out_of_range]['Humidity'].tolist()
                    logger.info(f"Humidity alert triggered for user {user_id}. Values out of range: {out_of_range_values}")
                    logger.info(f"Humidity range: {thresholds['humidity']['min']} - {thresholds['humidity']['max']}")
                    alerts.append(f"⚠️ Humidity out of range! Values: {out_of_range_values}")
                
                # Check light
                light_out_of_range = (df['Light'] < thresholds['light']['min']) | (df['Light'] > thresholds['light']['max'])
                if light_out_of_range.any():
                    out_of_range_values = df[light_out_of_range]['Light'].tolist()
                    logger.info(f"Light alert triggered for user {user_id}. Values out of range: {out_of_range_values}")
                    logger.info(f"Light range: {thresholds['light']['min']} - {thresholds['light']['max']}")
                    alerts.append(f"⚠️ Light intensity out of range! Values: {out_of_range_values}")
                
                # If there are alerts, check frequency and send
                if alerts:
                    frequency = user_alert_frequencies.get(user_id, config.DEFAULT_ALERT_FREQUENCY)
                    last_alert = user_states[user_id].get('last_alert')
                    
                    if not last_alert or (current_time - last_alert).total_seconds() >= frequency * 60:
                        message = "\n".join(alerts)
                        logger.info(f"Sending alerts to user {user_id}: {message}")
                        await self.app.bot.send_message(chat_id=user_id, text=message)
                        user_states[user_id]['last_alert'] = current_time
                    else:
                        logger.info(f"Alert frequency not met for user {user_id}, skipping")
                else:
                    logger.info(f"No alerts triggered for user {user_id}")

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}", exc_info=True)

    def check_thresholds(self, df, thresholds):
        alerts = []
        logger.info(f"Starting threshold check with thresholds: {thresholds}")
        logger.info(f"DataFrame columns: {df.columns.tolist()}")
        logger.info(f"Sample data:\n{df.head()}")
        
        # Check temperature
        temp_out_of_range = (df['Temperature'] < thresholds['temperature']['min']) | (df['Temperature'] > thresholds['temperature']['max'])
        if temp_out_of_range.any():
            out_of_range_values = df[temp_out_of_range]['Temperature'].tolist()
            logger.info(f"Temperature alert triggered. Values out of range: {out_of_range_values}")
            logger.info(f"Temperature range: {thresholds['temperature']['min']} - {thresholds['temperature']['max']}")
            alerts.append(f"Temperature out of range! Values: {out_of_range_values}")
        
        # Check humidity
        hum_out_of_range = (df['Humidity'] < thresholds['humidity']['min']) | (df['Humidity'] > thresholds['humidity']['max'])
        if hum_out_of_range.any():
            out_of_range_values = df[hum_out_of_range]['Humidity'].tolist()
            logger.info(f"Humidity alert triggered. Values out of range: {out_of_range_values}")
            logger.info(f"Humidity range: {thresholds['humidity']['min']} - {thresholds['humidity']['max']}")
            alerts.append(f"Humidity out of range! Values: {out_of_range_values}")
        
        # Check light
        light_out_of_range = (df['Light'] < thresholds['light']['min']) | (df['Light'] > thresholds['light']['max'])
        if light_out_of_range.any():
            out_of_range_values = df[light_out_of_range]['Light'].tolist()
            logger.info(f"Light alert triggered. Values out of range: {out_of_range_values}")
            logger.info(f"Light range: {thresholds['light']['min']} - {thresholds['light']['max']}")
            alerts.append(f"Light intensity out of range! Values: {out_of_range_values}")
        
        logger.info(f"Threshold check completed. Found {len(alerts)} alerts")
        return alerts

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started the bot")
    user_states[user.id] = {'authenticated': False}
    
    # Remove @ from username if present
    username = user.username.lstrip('@') if user.username else None
    
    if username and username in config.WHITELISTED_USERS:
        user_states[user.id] = {
            'authenticated': True,
            'expires': datetime.now() + timedelta(minutes=config.LOGIN_EXPIRATION)
        }
        logger.info(f"User {user.id} ({username}) is whitelisted")
        await update.message.reply_text(
            f"Welcome {user.first_name}! You are whitelisted and have full access."
        )
    else:
        logger.info(f"User {user.id} ({username}) needs to login")
        await update.message.reply_text(
            f"Welcome {user.first_name}! Please use /login to authenticate."
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Help command requested by user {update.effective_user.id}")
    await update.message.reply_text(
        "I am a sensor monitoring bot. I can:\n"
        "- Monitor sensor data from CSV files\n"
        "- Alert you when values are out of range\n"
        "- Let you set custom thresholds\n"
        "- Adjust alert frequency\n\n"
        "Available commands:\n"
        "• /start - Start the bot and check authentication\n"
        "• /help - Show this help message\n"
        "• /login - Start the login process\n"
        "• /setrange temp_min temp_max hum_min hum_max light_min light_max - Set custom thresholds\n"
        "   Example: /setrange 15 30 0.3 0.9 1000 3000\n"
        "• /setalert minutes - Set alert frequency in minutes\n"
        "   Example: /setalert 60\n\n"
        "CSV File Format:\n"
        "The bot expects CSV files with columns: Time, Temperature, Humidity, Light\n"
        "Example:\n"
        "Time,Temperature,Humidity,Light\n"
        "2025-04-16 23:52:20,19.15,0.8,2008.95"
    )

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Remove @ from username if present
    username = user.username.lstrip('@') if user.username else None
    logger.info(f"Login attempt by user {user.id} ({username})")
    
    if username and username in config.WHITELISTED_USERS:
        logger.info(f"User {user.id} ({username}) is already whitelisted")
        await update.message.reply_text("You are already whitelisted!")
        return

    if user.id not in login_attempts:
        login_attempts[user.id] = 0
        logger.debug(f"Initialized login attempts for user {user.id}")

    if login_attempts[user.id] >= config.MAX_LOGIN_ATTEMPTS:
        logger.warning(f"User {user.id} exceeded maximum login attempts")
        await update.message.reply_text("Too many failed attempts. Please try again later.")
        return

    logger.info(f"Requesting login code from user {user.id}")
    await update.message.reply_text(
        "Please enter the login code. You have 3 attempts.\n"
        "The code will expire in 10 minutes after successful login."
    )

async def verify_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Remove @ from username if present
    username = user.username.lstrip('@') if user.username else None
    logger.info(f"Login verification attempt by user {user.id} ({username})")
    
    if username and username in config.WHITELISTED_USERS:
        logger.info(f"User {user.id} ({username}) is already whitelisted")
        await update.message.reply_text("You are already whitelisted!")
        return

    if user.id not in login_attempts:
        logger.warning(f"User {user.id} attempted verification without /login")
        await update.message.reply_text("Please use /login first.")
        return

    if update.message.text == config.LOGIN_CODE:
        logger.info(f"User {user.id} ({username}) successfully logged in")
        user_states[user.id] = {
            'authenticated': True,
            'expires': datetime.now() + timedelta(minutes=config.LOGIN_EXPIRATION)
        }
        login_attempts[user.id] = 0
        await update.message.reply_text(
            f"Login successful! Your session will expire in {config.LOGIN_EXPIRATION} minutes."
        )
    else:
        login_attempts[user.id] += 1
        logger.warning(f"Invalid login attempt by user {user.id}, attempt {login_attempts[user.id]}")
        remaining_attempts = config.MAX_LOGIN_ATTEMPTS - login_attempts[user.id]
        if remaining_attempts > 0:
            await update.message.reply_text(
                f"Invalid code. {remaining_attempts} attempts remaining."
            )
        else:
            await update.message.reply_text("Too many failed attempts. Please try again later.")

async def set_range(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"Set range attempt by user {user.id} ({user.username})")
    
    if not user_states.get(user.id, {}).get('authenticated'):
        logger.warning(f"Unauthorized set_range attempt by user {user.id}")
        await update.message.reply_text("Please authenticate first using /login")
        return

    if len(context.args) != 6:
        logger.warning(f"Invalid set_range arguments by user {user.id}: {context.args}")
        await update.message.reply_text(
            "Please provide all threshold values in the format:\n"
            "/setrange temp_min temp_max hum_min hum_max light_min light_max\n"
            "Example: /setrange 15 30 0.3 0.9 1000 3000"
        )
        return

    try:
        thresholds = {
            'temperature': {
                'min': float(context.args[0]),
                'max': float(context.args[1])
            },
            'humidity': {
                'min': float(context.args[2]),
                'max': float(context.args[3])
            },
            'light': {
                'min': float(context.args[4]),
                'max': float(context.args[5])
            }
        }
        user_thresholds[user.id] = thresholds
        logger.info(f"User {user.id} updated thresholds: {thresholds}")
        
        # Process the file immediately after setting thresholds
        data_file = Path(config.DATA_DIR) / "data.csv"
        if data_file.exists():
            logger.info(f"Processing file after threshold update for user {user.id}")
            event_handler = CSVHandler(context.application)
            await event_handler.process_file(str(data_file))
        
        await update.message.reply_text("Thresholds updated successfully!")
    except ValueError as e:
        logger.error(f"Invalid threshold values by user {user.id}: {context.args}", exc_info=True)
        await update.message.reply_text("Please provide valid numbers for all thresholds.")

async def set_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"Set alert attempt by user {user.id} ({user.username})")
    
    if not user_states.get(user.id, {}).get('authenticated'):
        logger.warning(f"Unauthorized set_alert attempt by user {user.id}")
        await update.message.reply_text("Please authenticate first using /login")
        return

    if len(context.args) != 1:
        logger.warning(f"Invalid set_alert arguments by user {user.id}: {context.args}")
        await update.message.reply_text("Please provide alert frequency in minutes: /setalert <minutes>")
        return

    try:
        frequency = int(context.args[0])
        if frequency < 1:
            logger.warning(f"Invalid frequency value by user {user.id}: {frequency}")
            await update.message.reply_text("Alert frequency must be at least 1 minute.")
            return
        user_alert_frequencies[user.id] = frequency
        logger.info(f"User {user.id} set alert frequency to {frequency} minutes")
        await update.message.reply_text(f"Alert frequency set to {frequency} minutes.")
    except ValueError as e:
        logger.error(f"Invalid frequency value by user {user.id}: {context.args[0]}", exc_info=True)
        await update.message.reply_text("Please provide a valid number of minutes.")

async def current_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"Current settings requested by user {user.id} ({user.username})")
    
    if not user_states.get(user.id, {}).get('authenticated'):
        logger.warning(f"Unauthorized current settings request by user {user.id}")
        await update.message.reply_text("Please authenticate first using /login")
        return

    # Get user's thresholds or use defaults
    thresholds = user_thresholds.get(user.id, config.DEFAULT_THRESHOLDS)
    frequency = user_alert_frequencies.get(user.id, config.DEFAULT_ALERT_FREQUENCY)
    
    # Format the message
    message = (
        "Current Settings:\n\n"
        f"Temperature Range: {thresholds['temperature']['min']} - {thresholds['temperature']['max']}°C\n"
        f"Humidity Range: {thresholds['humidity']['min']} - {thresholds['humidity']['max']}\n"
        f"Light Range: {thresholds['light']['min']} - {thresholds['light']['max']}\n"
        f"Alert Frequency: Every {frequency} minutes"
    )
    
    await update.message.reply_text(message)

def main():
    logger.info("Starting bot initialization")
    # Create data directory if it doesn't exist
    Path(config.DATA_DIR).mkdir(exist_ok=True)
    logger.info(f"Data directory created/verified: {config.DATA_DIR}")

    # Initialize bot
    application = Application.builder().token(config.BOT_TOKEN).build()
    logger.info("Bot application initialized")

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("login", login))
    application.add_handler(CommandHandler("setrange", set_range))
    application.add_handler(CommandHandler("setalert", set_alert))
    application.add_handler(CommandHandler("current", current_settings))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, verify_login))
    logger.info("Command handlers registered")

    # Start the CSV file watcher
    event_handler = CSVHandler(application)
    observer = Observer()
    observer.schedule(event_handler, config.DATA_DIR, recursive=False)
    observer.start()
    logger.info(f"CSV file watcher started in directory: {config.DATA_DIR}")

    # Check if data.csv exists and process it
    data_file = Path(config.DATA_DIR) / "data.csv"
    if data_file.exists():
        logger.info(f"Found existing data file: {data_file}")
        event_handler.process_file(str(data_file))

    # Start the bot
    logger.info("Starting bot polling")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 