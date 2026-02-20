import asyncio
import threading
import logging
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import Application, ContextTypes
from config import BOT_TOKEN, WEBHOOK_URL
from database import init_db
from handlers import channel_handler, get_command_handlers, group_message_handler_obj, callback_handler
import handlers.commands as commands  # to set BOT_START_TIME
from datetime import datetime

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Global variables for bot and event loop
bot_app = None
loop = None

# Initialize DB
init_db()

# Store bot start time
commands.BOT_START_TIME = datetime.now()

def start_bot():
    global bot_app, loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Build application
    bot_app = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    bot_app.add_handler(channel_handler)
    for handler in get_command_handlers():
        bot_app.add_handler(handler)
    bot_app.add_handler(group_message_handler_obj)
    bot_app.add_handler(callback_handler)

    # Start bot
    loop.run_until_complete(bot_app.initialize())
    loop.run_until_complete(bot_app.start())

    # Set webhook
    async def set_webhook():
        await bot_app.bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"Webhook set to {WEBHOOK_URL}")
    loop.run_until_complete(set_webhook())

    logger.info("Bot started in background thread")
    loop.run_forever()

# Start bot in background thread
thread = threading.Thread(target=start_bot, daemon=True)
thread.start()

@app.route('/webhook', methods=['POST'])
def webhook():
    if not bot_app or not loop:
        return "Bot not ready", 503

    data = request.get_json(force=True)
    # Create update object
    update = Update.de_json(data, bot_app.bot)

    # Process update in bot's event loop
    asyncio.run_coroutine_threadsafe(bot_app.process_update(update), loop)
    return "OK", 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

@app.route('/', methods=['GET'])
def index():
    return "Telegram PDF Library Bot is running."

if __name__ == '__main__':
    # For local testing, use polling; on Render, we use webhook via Flask.
    # This file will be run by gunicorn, so we don't call app.run().
    pass
