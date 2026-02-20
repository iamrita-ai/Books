import asyncio
import logging
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application
from config import BOT_TOKEN, WEBHOOK_URL
from database import init_db
from handlers import channel_handler, get_command_handlers, group_message_handler_obj, callback_handler
import handlers.commands as commands
from datetime import datetime
import threading

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize database
init_db()
commands.BOT_START_TIME = datetime.now()

# Global bot application
bot_app = None

async def init_bot():
    """Initialize bot application"""
    global bot_app
    
    # Build application without updater
    bot_app = Application.builder().token(BOT_TOKEN).updater(None).build()
    
    # Add handlers
    bot_app.add_handler(channel_handler)
    for handler in get_command_handlers():
        bot_app.add_handler(handler)
    bot_app.add_handler(group_message_handler_obj)
    bot_app.add_handler(callback_handler)
    
    # Initialize
    await bot_app.initialize()
    await bot_app.start()
    
    # Set webhook
    await bot_app.bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"Webhook set to {WEBHOOK_URL}")
    
    return bot_app

def run_bot():
    """Run bot in event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_bot())
    logger.info("Bot started")
    # Keep loop running but don't block Flask
    threading.Thread(target=loop.run_forever, daemon=True).start()

# Start bot in background
threading.Thread(target=run_bot, daemon=True).start()

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook updates"""
    global bot_app
    
    if not bot_app:
        logger.error("Bot not initialized")
        return "Bot not ready", 503
    
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, bot_app.bot)
        
        # Process update synchronously in Flask thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot_app.process_update(update))
        loop.close()
        
        return "OK", 200
    except Exception as e:
        logger.exception(f"Error processing update: {e}")
        return "Error", 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "bot_ready": bot_app is not None}), 200

@app.route('/', methods=['GET'])
def index():
    return "Telegram PDF Library Bot is running."

# For local testing
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
