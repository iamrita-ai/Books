import logging
import threading
import os
import sys
import time
import fcntl
import atexit
from flask import Flask, jsonify

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

from database import init_db
from handlers import (
    source_group_handler_obj,
    get_command_handlers,
    group_message_handler_obj,
    callback_handler
)
from config import BOT_NAME
import datetime

init_db()
BOT_START_TIME = datetime.datetime.now()

LOCK_FILE = '/tmp/bot.lock'

def acquire_lock():
    try:
        global lock_fp
        lock_fp = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fp.write(str(os.getpid()))
        lock_fp.flush()
        return True
    except (IOError, OSError):
        try:
            with open(LOCK_FILE, 'r') as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 0)
            return False
        except (ProcessLookupError, ValueError, FileNotFoundError, IOError):
            try:
                os.remove(LOCK_FILE)
            except:
                pass
            return acquire_lock()

def release_lock():
    try:
        fcntl.flock(lock_fp, fcntl.LOCK_UN)
        lock_fp.close()
        os.remove(LOCK_FILE)
    except:
        pass

atexit.register(release_lock)

bot_thread = None
updater_instance = None
bot_running = True

def run_bot():
    global updater_instance
    if not acquire_lock():
        logger.warning("Another bot instance is already running. Exiting this thread.")
        return

    logger.info("🚀 Starting bot thread (lock acquired).")
    from telegram.ext import Updater
    from telegram.error import Conflict

    while bot_running:
        try:
            updater = Updater(BOT_TOKEN, use_context=True)
            updater_instance = updater
            dp = updater.dispatcher

            dp.add_handler(source_group_handler_obj)
            for handler in get_command_handlers():
                dp.add_handler(handler)
            dp.add_handler(group_message_handler_obj)
            dp.add_handler(callback_handler)

            # ✅ CORRECT ERROR CALLBACK (update, context)
            def error_callback(update, context):
                try:
                    if update is not None:
                        update_id = update.update_id if hasattr(update, 'update_id') else 'N/A'
                        logger.error(f"Update {update_id} caused error: {context.error}")
                    else:
                        logger.error(f"Error without update: {context.error}")
                except Exception as e:
                    logger.error(f"Error in error callback: {e}")
                
                if isinstance(context.error, Conflict):
                    logger.critical("Conflict detected – restarting updater in 30s")
                    updater.stop()

            dp.add_error_handler(error_callback)

            logger.info("Starting polling...")
            updater.start_polling(
                poll_interval=1.0,
                timeout=30,
                drop_pending_updates=True,
                bootstrap_retries=3
            )
            logger.info("✅ Bot is polling and ready!")

            while bot_running:
                time.sleep(10)
                logger.debug("Bot thread heartbeat - lock held")

            updater.stop()
            break

        except Conflict as e:
            logger.error(f"Conflict on startup: {e}. Waiting 30 seconds...")
            time.sleep(30)
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            time.sleep(10)

    release_lock()
    logger.info("Bot thread exiting, lock released.")

def start_bot_thread():
    global bot_thread
    bot_thread = threading.Thread(target=run_bot, daemon=True, name="BotThread")
    bot_thread.start()
    logger.info(f"Bot thread started with ID: {bot_thread.ident}")

start_bot_thread()

@app.route('/health', methods=['GET'])
def health():
    thread_alive = bot_thread.is_alive() if bot_thread else False
    return jsonify({
        "status": "healthy" if thread_alive else "degraded",
        "bot_thread_alive": thread_alive,
        "uptime_seconds": (datetime.datetime.now() - BOT_START_TIME).seconds
    }), 200

@app.route('/', methods=['GET'])
def index():
    return f"📚 {BOT_NAME} is running. Add me to a group to search for PDFs."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
