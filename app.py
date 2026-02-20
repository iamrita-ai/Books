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

bot_app = None
loop = None

init_db()
commands.BOT_START_TIME = datetime.now()

def start_bot():
    global bot_app, loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # ✅ FIX: Disable updater to avoid AttributeError
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

    logger.info("Bot started in background thread")
    loop.run_forever()

thread = threading.Thread(target=start_bot, daemon=True)
thread.start()

@app.route('/webhook', methods=['POST'])
def webhook():
    if not bot_app or not loop:
        return "Bot not ready", 503

    data = request.get_json(force=True)
    update = Update.de_json(data, bot_app.bot)
    asyncio.run_coroutine_threadsafe(bot_app.process_update(update), loop)
    return "OK", 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

@app.route('/', methods=['GET'])
def index():
    return "Telegram PDF Library Bot is running."
