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
updater_instance = None  # Store updater reference

def run_bot():
    """Run the bot in a background thread."""
    global updater_instance
    from telegram.ext import Updater
    from telegram.error import Conflict, NetworkError

    logger.info("🚀 Starting bot thread...")
    
    # Add retry mechanism for polling
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries and bot_running:
        try:
            updater = Updater(BOT_TOKEN, use_context=True)
            updater_instance = updater
            dp = updater.dispatcher

            # Add all handlers
            dp.add_handler(channel_handler)
            for handler in get_command_handlers():
                dp.add_handler(handler)
            dp.add_handler(group_message_handler_obj)
            dp.add_handler(callback_handler)

            # Start polling with proper settings
            logger.info("Starting polling...")
            updater.start_polling(
                poll_interval=1.0,
                timeout=30,
                clean=True,
                bootstrap_retries=3
            )
            logger.info("✅ Bot is polling and ready to receive updates!")
            
            # Keep thread alive without using idle()
            while bot_running:
                time.sleep(10)
                logger.debug("Bot thread heartbeat - still alive")
                
            # If we exit the loop, stop polling
            updater.stop()
            break
            
        except Conflict as e:
            retry_count += 1
            logger.error(f"Conflict error (attempt {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                logger.info("Waiting 10 seconds before retry...")
                time.sleep(10)
            else:
                logger.critical("Max retries reached. Bot thread stopping.")
                
        except NetworkError as e:
            retry_count += 1
            logger.error(f"Network error (attempt {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                logger.info("Waiting 5 seconds before retry...")
                time.sleep(5)
                
        except Exception as e:
            logger.exception(f"❌ Unexpected bot thread error: {e}")
            time.sleep(10)  # Wait before restarting
            retry_count += 1

def start_bot_thread():
    global bot_thread
    bot_thread = threading.Thread(target=run_bot, daemon=True, name="BotThread")
    bot_thread.start()
    logger.info(f"Bot thread started with ID: {bot_thread.ident}")

# Start the bot thread
start_bot_thread()

# ==================== Flask Web Server ====================
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint with detailed status."""
    thread_alive = bot_thread.is_alive() if bot_thread else False
    return jsonify({
        "status": "healthy" if thread_alive else "degraded",
        "bot_thread_alive": thread_alive,
        "uptime_seconds": (datetime.datetime.now() - BOT_START_TIME).seconds,
        "updater_running": updater_instance is not None
    }), 200

@app.route('/', methods=['GET'])
def index():
    return f"📚 {BOT_NAME} is running. Add me to a group to search for PDFs."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"Starting Flask on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
