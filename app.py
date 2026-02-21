import logging
import threading
import os
import sys
import time
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

# Global flag to restart bot if it dies
bot_thread = None
stop_bot = False

def run_bot():
    """Run the bot in a background thread with auto-restart."""
    while not stop_bot:
        try:
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
            updater = Updater(BOT_TOKEN, use_context=True)
            dp = updater.dispatcher
            dp.add_handler(CommandHandler("start", start))
            dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
            dp.add_error_handler(error_handler)

            updater.start_polling()
            logger.info("✅ Bot is polling!")
            updater.idle()  # This blocks until the bot stops
            logger.warning("Bot idle returned – possibly stopped.")
        except Exception as e:
            logger.exception(f"❌ Bot thread error: {e}")
            logger.info("Restarting bot in 5 seconds...")
            time.sleep(5)

def start_bot_thread():
    global bot_thread
    bot_thread = threading.Thread(target=run_bot, daemon=True, name="BotThread")
    bot_thread.start()
    logger.info(f"Bot thread started: {bot_thread.ident}")

start_bot_thread()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "bot_thread_alive": bot_thread.is_alive() if bot_thread else False
    }), 200

@app.route('/', methods=['GET'])
def index():
    return "📚 Telegram PDF Library Bot is running."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
