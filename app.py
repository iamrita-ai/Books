import logging
import threading
import os
import sys
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

# Import telegram (Python 3.11 mein imghdr exists)
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

def start(update, context):
    update.message.reply_text("Bot is working! 🎉")
    logger.info(f"Start from {update.effective_user.id}")

def echo(update, context):
    if update.message and update.message.text:
        update.message.reply_text(f"You said: {update.message.text}")
        logger.info(f"Echo: {update.message.text}")

def error_handler(update, context):
    logger.error(f"Update {update} caused error {context.error}")

def start_bot():
    logger.info("🚀 Starting bot...")
    try:
        updater = Updater(BOT_TOKEN, use_context=True)
        dp = updater.dispatcher
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
        dp.add_error_handler(error_handler)
        updater.start_polling()
        logger.info("✅ Bot is polling!")
        updater.idle()
    except Exception as e:
        logger.exception(f"❌ Fatal error: {e}")

thread = threading.Thread(target=start_bot, daemon=True)
thread.start()
logger.info("Bot thread started")

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "thread_alive": thread.is_alive()}), 200

@app.route('/', methods=['GET'])
def index():
    return "📚 Telegram Bot is running."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
