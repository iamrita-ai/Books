import logging
import threading
import os
import sys
import time
import fcntl  # for file locking (Linux only, works on Render)
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
updater_instance = None

# File lock path (must be in a writable location)
LOCK_FILE = '/tmp/bot.lock'

def acquire_lock():
    """Try to acquire a file lock. Returns True if successful, False otherwise."""
    try:
        global lock_fp
        lock_fp = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except (IOError, OSError):
        return False

def release_lock():
    """Release the file lock."""
    try:
        fcntl.flock(lock_fp, fcntl.LOCK_UN)
        lock_fp.close()
    except:
        pass

def run_bot():
    """Run the bot in a background thread with automatic recovery."""
    global updater_instance
    from telegram.ext import Updater
    from telegram.error import Conflict, NetworkError, TelegramError

    # Try to acquire the lock – if not, this thread exits silently.
    if not acquire_lock():
        logger.warning("Another bot instance is already running. Exiting this thread.")
        return

    logger.info("🚀 Starting bot thread (lock acquired).")
    
    # Outer loop for auto‑restart
    while bot_running:
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

            # Error handler to log and possibly restart
            def error_callback(update, context):
                logger.error(f"Update {update} caused error {context.error}")
                if isinstance(context.error, Conflict):
                    logger.critical("Conflict detected – updater will stop.")
                    # Force stop the updater (it will be restarted by the outer loop)
                    updater.stop()

            dp.add_error_handler(error_callback)

            # Start polling with recommended settings
            logger.info("Starting polling...")
            updater.start_polling(
                poll_interval=1.0,
                timeout=30,
                drop_pending_updates=True,  # replaces deprecated 'clean'
                bootstrap_retries=3
            )
            logger.info("✅ Bot is polling and ready to receive updates!")

            # Keep thread alive; updater runs in its own threads.
            while bot_running:
                time.sleep(10)
                logger.debug("Bot thread heartbeat - lock held")

            # If we exit the loop, stop the updater and release lock
            updater.stop()
            break

        except Conflict as e:
            logger.error(f"Conflict on startup: {e}. Waiting 30 seconds...")
            time.sleep(30)
        except NetworkError as e:
            logger.error(f"Network error: {e}. Retrying in 15 seconds...")
            time.sleep(15)
        except Exception as e:
            logger.exception(f"Unexpected error in bot thread: {e}")
            time.sleep(10)

    # Release the lock when the thread exits
    release_lock()
    logger.info("Bot thread exiting, lock released.")

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
