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
import sys

# Force flush logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize database
init_db()
commands.BOT_START_TIME = datetime.now()

bot_app = None
polling_thread = None
polling_active = False

def run_polling():
    """Run the bot with polling in a background thread."""
    global bot_app, polling_active
    logger.info("🚀 Polling thread started")
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Build application with updater (for polling)
        logger.info("Building application...")
        bot_app = Application.builder().token(BOT_TOKEN).build()
        
        # Add all handlers
        logger.info("Adding handlers...")
        bot_app.add_handler(channel_handler)
        for handler in get_command_handlers():
            bot_app.add_handler(handler)
            logger.debug(f"Added handler: {handler}")
        bot_app.add_handler(group_message_handler_obj)
        bot_app.add_handler(callback_handler)
        
        logger.info("🚀 Starting polling...")
        polling_active = True
        bot_app.run_polling()
        
    except Exception as e:
        logger.exception(f"❌ Fatal error in polling thread: {e}")
        polling_active = False
    finally:
        logger.info("🛑 Polling thread stopped")

def start_polling():
    """Start polling in a background thread."""
    global polling_thread
    polling_thread = threading.Thread(target=run_polling, daemon=True, name="PollingThread")
    polling_thread.start()
    logger.info(f"Polling thread started with ID: {polling_thread.ident}")

# ⚠️ IMPORTANT: Start polling at module level, not inside __main__
logger.info("🔄 Initializing bot...")
start_polling()

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    thread_alive = polling_thread.is_alive() if polling_thread else False
    return jsonify({
        "status": "healthy",
        "polling_alive": thread_alive,
        "polling_active": polling_active,
        "bot_app_initialized": bot_app is not None
    }), 200

@app.route('/debug', methods=['GET'])
def debug():
    """Debug endpoint to check thread status."""
    thread_status = {
        "polling_thread_alive": polling_thread.is_alive() if polling_thread else False,
        "polling_thread_name": polling_thread.name if polling_thread else None,
        "polling_active": polling_active,
        "bot_app": str(bot_app) if bot_app else None,
        "total_threads": threading.active_count(),
        "threads": [t.name for t in threading.enumerate()]
    }
    return jsonify(thread_status), 200

@app.route('/', methods=['GET'])
def index():
    return "📚 Telegram PDF Library Bot is running with polling."

# This block still runs when executed directly (for local testing)
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting Flask on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
