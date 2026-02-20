import logging
import threading
import time
import os
import sys
from flask import Flask, jsonify
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Bot token from environment
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("BOT_TOKEN not set!")
    sys.exit(1)

# Global updater reference
updater = None
bot_thread = None

# Simple handler functions
def start(update, context):
    """Handle /start command."""
    update.message.reply_text(
        "👋 Hello! I'm a PDF library bot.\n"
        "Add me to a group and send any part of a book name to search."
    )
    logger.info(f"Start command from {update.effective_user.id}")

def help_command(update, context):
    """Handle /help command."""
    update.message.reply_text(
        "📚 *How to use:*\n"
        "• In a group, type any part of a book title to search.\n"
        "• Click on a result button to get the PDF.\n"
        "• Commands: /start, /help"
    )
    logger.info(f"Help command from {update.effective_user.id}")

def echo(update, context):
    """Echo any text message (for testing)."""
    if update.message and update.message.text:
        update.message.reply_text(f"You said: {update.message.text}")
        logger.info(f"Echo: {update.message.text}")

def error_handler(update, context):
    """Log errors."""
    logger.error(f"Update {update} caused error {context.error}")

def start_bot():
    """Start the bot in a background thread."""
    global updater
    logger.info("🚀 Starting bot with Updater...")
    
    try:
        # Create Updater (synchronous)
        updater = Updater(BOT_TOKEN, use_context=True)
        dp = updater.dispatcher
        
        # Add handlers
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("help", help_command))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
        dp.add_error_handler(error_handler)
        
        # Start polling
        logger.info("Starting polling...")
        updater.start_polling()
        logger.info("Bot is running!")
        
        # Keep thread alive
        while True:
            time.sleep(10)
            logger.debug("Bot thread heartbeat")
            
    except Exception as e:
        logger.exception(f"❌ Fatal error in bot thread: {e}")

# Start bot in background thread
bot_thread = threading.Thread(target=start_bot, daemon=True, name="BotThread")
bot_thread.start()
logger.info(f"Bot thread started: {bot_thread.ident}")

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    thread_alive = bot_thread.is_alive() if bot_thread else False
    return jsonify({
        "status": "healthy",
        "bot_thread_alive": thread_alive,
        "updater_running": updater is not None
    }), 200

@app.route('/debug', methods=['GET'])
def debug():
    """Debug endpoint."""
    return jsonify({
        "bot_thread_alive": bot_thread.is_alive() if bot_thread else False,
        "bot_thread_name": bot_thread.name if bot_thread else None,
        "updater": str(updater) if updater else None,
        "total_threads": threading.active_count(),
        "threads": [t.name for t in threading.enumerate()]
    }), 200

@app.route('/', methods=['GET'])
def index():
    return "📚 Telegram PDF Library Bot is running with synchronous Updater."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting Flask on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
