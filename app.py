import asyncio
import logging
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot_app = None

async def init_bot():
    global bot_app
    bot_app = Application.builder().token(BOT_TOKEN).updater(None).build()
    await bot_app.initialize()
    await bot_app.start()
    
    # Set webhook
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_URL', 'localhost').replace('https://', '')}/webhook"
    await bot_app.bot.set_webhook(url=webhook_url)
    logger.info(f"Webhook set to {webhook_url}")

# Simple test handler
async def echo(update: Update, context):
    await update.message.reply_text(f"You said: {update.message.text}")

def start_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    global bot_app
    bot_app = Application.builder().token(BOT_TOKEN).updater(None).build()
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    loop.run_until_complete(bot_app.initialize())
    loop.run_until_complete(bot_app.start())
    
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_URL', 'localhost').replace('https://', '')}/webhook"
    loop.run_until_complete(bot_app.bot.set_webhook(url=webhook_url))
    logger.info(f"Webhook set to {webhook_url}")
    
    loop.run_forever()

import threading
threading.Thread(target=start_bot, daemon=True).start()

@app.route('/webhook', methods=['POST'])
def webhook():
    """Simple webhook handler"""
    logger.info("Webhook received")
    if not bot_app:
        return "Bot not ready", 503
    
    try:
        data = request.get_json()
        logger.info(f"Update received: {data.get('update_id')}")
        update = Update.de_json(data, bot_app.bot)
        
        # Process synchronously
        asyncio.run(bot_app.process_update(update))
        
        return "OK", 200
    except Exception as e:
        logger.exception(f"Error: {e}")
        return "Error", 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/', methods=['GET'])
def index():
    return "Bot is running"
