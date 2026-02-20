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
bot_thread = None

# Simple message handler (will be replaced by your full handlers later)
async def echo_handler(update: Update, context):
    """Echo the user's message back"""
    if update.message and update.message.text:
        await update.message.reply_text(f"You said: {update.message.text}")
        logger.info(f"Echoed: {update.message.text}")

def bot_heartbeat():
    """Periodic heartbeat to show bot thread is alive"""
    while True:
        time.sleep(60)
        logger.info("💓 Bot thread heartbeat - still alive")

def start_bot():
    """Initialize bot in background thread"""
    global bot_app
    thread_id = threading.current_thread().ident
    logger.info(f"🚀 Starting bot initialization in thread {thread_id}...")
    
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
        logger.info(f"✅ Bot is fully initialized and ready! (thread {thread_id})")
        
        # Start heartbeat in a separate daemon thread within the bot thread
        heartbeat_thread = threading.Thread(target=bot_heartbeat, daemon=True)
        heartbeat_thread.start()
        
        # Keep loop running forever
        loop.run_forever()
    except Exception as e:
        logger.exception(f"❌ Fatal error in bot thread: {e}")
    finally:
        logger.info("🛑 Bot thread is exiting.")
        # If loop was running, close it
        if loop.is_running():
            loop.stop()
        loop.close()

# Start bot in background
bot_thread = threading.Thread(target=start_bot, daemon=True)
bot_thread.start()

def handle_webhook():
    """Process incoming webhook POST requests"""
    logger.info("📨 Webhook POST received")
    
    # Log event state before waiting
    logger.debug(f"bot_ready.is_set() = {bot_ready.is_set()}")
    
    # Wait a short time for bot to be ready (1 second, fail fast)
    if not bot_ready.wait(timeout=1):
        logger.error("⏰ Bot not ready within 1 second")
        return "Bot not ready", 503
    
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
        "bot_thread_alive": bot_thread.is_alive() if bot_thread else False
    }), 200

@app.route('/', methods=['GET'])
def index():
    ready_status = "✅ Bot is ready!" if bot_ready.is_set() else "⏳ Bot is initializing..."
    thread_status = f"Bot thread alive: {bot_thread.is_alive() if bot_thread else False}"
    return f"🚀 Telegram Bot is running!<br>{ready_status}<br>{thread_status}"
