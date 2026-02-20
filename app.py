import asyncio
import threading
import logging
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application
from config import BOT_TOKEN, WEBHOOK_URL
from database import init_db
from handlers import channel_handler, get_command_handlers, group_message_handler_obj, callback_handler
import handlers.commands as commands
from datetime import datetime

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global bot objects and ready event
bot_app = None
loop = None
bot_ready = threading.Event()

init_db()
commands.BOT_START_TIME = datetime.now()

def start_bot():
    global bot_app, loop
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        bot_app = Application.builder().token(BOT_TOKEN).updater(None).build()

        bot_app.add_handler(channel_handler)
        for handler in get_command_handlers():
            bot_app.add_handler(handler)
        bot_app.add_handler(group_message_handler_obj)
        bot_app.add_handler(callback_handler)

        loop.run_until_complete(bot_app.initialize())
        loop.run_until_complete(bot_app.start())

        async def set_webhook():
            await bot_app.bot.set_webhook(url=WEBHOOK_URL)
            logger.info(f"Webhook set to {WEBHOOK_URL}")
        loop.run_until_complete(set_webhook())

        bot_ready.set()
        logger.info("Bot started in background thread - event set")
    except Exception as e:
        logger.exception(f"Fatal error in start_bot: {e}")
        return

    loop.run_forever()

thread = threading.Thread(target=start_bot, daemon=True)
thread.start()

# ✅ FIX: Explicitly allow POST methods on the webhook route
@app.route('/webhook', methods=['POST'])
def webhook():
    logger.debug(f"Webhook received, event is_set: {bot_ready.is_set()}")
    
    if not bot_ready.wait(timeout=10):
        logger.error("Bot not ready within timeout")
        return "Bot not ready", 503

    if not bot_app or not loop:
        logger.error("bot_app or loop is None despite ready event")
        return "Bot not ready", 503

    try:
        data = request.get_json(force=True)
        logger.debug(f"Received update: {data.get('update_id')}")
        update = Update.de_json(data, bot_app.bot)
        asyncio.run_coroutine_threadsafe(bot_app.process_update(update), loop)
        return "OK", 200
    except Exception as e:
        logger.exception(f"Error processing webhook: {e}")
        return "Error", 500

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    status = "ready" if bot_ready.is_set() else "starting"
    return jsonify({"status": status}), 200

# Root endpoint
@app.route('/', methods=['GET'])
def index():
    return "Telegram PDF Library Bot is running."

# Add a catch-all for debugging (optional, remove in production)
@app.route('/webhook', methods=['GET'])
def webhook_get():
    return "Webhook endpoint accepts POST only", 405
