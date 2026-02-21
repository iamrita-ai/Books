import logging
import threading
import os
import sys
from flask import Flask, jsonify

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

# Now import telegram safely (Python 3.11 has imghdr)
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import init_db, search_files, get_file_by_id, update_user, is_bot_locked, log_to_channel
from config import OWNER_ID, FORCE_SUB_CHANNEL, RESULTS_PER_PAGE
from utils import random_reaction, format_size, check_subscription

# Initialize database
init_db()

# ==================== Handlers ====================

def start(update, context):
    user = update.effective_user
    update_user(user.id, user.first_name, user.username)
    
    if update.effective_chat.type == "private":
        text = (
            "👋 Hello! I'm a PDF library bot.\n\n"
            "📚 I work **only in groups**. Add me to a group and send any part of a book name to search.\n\n"
            "🔍 **Available books**: Self-improvement, Mindset, Hindi literature, and more.\n"
            "⚠️ **No copyrighted or illegal content** – only public domain or author-approved books."
        )
    else:
        text = (
            "👋 Hello! I'm a PDF library bot.\n"
            "Send any part of a book name to search.\n\n"
            "⚠️ **No copyrighted or illegal content** – only self-improvement and public domain books."
        )
    update.message.reply_text(text)

def help_command(update, context):
    update.message.reply_text(
        "📚 *How to use:*\n"
        "• In a group, type any part of a book title to search.\n"
        "• Click on a result button to get the PDF instantly.\n"
        "• Use #request <book name> to suggest new books.\n"
        "• Commands: /start, /help\n\n"
        "❌ No pirated or copyrighted material.",
        parse_mode='Markdown'
    )

def group_message_handler(update, context):
    # React with random emoji
    try:
        update.message.react([random_reaction()])
    except:
        pass

    user = update.effective_user
    if not user:
        return
    update_user(user.id, user.first_name, user.username)

    # Lock check
    if is_bot_locked() and user.id != OWNER_ID:
        return

    # Force subscribe check
    if not check_subscription(user.id, context.bot):
        keyboard = [[InlineKeyboardButton("🔔 Join Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL[1:]}")]]
        update.message.reply_text(
            "⚠️ You must join our channel to search for books.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if update.message.text:
        query = update.message.text.strip()
        if not query:
            return

        if query.lower().startswith("#request"):
            update.message.reply_text("📝 Your request has been noted.")
            logger.info(f"Request from {user.first_name}: {query}")
            return

        results = search_files(query)
        if not results:
            update.message.reply_text("❌ No books found.")
            return

        context.user_data['search_results'] = results
        context.user_data['current_page'] = 0
        send_results_page(update, context, 0)

def send_results_page(update, context, page):
    results = context.user_data.get('search_results', [])
    total = len(results)
    start = page * RESULTS_PER_PAGE
    end = min(start + RESULTS_PER_PAGE, total)
    page_results = results[start:end]

    keyboard = []
    for res in page_results:
        btn_text = f"{res['original_filename']} ({format_size(res['file_size'])})"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"get_{res['id']}")])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Prev", callback_data=f"page_{page-1}"))
    if end < total:
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"page_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    info_row = [
        InlineKeyboardButton("👤 Owner", url=f"tg://user?id={OWNER_ID}"),
        InlineKeyboardButton("📢 Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL[1:]}"),
        InlineKeyboardButton("ℹ️ Info", callback_data="info")
    ]
    keyboard.append(info_row)

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        f"📚 Found {total} results (page {page+1}/{(total+RESULTS_PER_PAGE-1)//RESULTS_PER_PAGE}):",
        reply_markup=reply_markup
    )

def button_callback(update, context):
    query = update.callback_query
    query.answer()

    data = query.data
    if data.startswith("get_"):
        file_id_num = int(data[4:])
        file_record = get_file_by_id(file_id_num)
        if file_record:
            context.bot.send_document(
                chat_id=query.message.chat_id,
                document=file_record['file_id'],
                reply_to_message_id=query.message.message_id
            )
        else:
            query.edit_message_text("❌ File not found.")

    elif data.startswith("page_"):
        page = int(data[5:])
        context.user_data['current_page'] = page
        # Re-send the page (we need to edit the original message)
        results = context.user_data.get('search_results', [])
        total = len(results)
        start = page * RESULTS_PER_PAGE
        end = min(start + RESULTS_PER_PAGE, total)
        page_results = results[start:end]

        keyboard = []
        for res in page_results:
            btn_text = f"{res['original_filename']} ({format_size(res['file_size'])})"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"get_{res['id']}")])

        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("◀️ Prev", callback_data=f"page_{page-1}"))
        if end < total:
            nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"page_{page+1}"))
        if nav_buttons:
            keyboard.append(nav_buttons)

        info_row = [
            InlineKeyboardButton("👤 Owner", url=f"tg://user?id={OWNER_ID}"),
            InlineKeyboardButton("📢 Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL[1:]}"),
            InlineKeyboardButton("ℹ️ Info", callback_data="info")
        ]
        keyboard.append(info_row)

        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            f"📚 Found {total} results (page {page+1}/{(total+RESULTS_PER_PAGE-1)//RESULTS_PER_PAGE}):",
            reply_markup=reply_markup
        )

    elif data == "info":
        text = (
            "📚 *PDF Library Bot*\n"
            f"Owner: [Click here](tg://user?id={OWNER_ID})\n"
            f"Channel: {FORCE_SUB_CHANNEL}\n"
            "Send any part of a book name to search.\n\n"
            "⚠️ **No copyrighted or illegal content** – only public domain books."
        )
        query.edit_message_text(text, parse_mode='Markdown')

def error_handler(update, context):
    logger.error(f"Update {update} caused error {context.error}")

# ==================== Bot Thread ====================

def start_bot():
    logger.info("🚀 Starting bot with Updater...")
    try:
        updater = Updater(BOT_TOKEN, use_context=True)
        dp = updater.dispatcher

        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("help", help_command))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, group_message_handler))
        dp.add_handler(CallbackQueryHandler(button_callback))
        dp.add_error_handler(error_handler)

        logger.info("Starting polling...")
        updater.start_polling()
        logger.info("✅ Bot is running and polling!")
        updater.idle()
    except Exception as e:
        logger.exception(f"❌ Fatal error in bot thread: {e}")

bot_thread = threading.Thread(target=start_bot, daemon=True)
bot_thread.start()
logger.info("Bot thread started")

# ==================== Flask endpoints ====================

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "bot_thread_alive": bot_thread.is_alive()
    }), 200

@app.route('/', methods=['GET'])
def index():
    return "📚 Telegram PDF Library Bot is running."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
