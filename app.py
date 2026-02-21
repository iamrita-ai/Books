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

# ------------------ Bot Thread ------------------
def run_bot():
    """Run the bot in a background thread."""
    # Import telegram here so Flask can start first
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
    
    logger.info("🚀 Starting bot thread...")
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
        logger.exception(f"❌ Bot thread error: {e}")

# Start bot thread (daemon so it exits when Flask stops)
bot_thread = threading.Thread(target=run_bot, daemon=True, name="BotThread")
bot_thread.start()
logger.info(f"Bot thread started: {bot_thread.ident}")

# ------------------ Flask Web Server ------------------
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "bot_thread_alive": bot_thread.is_alive()
    }), 200

@app.route('/', methods=['GET'])
def index():
    return "📚 Telegram PDF Library Bot is running."

# Bind to PORT for Render
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"Starting Flask on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
