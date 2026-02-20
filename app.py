import logging
import subprocess
import sys
import time
import os
from flask import Flask, jsonify
from database import init_db
import handlers.commands as commands
from datetime import datetime

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

# Global variable to track bot subprocess
bot_process = None
bot_process_start_time = None

def start_bot_subprocess():
    """Start the bot as a separate subprocess."""
    global bot_process, bot_process_start_time
    
    # Path to the bot script
    bot_script = os.path.join(os.path.dirname(__file__), 'bot_runner.py')
    
    # Create the bot runner script if it doesn't exist
    if not os.path.exists(bot_script):
        with open(bot_script, 'w') as f:
            f.write('''#!/usr/bin/env python3
import asyncio
import logging
import sys
from telegram.ext import Application
from config import BOT_TOKEN
from handlers import channel_handler, get_command_handlers, group_message_handler_obj, callback_handler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def main():
    """Run the bot with polling."""
    logger.info("🚀 Bot subprocess started")
    
    try:
        # Create application with default settings
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
        logger.exception(f"❌ Fatal error in bot subprocess: {e}")
    finally:
        logger.info("🛑 Bot subprocess stopped")

if __name__ == '__main__':
    main()
''')
        os.chmod(bot_script, 0o755)  # Make executable
    
    # Start the subprocess
    if bot_process and bot_process.poll() is None:
        logger.info("Bot subprocess already running")
        return
    
    bot_process = subprocess.Popen(
        [sys.executable, bot_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    bot_process_start_time = time.time()
    logger.info(f"Bot subprocess started with PID: {bot_process.pid}")

# Start the bot subprocess immediately
logger.info("🔄 Initializing bot...")
start_bot_subprocess()

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    global bot_process
    
    # Check if process is running, restart if dead
    if bot_process:
        poll = bot_process.poll()
        if poll is not None:
            logger.warning(f"Bot subprocess died with code {poll}, restarting...")
            start_bot_subprocess()
    
    process_alive = bot_process and bot_process.poll() is None
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
    return jsonify({
        "bot_process_alive": bot_process and bot_process.poll() is None,
        "bot_process_pid": bot_process.pid if bot_process else None,
        "bot_process_start_time": bot_process_start_time
    }), 200

@app.route('/', methods=['GET'])
def index():
    return "📚 Telegram PDF Library Bot is running with polling (subprocess)."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting Flask on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
