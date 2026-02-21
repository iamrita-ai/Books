import logging
import multiprocessing
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

# Bot token from environment
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("BOT_TOKEN not set!")
    sys.exit(1)

# ------------------ Bot Process ------------------
def run_bot():
    """Run the bot in a separate process."""
    # Import telegram here to avoid interfering with Flask
    from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
    
    def start(update, context):
        update.message.reply_text("✅ Bot is working!")
        logger.info(f"Start from {update.effective_user.id}")
    
    def echo(update, context):
        if update.message and update.message.text:
            update.message.reply_text(f"You said: {update.message.text}")
            logger.info(f"Echo: {update.message.text}")
    
    def error_handler(update, context):
        logger.error(f"Update {update} caused error {context.error}")
    
    logger.info("🚀 Starting bot process...")
    try:
        updater = Updater(BOT_TOKEN, use_context=True)
        dp = updater.dispatcher
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
        dp.add_error_handler(error_handler)
        
        logger.info("Starting polling...")
        updater.start_polling()
        logger.info("✅ Bot is polling!")
        updater.idle()
    except Exception as e:
        logger.exception(f"❌ Bot process error: {e}")

# Start bot process
bot_process = multiprocessing.Process(target=run_bot, name="BotProcess")
bot_process.daemon = True  # Will be killed when main process exits
bot_process.start()
logger.info(f"Bot process started with PID: {bot_process.pid}")

# ------------------ Flask Web Server ------------------
@app.route('/health', methods=['GET'])
def health():
    """Health check for Render."""
    return jsonify({
        "status": "healthy",
        "bot_process_alive": bot_process.is_alive(),
        "bot_pid": bot_process.pid
    }), 200

@app.route('/', methods=['GET'])
def index():
    return "📚 Telegram PDF Library Bot is running."

# This is the critical part for Render – bind to PORT
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
