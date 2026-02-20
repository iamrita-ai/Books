import asyncio
import logging
import threading
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

# Initialize Flask
app = Flask(__name__)

# Bot token from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("BOT_TOKEN not set!")
    exit(1)

# Global bot application
bot_app = None

# Simple message handler for testing
async def echo_handler(update: Update, context):
    """Echo the user's message back"""
    if update.message and update.message.text:
        await update.message.reply_text(f"You said: {update.message.text}")
        logger.info(f"Echoed message: {update.message.text}")

def start_bot():
    """Initialize and start the bot in a background thread"""
    global bot_app
    
    # Create new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Build application
        bot_app = Application.builder().token(BOT_TOKEN).updater(None).build()
        
        # Add handler
        bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_handler))
        
        # Initialize
        loop.run_until_complete(bot_app.initialize())
        loop.run_until_complete(bot_app.start())
        
        # Set webhook
        webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_URL', 'localhost').replace('https://', '')}/webhook"
        loop.run_until_complete(bot_app.bot.set_webhook(url=webhook_url))
        logger.info(f"✅ Webhook set to {webhook_url}")
        
        # Keep the loop running
        loop.run_forever()
    except Exception as e:
        logger.exception(f"❌ Fatal error in bot thread: {e}")

# Start bot in background thread
bot_thread = threading.Thread(target=start_bot, daemon=True)
bot_thread.start()

# Define webhook handler function
def handle_webhook():
    """Process incoming webhook POST requests"""
    global bot_app
    
    logger.info("📨 Webhook received")
    
    # Check if bot is ready
    if not bot_app:
        logger.error("Bot not initialized")
        return "Bot not ready", 503
    
    try:
        # Get JSON data
        data = request.get_json(force=True)
        logger.info(f"Update ID: {data.get('update_id')}")
        
        # Create update object
        update = Update.de_json(data, bot_app.bot)
        
        # Process update in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot_app.process_update(update))
        loop.close()
        
        return "OK", 200
    except Exception as e:
        logger.exception(f"❌ Error processing webhook: {e}")
        return "Error", 500

# Explicitly add URL rule with POST method
app.add_url_rule('/webhook', 'webhook', handle_webhook, methods=['POST'])

# Also add a GET handler for testing
@app.route('/webhook', methods=['GET'])
def webhook_get():
    return "✅ Webhook endpoint is active. Send POST requests only.", 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "bot_ready": bot_app is not None
    }), 200

@app.route('/', methods=['GET'])
def index():
    return "🚀 Telegram Bot is running!"

if __name__ == '__main__':
    # For local testing only
    app.run(host='0.0.0.0', port=8080)
