import logging
import multiprocessing
import time
import os
import sys
from flask import Flask, jsonify
from config import BOT_TOKEN
from database import init_db
import handlers.commands as commands
from datetime import datetime

# Force flush logging
logging.basicConfig(
    format='%(asime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize database
init_db()
commands.BOT_START_TIME = datetime.now()

# Global variable to track bot process
bot_process = None
bot_process_start_time = None

def run_bot_process():
    """Run the bot in a separate process using python-telegram-bot's built-in polling."""
    import asyncio
    from telegram.ext import Application
    from handlers import channel_handler, get_command_handlers, group_message_handler_obj, callback_handler
    
    logger.info("🚀 Bot process started")
    
    try:
        # Create application with default settings (works with polling)
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(channel_handler)
        for handler in get_command_handlers():
            application.add_handler(handler)
        application.add_handler(group_message_handler_obj)
        application.add_handler(callback_handler)
        
        # Start polling (this blocks)
        logger.info("Starting polling...")
        application.run_polling()
        
    except Exception as e:
        logger.exception(f"❌ Fatal error in bot process: {e}")
    finally:
        logger.info("🛑 Bot process stopped")

def start_bot():
    """Start the bot in a separate process."""
    global bot_process, bot_process_start_time
    if bot_process and bot_process.is_alive():
        logger.info("Bot process already running")
        return
    
    bot_process = multiprocessing.Process(target=run_bot_process, name="BotProcess")
    bot_process.daemon = True  # This will be ignored, but we keep it
    bot_process.start()
    bot_process_start_time = time.time()
    logger.info(f"Bot process started with PID: {bot_process.pid}")

# Start the bot process immediately
logger.info("🔄 Initializing bot...")
start_bot()

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    global bot_process
    
    # Check if process is alive, restart if dead
    if bot_process and not bot_process.is_alive():
        logger.warning("Bot process died, restarting...")
        start_bot()
    
    process_alive = bot_process.is_alive() if bot_process else False
    uptime = time.time() - bot_process_start_time if bot_process_start_time and process_alive else 0
    
    return jsonify({
        "status": "healthy",
        "bot_process_alive": process_alive,
        "bot_process_pid": bot_process.pid if bot_process else None,
        "bot_uptime_seconds": uptime
    }), 200

@app.route('/debug', methods=['GET'])
def debug():
    """Debug endpoint."""
    global bot_process
    return jsonify({
        "bot_process_alive": bot_process.is_alive() if bot_process else False,
        "bot_process_pid": bot_process.pid if bot_process else None,
        "bot_process_start_time": bot_process_start_time
    }), 200

@app.route('/', methods=['GET'])
def index():
    return "📚 Telegram PDF Library Bot is running with polling (multiprocessing)."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting Flask on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
