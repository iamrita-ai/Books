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
bot_ready = threading.Event()  # Signal that bot is fully initialized

init_db()
commands.BOT_START_TIME = datetime.now()

def start_bot():
    global bot_app, loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Build application without updater (webhook mode)
    bot_app = Application.builder().token(BOT_TOKEN).updater(None).build()

    # Add handlers
    bot_app.add_handler(channel_handler)
    for handler in get_command_handlers():
        bot_app.add_handler(handler)
    bot_app.add_handler(group_message_handler_obj)
    bot_app.add_handler(callback_handler)

    # Initialize and start the bot
    loop.run_until_complete(bot_app.initialize())
    loop.run_until_complete(bot_app.start())

    # Set webhook
    async def set_webhook():
        await bot_app.bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"Webhook set to {WEBHOOK_URL}")
    loop.run_until_complete(set_webhook())

    # Signal that the bot is ready
    bot_ready.set()
    logger.info("Bot started in background thread")

    # Keep the event loop running forever
    loop.run_forever()

# Start bot in a background daemon thread
thread = threading.Thread(target=start_bot, daemon=True)
thread.start()

@app.route('/webhook', methods=['POST'])
def webhook():
    # Wait for bot to be ready (max 10 seconds)
    if not bot_ready.wait(timeout=10):
        logger.error("Bot not ready within timeout")
        return "Bot not ready", 503

    # Double-check that bot_app and loop are present
    if not bot_app or not loop:
        logger.error("bot_app or loop is None despite ready event")
        return "Bot not ready", 503

    data = request.get_json(force=True)
    update = Update.de_json(data, bot_app.bot)

    # Submit the update to the bot's event loop
    asyncio.run_coroutine_threadsafe(bot_app.process_update(update), loop)
    return "OK", 200

@app.route('/health', methods=['GET'])
def health():
    status = "ready" if bot_ready.is_set() else "starting"
    return jsonify({"status": status}), 200

@app.route('/', methods=['GET'])
def index():
    return "Telegram PDF Library Bot is running."
