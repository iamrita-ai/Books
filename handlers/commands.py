from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import CommandHandler, Filters, CallbackContext
from config import OWNER_ID, BOT_NAME, FORCE_SUB_CHANNEL, REQUEST_GROUP
from database import (get_total_files, get_total_users, get_db_size, is_bot_locked,
                      set_bot_locked, get_all_users, update_user, search_files)
from utils import get_uptime, get_memory_usage, get_disk_usage, check_subscription, log_to_channel, build_start_keyboard, build_info_keyboard, format_size
import datetime
import logging

logger = logging.getLogger(__name__)

BOT_START_TIME = datetime.datetime.now()

def _check_and_send_force_sub(update: Update, context) -> bool:
    user = update.effective_user
    if not user:
        return False
    if not check_subscription(user.id, context.bot):
        keyboard = [[InlineKeyboardButton("🔔 Join Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL[1:]}")]]
        update.message.reply_text(
            "⚠️ You must join our channel to use this bot.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return False
    return True

def owner_only(func):
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != OWNER_ID:
            update.message.reply_text("⛔ You are not authorized to use this command.")
            return
        return func(update, context, *args, **kwargs)
    return wrapper

def start(update: Update, context):
    user = update.effective_user
    update_user(user.id, user.first_name, user.username)

    if update.effective_chat.type == "private":
        text = (
            f"👋 <b>Hello {user.first_name}!</b>\n\n"
            f"I'm <b>{BOT_NAME}</b>, your personal PDF library assistant.\n\n"
            "📚 <b>How to use me:</b>\n"
            "• Add me to a <b>group</b> where you want to search for books.\n"
            "• In the group, you can:\n"
            "   - Type any part of a book name (e.g., `mindset`)\n"
            "   - Use <code>#book mindset</code> to search\n"
            "   - Use <code>#request book name</code> to request a book\n"
            "   - Use <code>/book mindset</code> command (if preferred)\n"
            "• Click on a result button to instantly get the PDF.\n\n"
            "📖 <b>Book categories:</b> Self-improvement, Mindset, Hindi literature, English classics, and more.\n\n"
            "❌ <b>No copyrighted or illegal content</b> – only public domain or author-approved books.\n\n"
            "📝 <b>Request a new book:</b>\n"
            "Use /new_request command followed by the book name (e.g., <code>/new_request The Art of War</code>).\n"
            "Your request will be forwarded to the bot owner.\n\n"
        )
        keyboard_rows = build_start_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard_rows)
    else:
        text = (
            f"👋 <b>Hello {user.first_name}!</b>\n\n"
            f"I'm <b>{BOT_NAME}</b>, here to help you find PDF books.\n\n"
            "🔍 <b>To search:</b>\n"
            "• Type any part of a book name (e.g., `mindset`)\n"
            "• Use <code>#book mindset</code>\n"
            "• Use <code>/book mindset</code> command\n\n"
            "📝 <b>To request a book:</b>\n"
            "Use <code>#request book name</code>\n\n"
            "❌ <b>No copyrighted content</b> – only public domain books."
        )
        reply_markup = None

    update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

def help_command(update: Update, context):
    text = (
        "📚 <b>Help & Commands</b>\n\n"
        "<b>Group commands:</b>\n"
        "• <code>/start</code> – Welcome message\n"
        "• <code>/help</code> – This help\n"
        "• <code>/stats</code> – Bot statistics\n"
        "• <code>/book &lt;name&gt;</code> – Search for a book\n"
        "• <code>#book &lt;name&gt;</code> – Alternative search tag\n"
        "• <code>#request &lt;name&gt;</code> – Request a book\n\n"
        "<b>Private chat commands:</b>\n"
        "• <code>/new_request &lt;name&gt;</code> – Request a book (owner notified)\n\n"
        "<b>Admin commands (owner only):</b>\n"
        "• <code>/users</code> – Show total users\n"
        "• <code>/broadcast &lt;msg&gt;</code> – Send message to all users\n"
        "• <code>/lock</code> – Lock the bot\n"
        "• <code>/unlock</code> – Unlock the bot\n"
        "• <code>/import</code> – Import database (placeholder)\n"
        "• <code>/export</code> – Export database\n"
        "• <code>/delete_db</code> – Delete all data\n\n"
        "📖 <b>Available books:</b> Self-improvement, Hindi literature, English classics, etc.\n"
        "❌ <b>No pirated content.</b>"
    )
    update.message.reply_text(text, parse_mode=ParseMode.HTML)

def stats(update: Update, context):
    if not _check_and_send_force_sub(update, context):
        return
    total_files = get_total_files()
    total_users = get_total_users()
    db_size = get_db_size() / 1024
    uptime = get_uptime(BOT_START_TIME)
    mem = get_memory_usage()
    disk = get_disk_usage()
    locked = "🔒 Locked" if is_bot_locked() else "🔓 Unlocked"

    text = (
        f"📊 <b>Bot Statistics</b>\n\n"
        f"⏱️ <b>Uptime:</b> {uptime}\n"
        f"📚 <b>Total PDFs:</b> {total_files}\n"
        f"👥 <b>Total Users:</b> {total_users}\n"
        f"💾 <b>Database size:</b> {db_size:.2f} KB\n"
        f"🔐 <b>Status:</b> {locked}\n"
    )
    if mem:
        text += f"🧠 <b>Memory:</b> {mem:.2f} MB\n"
    if disk:
        text += f"📀 <b>Disk used:</b> {disk:.2f} MB\n"

    update.message.reply_text(text, parse_mode=ParseMode.HTML)

def book_search(update: Update, context):
    if not context.args:
        update.message.reply_text("Please provide a book name. Example: /book mindset")
        return
    query = ' '.join(context.args)
    results = search_files(query)
    if not results:
        update.message.reply_text("❌ No books found.")
        return
    context.user_data['search_results'] = results
    context.user_data['current_page'] = 0
    send_results_page(update, context, 0)

def send_results_page(update: Update, context: CallbackContext, page):
    # This function is also used by message handler; we define it here or import? Better to define in a shared location.
    # To avoid duplication, we'll keep it in commands and also use it from messages if needed.
    # But since it's used in both places, we can define it in a separate module or just duplicate.
    # We'll duplicate for simplicity.
    from utils import build_info_keyboard, format_size
    results = context.user_data.get('search_results', [])
    total = len(results)
    start = page * RESULTS_PER_PAGE
    end = min(start + RESULTS_PER_PAGE, total)
    page_results = results[start:end]

    keyboard = []
    for res in page_results:
        btn_text = f"📘 {res['original_filename']} ({format_size(res['file_size'])})"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"get_{res['id']}")])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Prev", callback_data=f"page_{page-1}"))
    if end < total:
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"page_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    info_buttons = build_info_keyboard()
    if info_buttons:
        keyboard.append(info_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        f"📚 Found <b>{total}</b> results (page {page+1}/{(total+RESULTS_PER_PAGE-1)//RESULTS_PER_PAGE}):",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

@owner_only
def users(update: Update, context):
    count = get_total_users()
    update.message.reply_text(f"👥 <b>Total users:</b> {count}", parse_mode=ParseMode.HTML)

@owner_only
def broadcast(update: Update, context):
    if not context.args:
        update.message.reply_text("Usage: <code>/broadcast &lt;message&gt;</code>", parse_mode=ParseMode.HTML)
        return
    message = ' '.join(context.args)
    users = get_all_users()
    success = 0
    for uid in users:
        try:
            context.bot.send_message(uid, message)
            success += 1
        except Exception:
            pass
    update.message.reply_text(f"📢 Broadcast sent to {success}/{len(users)} users.")
    log_to_channel(context.bot, f"Broadcast sent by owner: {message[:50]}...")

@owner_only
def lock(update: Update, context):
    set_bot_locked(True)
    update.message.reply_text("🔒 Bot is now locked. Only owner can use commands.")
    log_to_channel(context.bot, "Bot locked by owner.")

@owner_only
def unlock(update: Update, context):
    set_bot_locked(False)
    update.message.reply_text("🔓 Bot is now unlocked for everyone.")
    log_to_channel(context.bot, "Bot unlocked by owner.")

@owner_only
def import_db(update: Update, context):
    update.message.reply_text("Import not implemented in this version.")

@owner_only
def export_db(update: Update, context):
    update.message.reply_document(document=open('bot_data.db', 'rb'))

@owner_only
def delete_db(update: Update, context):
    update.message.reply_text("⚠️ <b>This will delete all data.</b>\nType <code>/confirm_delete</code> to proceed.", parse_mode=ParseMode.HTML)
    context.user_data['confirm_delete'] = True

@owner_only
def confirm_delete(update: Update, context):
    if context.user_data.get('confirm_delete'):
        from database import get_db, init_db
        with get_db() as conn:
            conn.execute("DROP TABLE IF EXISTS files")
            conn.execute("DROP TABLE IF EXISTS users")
            conn.execute("DROP TABLE IF EXISTS settings")
        init_db()
        update.message.reply_text("✅ Database cleared.")
        log_to_channel(context.bot, "Database deleted by owner.")
    else:
        update.message.reply_text("No pending delete request.")

def new_request(update: Update, context):
    if update.effective_chat.type != "private":
        update.message.reply_text("Please use this command in private chat with me.")
        return

    if not context.args:
        update.message.reply_text(
            "📝 Please provide a book name.\n"
            "Example: <code>/new_request The Art of War</code>",
            parse_mode=ParseMode.HTML
        )
        return

    book_name = ' '.join(context.args)
    user = update.effective_user
    if OWNER_ID:
        try:
            text = (
                f"📌 <b>New Book Request</b>\n\n"
                f"<b>Book:</b> <code>{book_name}</code>\n"
                f"<b>User:</b> {user.first_name} (@{user.username})\n"
                f"<b>User ID:</b> <code>{user.id}</code>\n"
                f"<b>Link:</b> <a href=\"tg://user?id={user.id}\">Click here</a>"
            )
            context.bot.send_message(chat_id=OWNER_ID, text=text, parse_mode=ParseMode.HTML)
            update.message.reply_text(
                "✅ Your request has been sent to the bot owner. We'll try to add it soon!"
            )
        except Exception as e:
            logger.error(f"Failed to send request to owner: {e}")
            update.message.reply_text("❌ Sorry, could not send your request. Please try later.")
    else:
        update.message.reply_text("Owner not configured.")

def get_handlers():
    return [
        CommandHandler("start", start),
        CommandHandler("help", help_command),
        CommandHandler("stats", stats, Filters.chat_type.groups),
        CommandHandler("users", users, Filters.chat_type.groups),
        CommandHandler("broadcast", broadcast, Filters.chat_type.groups),
        CommandHandler("lock", lock, Filters.chat_type.groups),
        CommandHandler("unlock", unlock, Filters.chat_type.groups),
        CommandHandler("import", import_db, Filters.chat_type.groups),
        CommandHandler("export", export_db, Filters.chat_type.groups),
        CommandHandler("delete_db", delete_db, Filters.chat_type.groups),
        CommandHandler("confirm_delete", confirm_delete, Filters.chat_type.groups),
        CommandHandler("new_request", new_request, Filters.chat_type.private),
        CommandHandler("book", book_search, Filters.chat_type.groups),
    ]
