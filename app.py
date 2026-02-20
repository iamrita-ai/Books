import asyncio
import logging
import threading
import time
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, MessageHandler, filters
import os

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Bot token from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("BOT_TOKEN not set!")
    exit(1)

# Global variables
bot_app = None
bot_ready = threading.Event()  # Signal when bot is fully initialized

# Simple message handler
async def echo_handler(update: Update, context):
    """Echo the user's message back"""
    if update.message and update.message.text:
        await update.message.reply_text(f"You said: {update.message.text}")
        logger.info(f"Echoed: {update.message.text}")

def start_bot():
    """Initialize bot in background thread"""
    global bot_app
    
    logger.info("🚀 Starting bot initialization...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Build application
        bot_app = Application.builder().token(BOT_TOKEN).updater(None).build()
        bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_handler))
        
        # Initialize
        loop.run_until_complete(bot_app.initialize())
        loop.run_until_complete(bot_app.start())
        
        # Set webhook
        webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_URL', 'localhost').replace('https://', '')}/webhook"
        loop.run_until_complete(bot_app.bot.set_webhook(url=webhook_url))
        logger.info(f"✅ Webhook set to {webhook_url}")
        
        # Signal that bot is ready
        bot_ready.set()
        logger.info("✅ Bot is fully initialized and ready!")
        
        # Keep loop running
        loop.run_forever()
    except Exception as e:
        logger.exception(f"❌ Fatal error in bot thread: {e}")

# Start bot in background
threading.Thread(target=start_bot, daemon=True).start()

def handle_webhook():
    """Process incoming webhook POST requests"""
    logger.info("📨 Webhook POST received")
    
    # Wait for bot to be ready (max 30 seconds)
    if not bot_ready.wait(timeout=30):
        logger.error("⏰ Timeout waiting for bot to initialize")
        return "Bot initialization timeout", 503
    
    if not bot_app:
        logger.error("❌ Bot app is None despite ready event")
        return "Bot not ready", 503
    
    try:
        data = request.get_json(force=True)
        logger.info(f"📦 Update ID: {data.get('update_id')}")
        
        update = Update.de_json(data, bot_app.bot)
        
        # Process in new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot_app.process_update(update))
        loop.close()
        
        logger.info("✅ Update processed successfully")
        return "OK", 200
    except Exception as e:
        logger.exception(f"❌ Error processing webhook: {e}")
        return "Error", 500

# Register webhook endpoint
app.add_url_rule('/webhook', 'webhook', handle_webhook, methods=['POST'])

# GET handler for testing
@app.route('/webhook', methods=['GET'])
def webhook_get():
    return "✅ Webhook endpoint is active. Send POST requests only.", 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "bot_ready": bot_ready.is_set(),
        "pending_updates": 0
    }), 200

@app.route('/', methods=['GET'])
def index():
    ready_status = "✅ Bot is ready!" if bot_ready.is_set() else "⏳ Bot is initializing..."
    return f"🚀 Telegram Bot is running!<br>{ready_status}"
