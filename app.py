import logging
import threading
import os
import sys
import time
from flask import Flask, jsonify

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("BOT_TOKEN not set!")
    sys.exit(1)

# Import database and handlers
from database import init_db
from handlers import channel_handler, get_command_handlers, group_message_handler_obj, callback_handler
from config import BOT_NAME
import datetime

# Initialize database
init_db()
BOT_START_TIME = datetime.datetime.now()

# Global flag to control bot thread
bot_running = True
bot_thread = None

def run_bot():
    """Run the bot in a background thread without idle()."""
    from telegram.ext import Updater

    logger.info("🚀 Starting bot thread...")
    try:
        updater = Updater(BOT_TOKEN, use_context=True)
        dp = updater.dispatcher

        # Add handlers
        dp.add_handler(channel_handler)
        for handler in get_command_handlers():
            dp.add_handler(handler)
        dp.add_handler(group_message_handler_obj)
        dp.add_handler(callback_handler)

        # Start polling
        updater.start_polling()
        logger.info("✅ Bot is polling!")

        # Keep the thread alive without using idle()
        while bot_running:
            time.sleep(10)
            logger.debug("Bot thread heartbeat")

    except Exception as e:
        logger.exception(f"❌ Bot thread error: {e}")

def start_bot_thread():
    global bot_thread
    bot_thread = threading.Thread(target=run_bot, daemon=True, name="BotThread")
    bot_thread.start()
    logger.info(f"Bot thread started: {bot_thread.ident}")

# Start the bot thread
start_bot_thread()

# ==================== Flask Web Server ====================
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "bot_thread_alive": bot_thread.is_alive() if bot_thread else False
    }), 200

@app.route('/', methods=['GET'])
def index():
    return f"📚 {BOT_NAME} is running. Add me to a group to search for PDFs."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
