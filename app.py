import asyncio
import logging
import threading
from flask import Flask, jsonify
from telegram.ext import Application
from config import BOT_TOKEN
from database import init_db
from handlers import channel_handler, get_command_handlers, group_message_handler_obj, callback_handler
import handlers.commands as commands
from datetime import datetime
import os

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize database
init_db()
commands.BOT_START_TIME = datetime.now()

bot_app = None
polling_thread = None

def run_polling():
    """Run the bot with polling in a background thread."""
    global bot_app
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Build application with updater (for polling)
    bot_app = Application.builder().token(BOT_TOKEN).build()
    
    # Add all handlers
    bot_app.add_handler(channel_handler)
    for handler in get_command_handlers():
        bot_app.add_handler(handler)
    bot_app.add_handler(group_message_handler_obj)
    bot_app.add_handler(callback_handler)
    
    logger.info("🚀 Starting polling...")
    bot_app.run_polling()

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "polling_alive": polling_thread.is_alive() if polling_thread else False
    }), 200

@app.route('/', methods=['GET'])
def index():
    return "📚 Telegram PDF Library Bot is running with polling."

if __name__ == '__main__':
    # Start polling in a background daemon thread
    polling_thread = threading.Thread(target=run_polling, daemon=True)
    polling_thread.start()
    
    # Run Flask in the main thread
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
