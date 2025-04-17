# NPEC Sensor Monitoring Bot

A Telegram bot that monitors sensor data from CSV files and sends alerts when values exceed specified thresholds.

## Features

- **Real-time Monitoring**: Watches CSV files for changes and processes them automatically
- **Customizable Thresholds**: Set custom ranges for temperature, humidity, and light sensors
- **User Authentication**: Secure access with whitelisted users and temporary login codes
- **Configurable Alerts**: Adjust alert frequency and receive notifications when values are out of range
- **Docker Support**: Easy deployment using Docker and Docker Compose

## Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

## Configuration

1. Create a `.env` file with the following variables:
```env
BOT_TOKEN=your_telegram_bot_token
WHITELISTED_USERS=username1,username2
TEMP_CODE=your_temporary_code
```

2. The `data` directory should contain CSV files with the following format:
```csv
Time,Temperature,Humidity,Light
2025-04-16 23:52:20,19.15,0.8,2008.95
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/NPECbot.git
cd NPECbot
```

2. Build and run using Docker Compose:
```bash
./redeploy.sh
```

## Usage

### Bot Commands

- `/start` - Start the bot and check authentication
- `/login` - Start the login process
- `/setrange temp_min temp_max hum_min hum_max light_min light_max` - Set custom thresholds
  - Example: `/setrange 15 30 0.3 0.9 1000 3000`
- `/setalert minutes` - Set alert frequency in minutes
  - Example: `/setalert 60`
- `/current` - View current threshold settings
- `/help` - Show help message

### Authentication

1. Whitelisted users are automatically authenticated
2. Other users need to use `/login` and provide the temporary code
3. Sessions expire after a configurable time (default: 10 minutes)

### Alert System

- Alerts are sent when sensor values exceed the specified thresholds
- Alert frequency can be customized per user
- Multiple alerts are combined into a single message
- Alerts include the actual values that triggered them

## Development

### Project Structure

```
NPECbot/
├── bot.py              # Main bot implementation
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── Dockerfile         # Docker configuration
├── docker-compose.yml # Docker Compose configuration
├── redeploy.sh        # Deployment script
└── data/              # Directory for CSV files
```

### Running Locally

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the bot:
```bash
python bot.py
```