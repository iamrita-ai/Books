import logging
import threading
import os
import sys
from flask import Flask, jsonify

# ---------- FIX: Add dummy imghdr module ----------
import sys
from types import ModuleType
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

dummy_imghdr = ModuleType('imghdr')
def what(file, h=None):
    return None
dummy_imghdr.what = what
sys.modules['imghdr'] = dummy_imghdr
# --------------------------------------------------

# ---------- FIX: Add dummy pkg_resources module (for APScheduler) ----------
dummy_pkg_resources = ModuleType('pkg_resources')
def get_distribution(dist):
    # Return a dummy object with version
    class DummyDist:
        version = '0.0.0'
    return DummyDist()
dummy_pkg_resources.get_distribution = get_distribution
# Also define DistributionNotFound exception
class DistributionNotFound(Exception):
    pass
dummy_pkg_resources.DistributionNotFound = DistributionNotFound
sys.modules['pkg_resources'] = dummy_pkg_resources
# --------------------------------------------------------------------------

# Now import telegram (it will find the dummy modules)
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

# Simple handler functions
def start(update, context):
    update.message.reply_text(
        "👋 Hello! I'm a PDF library bot.\n"
        "Add me to a group and send any part of a book name to search."
    )
    logger.info(f"Start command from {update.effective_user.id}")

def help_command(update, context):
    update.message.reply_text(
        "📚 *How to use:*\n"
        "• In a group, type any part of a book title to search.\n"
        "• Click on a result button to get the PDF.\n"
        "• Commands: /start, /help"
    )
    logger.info(f"Help command from {update.effective_user.id}")

def echo(update, context):
    if update.message and update.message.text:
        update.message.reply_text(f"You said: {update.message.text}")
        logger.info(f"Echo: {update.message.text}")

def error_handler(update, context):
    logger.error(f"Update {update} caused error {context.error}")

def start_bot():
    """Run the bot in a background thread."""
    logger.info("🚀 Starting bot with Updater...")
    try:
        updater = Updater(BOT_TOKEN, use_context=True)
        dp = updater.dispatcher
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("help", help_command))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
        dp.add_error_handler(error_handler)
        logger.info("Starting polling...")
        updater.start_polling()
        logger.info("✅ Bot is running and polling!")
        updater.idle()
    except Exception as e:
        logger.exception(f"❌ Fatal error in bot thread: {e}")

# Start bot in background thread
bot_thread = threading.Thread(target=start_bot, daemon=True, name="BotThread")
bot_thread.start()
logger.info(f"Bot thread started: {bot_thread.ident}")

@app.route('/health', methods=['GET'])
def health():
    thread_alive = bot_thread.is_alive() if bot_thread else False
    return jsonify({
        "status": "healthy",
        "bot_thread_alive": thread_alive
    }), 200

@app.route('/', methods=['GET'])
def index():
    return "📚 Telegram PDF Library Bot is running."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting Flask on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
