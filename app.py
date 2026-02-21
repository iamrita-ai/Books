import logging
import threading
import os
import sys
import time
from flask import Flask, jsonify

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("BOT_TOKEN not set!")
    sys.exit(1)

# Import database and utils (these don't cause import errors)
from database import init_db, add_file, search_files, get_file_by_id, update_user, is_bot_locked, set_bot_locked, get_total_files, get_total_users, get_db_size, get_all_users
from utils import random_reaction, format_size, check_subscription, log_to_channel, get_uptime, get_memory_usage, get_disk_usage
from config import OWNER_ID, FORCE_SUB_CHANNEL, RESULTS_PER_PAGE, SOURCE_CHANNEL, LOG_CHANNEL, MAX_FILE_SIZE, BOT_NAME
import datetime

# Initialize database
init_db()
BOT_START_TIME = datetime.datetime.now()

# Global flag to control bot thread
bot_running = True
bot_thread = None

def run_bot():
    """Run the bot in a background thread without idle()."""
    from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
    
    def start(update, context):
        user = update.effective_user
        update_user(user.id, user.first_name, user.username)
        
        if update.effective_chat.type == "private":
            text = (
                f"👋 Hello! I'm {BOT_NAME}, a PDF library bot.\n\n"
                "📚 I work **only in groups**. Add me to a group and send any part of a book name to search.\n\n"
                "🔍 **Available books**: Self-improvement, Mindset, Hindi literature, and more.\n"
                "⚠️ **No copyrighted or illegal content** – only public domain or author-approved books.\n\n"
                "Need a new book? Request in the group with #request followed by the name."
            )
        else:
            text = (
                f"👋 Hello! I'm {BOT_NAME}, a PDF library bot.\n"
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
            "• Commands:\n"
            "/start - Welcome message\n"
            "/help - This help\n"
            "/stats - Bot statistics\n\n"
            "❌ No pirated or copyrighted material.",
            parse_mode=ParseMode.MARKDOWN
        )

    def stats(update, context):
        total_files = get_total_files()
        total_users = get_total_users()
        db_size = get_db_size() / 1024
        uptime = get_uptime(BOT_START_TIME)
        mem = get_memory_usage()
        disk = get_disk_usage()
        locked = "🔒 Locked" if is_bot_locked() else "🔓 Unlocked"

        text = (
            f"📊 *Bot Statistics*\n"
            f"• Uptime: {uptime}\n"
            f"• Total PDFs: {total_files}\n"
            f"• Total Users: {total_users}\n"
            f"• Database size: {db_size:.2f} KB\n"
            f"• Status: {locked}\n"
        )
        if mem:
            text += f"• Memory: {mem:.2f} MB\n"
        if disk:
            text += f"• Disk used: {disk:.2f} MB\n"

        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

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
        if FORCE_SUB_CHANNEL and not check_subscription(user.id, context.bot):
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
                update.message.reply_text("📝 Your request has been noted. We'll try to add it if it's non-copyright.")
                log_to_channel(context.bot, f"📌 Book request from {user.first_name}: {query[8:].strip()}")
                return

            results = search_files(query)
            if not results:
                update.message.reply_text("❌ No books found matching your query.")
                log_to_channel(context.bot, f"Search '{query}' by {user.first_name} – no results")
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
            InlineKeyboardButton("📢 Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL[1:]}" if FORCE_SUB_CHANNEL else None),
            InlineKeyboardButton("ℹ️ Info", callback_data="info")
        ]
        info_row = [btn for btn in info_row if btn]  # Remove None
        if info_row:
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
                InlineKeyboardButton("📢 Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL[1:]}" if FORCE_SUB_CHANNEL else None),
                InlineKeyboardButton("ℹ️ Info", callback_data="info")
            ]
            info_row = [btn for btn in info_row if btn]
            if info_row:
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
                "⚠️ **No copyrighted or illegal content** – only self-improvement and public domain books."
            )
            query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

    def error_handler(update, context):
        logger.error(f"Update {update} caused error {context.error}")

    logger.info("🚀 Starting bot thread...")
    try:
        updater = Updater(BOT_TOKEN, use_context=True)
        dp = updater.dispatcher
        
        # Add handlers
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("help", help_command))
        dp.add_handler(CommandHandler("stats", stats))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, group_message_handler))
        dp.add_handler(CallbackQueryHandler(button_callback))
        dp.add_error_handler(error_handler)

        # Start polling
        updater.start_polling()
        logger.info("✅ Bot is polling!")

        # Keep the thread alive without using idle()
        while bot_running:
            time.sleep(10)
            logger.debug("Bot thread heartbeat")

    except Exception as e:
        logger.exception(f"❌ Bot thread error: {e}")

def start_bot_thread():
    global bot_thread
    bot_thread = threading.Thread(target=run_bot, daemon=True, name="BotThread")
    bot_thread.start()
    logger.info(f"Bot thread started: {bot_thread.ident}")

# Start the bot thread
start_bot_thread()

# ==================== Flask Web Server ====================
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "bot_thread_alive": bot_thread.is_alive() if bot_thread else False
    }), 200

@app.route('/', methods=['GET'])
def index():
    return "📚 Telegram PDF Library Bot is running."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
