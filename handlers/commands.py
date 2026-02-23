from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, ChatAction
from telegram.ext import CommandHandler, Filters, CallbackContext, MessageHandler
from config import OWNER_ID, BOT_NAME, FORCE_SUB_CHANNEL, REQUEST_GROUP, RESULTS_PER_PAGE
from database import (
    get_total_files, get_total_users, get_db_size, is_bot_locked,
    set_bot_locked, get_all_users, update_user, search_files,
    get_top_books, get_random_book, add_feedback, warn_user, is_user_banned
)
from utils import (
    get_uptime, get_memory_usage, get_disk_usage, check_subscription,
    log_to_channel, build_start_keyboard, build_info_keyboard, format_size,
    safe_reply_text
)
import datetime
import logging
import time

logger = logging.getLogger(__name__)

BOT_START_TIME = datetime.datetime.now()

# ==================== Helper Functions ====================

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

def send_results_page(update: Update, context: CallbackContext, page):
    """Shared function to display search results with pagination."""
    from utils import build_info_keyboard, format_size
    results = context.user_data.get('search_results', [])
    if not results:
        update.message.reply_text("❌ No results found.")
        return

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

# ==================== Public Commands ====================

def start(update: Update, context):
    user = update.effective_user
    update_user(user.id, user.first_name, user.username)

    # Show typing animation
    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    if update.effective_chat.type == "private":
        text = (
            f"👋 <b>𝐇𝐞𝐥𝐥𝐨 {user.first_name}!</b>\n\n"
            f"𝐈'𝐦 <b>{BOT_NAME}</b>, 𝐲𝐨𝐮𝐫 𝐩𝐞𝐫𝐬𝐨𝐧𝐚𝐥 𝐏𝐃𝐅 𝐥𝐢𝐛𝐫𝐚𝐫𝐲 𝐚𝐬𝐬𝐢𝐬𝐭𝐚𝐧𝐭.\n\n"
            "📚 <b>𝐇𝐨𝐰 𝐭𝐨 𝐮𝐬𝐞 𝐦𝐞:</b>\n"
            "• 𝐀𝐝𝐝 𝐦𝐞 𝐭𝐨 𝐚 <b>𝐠𝐫𝐨𝐮𝐩</b> 𝐰𝐡𝐞𝐫𝐞 𝐲𝐨𝐮 𝐰𝐚𝐧𝐭 𝐭𝐨 𝐬𝐞𝐚𝐫𝐜𝐡 𝐟𝐨𝐫 𝐛𝐨𝐨𝐤𝐬.\n"
            "• 𝐈𝐧 𝐭𝐡𝐞 𝐠𝐫𝐨𝐮𝐩, 𝐲𝐨𝐮 𝐜𝐚𝐧:\n"
            "   ➤ 𝐔𝐬𝐞 <code>#book mindset</code> 𝐭𝐨 𝐬𝐞𝐚𝐫𝐜𝐡\n"
            "   ➤ 𝐔𝐬𝐞 <code>/book mindset</code> 𝐜𝐨𝐦𝐦𝐚𝐧𝐝\n"
            "   ➤ 𝐔𝐬𝐞 <code>/random</code> 𝐟𝐨𝐫 𝐚 𝐫𝐚𝐧𝐝𝐨𝐦 𝐛𝐨𝐨𝐤\n"
            "   ➤ 𝐔𝐬𝐞 <code>/top</code> 𝐟𝐨𝐫 𝐦𝐨𝐬𝐭 𝐝𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐞𝐝 𝐛𝐨𝐨𝐤𝐬\n"
            "   ➤ 𝐔𝐬𝐞 <code>#request book name</code> 𝐭𝐨 𝐫𝐞𝐪𝐮𝐞𝐬𝐭 𝐚 𝐛𝐨𝐨𝐤\n"
            "• 𝐂𝐥𝐢𝐜𝐤 𝐨𝐧 𝐚 𝐫𝐞𝐬𝐮𝐥𝐭 𝐛𝐮𝐭𝐭𝐨𝐧 𝐭𝐨 𝐢𝐧𝐬𝐭𝐚𝐧𝐭𝐥𝐲 𝐠𝐞𝐭 𝐭𝐡𝐞 𝐏𝐃𝐅.\n\n"
            "📖 <b>𝐁𝐨𝐨𝐤 𝐜𝐚𝐭𝐞𝐠𝐨𝐫𝐢𝐞𝐬:</b> 𝐒𝐞𝐥𝐟-𝐢𝐦𝐩𝐫𝐨𝐯𝐞𝐦𝐞𝐧𝐭, 𝐌𝐢𝐧𝐝𝐬𝐞𝐭, 𝐇𝐢𝐧𝐝𝐢 𝐥𝐢𝐭𝐞𝐫𝐚𝐭𝐮𝐫𝐞, 𝐄𝐧𝐠𝐥𝐢𝐬𝐡 𝐜𝐥𝐚𝐬𝐬𝐢𝐜𝐬, 𝐚𝐧𝐝 𝐦𝐨𝐫𝐞.\n\n"
            "❌ <b>𝐍𝐨 𝐜𝐨𝐩𝐲𝐫𝐢𝐠𝐡𝐭𝐞𝐝 𝐨𝐫 𝐢𝐥𝐥𝐞𝐠𝐚𝐥 𝐜𝐨𝐧𝐭𝐞𝐧𝐭</b> – 𝐨𝐧𝐥𝐲 𝐩𝐮𝐛𝐥𝐢𝐜 𝐝𝐨𝐦𝐚𝐢𝐧 𝐨𝐫 𝐚𝐮𝐭𝐡𝐨𝐫-𝐚𝐩𝐩𝐫𝐨𝐯𝐞𝐝 𝐛𝐨𝐨𝐤𝐬.\n\n"
            "📝 <b>𝐑𝐞𝐪𝐮𝐞𝐬𝐭 𝐚 𝐧𝐞𝐰 𝐛𝐨𝐨𝐤:</b>\n"
            "𝐔𝐬𝐞 /new_request 𝐜𝐨𝐦𝐦𝐚𝐧𝐝 𝐟𝐨𝐥𝐥𝐨𝐰𝐞𝐝 𝐛𝐲 𝐭𝐡𝐞 𝐛𝐨𝐨𝐤 𝐧𝐚𝐦𝐞 (𝐞.𝐠., <code>/new_request The Art of War</code>).\n"
            "𝐘𝐨𝐮𝐫 𝐫𝐞𝐪𝐮𝐞𝐬𝐭 𝐰𝐢𝐥𝐥 𝐛𝐞 𝐟𝐨𝐫𝐰𝐚𝐫𝐝𝐞𝐝 𝐭𝐨 𝐭𝐡𝐞 𝐛𝐨𝐭 𝐨𝐰𝐧𝐞𝐫.\n\n"
        )
        keyboard_rows = build_start_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard_rows)
    else:
        text = (
            f"👋 <b>𝐇𝐞𝐥𝐥𝐨 {user.first_name}!</b>\n\n"
            f"𝐈'𝐦 <b>{BOT_NAME}</b>, 𝐡𝐞𝐫𝐞 𝐭𝐨 𝐡𝐞𝐥𝐩 𝐲𝐨𝐮 𝐟𝐢𝐧𝐝 𝐏𝐃𝐅 𝐛𝐨𝐨𝐤𝐬.\n\n"
            "🔍 <b>𝐂𝐨𝐦𝐦𝐚𝐧𝐝𝐬:</b>\n"
            "• <code>/book mindset</code> – 𝐒𝐞𝐚𝐫𝐜𝐡 𝐚 𝐛𝐨𝐨𝐤\n"
            "• <code>/random</code> – 𝐑𝐚𝐧𝐝𝐨𝐦 𝐛𝐨𝐨𝐤 𝐬𝐮𝐠𝐠𝐞𝐬𝐭𝐢𝐨𝐧\n"
            "• <code>/top</code> – 𝐓𝐨𝐩 𝐝𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐞𝐝 𝐛𝐨𝐨𝐤𝐬\n"
            "• <code>/feedback &lt;book_id&gt; &lt;rating&gt; [comment]</code> – 𝐑𝐚𝐭𝐞 𝐚 𝐛𝐨𝐨𝐤\n"
            "• <code>#request book name</code> – 𝐑𝐞𝐪𝐮𝐞𝐬𝐭 𝐚 𝐛𝐨𝐨𝐤\n\n"
            "❌ <b>𝐍𝐨 𝐜𝐨𝐩𝐲𝐫𝐢𝐠𝐡𝐭𝐞𝐝 𝐜𝐨𝐧𝐭𝐞𝐧𝐭</b> – 𝐨𝐧𝐥𝐲 𝐩𝐮𝐛𝐥𝐢𝐜 𝐝𝐨𝐦𝐚𝐢𝐧 𝐛𝐨𝐨𝐤𝐬."
        )
        reply_markup = None

    update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

def help_command(update: Update, context):
    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    text = (
        "📚 <b>𝐇𝐞𝐥𝐩 & 𝐂𝐨𝐦𝐦𝐚𝐧𝐝𝐬</b>\n\n"
        "<b>𝐆𝐫𝐨𝐮𝐩 𝐜𝐨𝐦𝐦𝐚𝐧𝐝𝐬:</b>\n"
        "• <code>/start</code> – 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐦𝐞𝐬𝐬𝐚𝐠𝐞\n"
        "• <code>/help</code> – 𝐓𝐡𝐢𝐬 𝐡𝐞𝐥𝐩\n"
        "• <code>/stats</code> – 𝐁𝐨𝐭 𝐬𝐭𝐚𝐭𝐢𝐬𝐭𝐢𝐜𝐬\n"
        "• <code>/book &lt;𝐧𝐚𝐦𝐞&gt;</code> – 𝐒𝐞𝐚𝐫𝐜𝐡 𝐟𝐨𝐫 𝐚 𝐛𝐨𝐨𝐤\n"
        "• <code>/random</code> – 𝐑𝐚𝐧𝐝𝐨𝐦 𝐛𝐨𝐨𝐤 𝐬𝐮𝐠𝐠𝐞𝐬𝐭𝐢𝐨𝐧\n"
        "• <code>/top</code> – 𝐓𝐨𝐩 𝐝𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐞𝐝 𝐛𝐨𝐨𝐤𝐬\n"
        "• <code>/feedback &lt;𝐢𝐝&gt; &lt;𝐫𝐚𝐭𝐢𝐧𝐠&gt; [𝐜𝐨𝐦𝐦𝐞𝐧𝐭]</code> – 𝐑𝐚𝐭𝐞 𝐚 𝐛𝐨𝐨𝐤 (1-5)\n"
        "• <code>#book &lt;𝐧𝐚𝐦𝐞&gt;</code> – 𝐀𝐥𝐭𝐞𝐫𝐧𝐚𝐭𝐢𝐯𝐞 𝐬𝐞𝐚𝐫𝐜𝐡 𝐭𝐚𝐠\n"
        "• <code>#request &lt;𝐧𝐚𝐦𝐞&gt;</code> – 𝐑𝐞𝐪𝐮𝐞𝐬𝐭 𝐚 𝐛𝐨𝐨𝐤\n\n"
        "<b>𝐏𝐫𝐢𝐯𝐚𝐭𝐞 𝐜𝐡𝐚𝐭 𝐜𝐨𝐦𝐦𝐚𝐧𝐝𝐬:</b>\n"
        "• <code>/new_request &lt;𝐧𝐚𝐦𝐞&gt;</code> – 𝐑𝐞𝐪𝐮𝐞𝐬𝐭 𝐚 𝐛𝐨𝐨𝐤 (𝐨𝐰𝐧𝐞𝐫 𝐧𝐨𝐭𝐢𝐟𝐢𝐞𝐝)\n\n"
        "<b>𝐀𝐝𝐦𝐢𝐧 𝐜𝐨𝐦𝐦𝐚𝐧𝐝𝐬 (𝐨𝐰𝐧𝐞𝐫 𝐨𝐧𝐥𝐲):</b>\n"
        "• <code>/users</code> – 𝐒𝐡𝐨𝐰 𝐭𝐨𝐭𝐚𝐥 𝐮𝐬𝐞𝐫𝐬\n"
        "• <code>/broadcast &lt;𝐦𝐬𝐠&gt;</code> – 𝐒𝐞𝐧𝐝 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐭𝐨 𝐚𝐥𝐥 𝐮𝐬𝐞𝐫𝐬\n"
        "• <code>/lock</code> – 𝐋𝐨𝐜𝐤 𝐭𝐡𝐞 𝐛𝐨𝐭\n"
        "• <code>/unlock</code> – 𝐔𝐧𝐥𝐨𝐜𝐤 𝐭𝐡𝐞 𝐛𝐨𝐭\n"
        "• <code>/import</code> – 𝐈𝐦𝐩𝐨𝐫𝐭 𝐝𝐚𝐭𝐚𝐛𝐚𝐬𝐞 (𝐫𝐞𝐩𝐥𝐲 𝐭𝐨 .𝐝𝐛 𝐟𝐢𝐥𝐞)\n"
        "• <code>/export</code> – 𝐄𝐱𝐩𝐨𝐫𝐭 𝐝𝐚𝐭𝐚𝐛𝐚𝐬𝐞\n"
        "• <code>/delete_db</code> – 𝐃𝐞𝐥𝐞𝐭𝐞 𝐚𝐥𝐥 𝐝𝐚𝐭𝐚 (𝐫𝐞𝐪𝐮𝐢𝐫𝐞𝐬 𝐜𝐨𝐧𝐟𝐢𝐫𝐦𝐚𝐭𝐢𝐨𝐧)\n"
        "• <code>/warn &lt;𝐮𝐬𝐞𝐫_𝐢𝐝&gt; &lt;𝐫𝐞𝐚𝐬𝐨𝐧&gt;</code> – 𝐖𝐚𝐫𝐧 𝐚 𝐮𝐬𝐞𝐫\n\n"
        "📖 <b>𝐀𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞 𝐛𝐨𝐨𝐤𝐬:</b> 𝐒𝐞𝐥𝐟-𝐢𝐦𝐩𝐫𝐨𝐯𝐞𝐦𝐞𝐧𝐭, 𝐇𝐢𝐧𝐝𝐢 𝐥𝐢𝐭𝐞𝐫𝐚𝐭𝐮𝐫𝐞, 𝐄𝐧𝐠𝐥𝐢𝐬𝐡 𝐜𝐥𝐚𝐬𝐬𝐢𝐜𝐬, 𝐞𝐭𝐜.\n"
        "❌ <b>𝐍𝐨 𝐩𝐢𝐫𝐚𝐭𝐞𝐝 𝐜𝐨𝐧𝐭𝐞𝐧𝐭.</b>"
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
        f"📊 <b>𝐁𝐨𝐭 𝐒𝐭𝐚𝐭𝐢𝐬𝐭𝐢𝐜𝐬</b>\n\n"
        f"⏱️ <b>𝐔𝐩𝐭𝐢𝐦𝐞:</b> {uptime}\n"
        f"📚 <b>𝐓𝐨𝐭𝐚𝐥 𝐏𝐃𝐅𝐬:</b> {total_files}\n"
        f"👥 <b>𝐓𝐨𝐭𝐚𝐥 𝐔𝐬𝐞𝐫𝐬:</b> {total_users}\n"
        f"💾 <b>𝐃𝐚𝐭𝐚𝐛𝐚𝐬𝐞 𝐬𝐢𝐳𝐞:</b> {db_size:.2f} 𝐊𝐁\n"
        f"🔐 <b>𝐒𝐭𝐚𝐭𝐮𝐬:</b> {locked}\n"
    )
    if mem:
        text += f"🧠 <b>𝐌𝐞𝐦𝐨𝐫𝐲:</b> {mem:.2f} 𝐌𝐁\n"
    if disk:
        text += f"📀 <b>𝐃𝐢𝐬𝐤 𝐮𝐬𝐞𝐝:</b> {disk:.2f} 𝐌𝐁\n"

    update.message.reply_text(text, parse_mode=ParseMode.HTML)

def book_search(update: Update, context):
    if not context.args:
        update.message.reply_text("𝐏𝐥𝐞𝐚𝐬𝐞 𝐩𝐫𝐨𝐯𝐢𝐝𝐞 𝐚 𝐛𝐨𝐨𝐤 𝐧𝐚𝐦𝐞. 𝐄𝐱𝐚𝐦𝐩𝐥𝐞: /book mindset")
        return
    query = ' '.join(context.args)
    results = search_files(query)
    if not results:
        update.message.reply_text("❌ 𝐍𝐨 𝐛𝐨𝐨𝐤𝐬 𝐟𝐨𝐮𝐧𝐝.")
        return
    context.user_data['search_results'] = results
    context.user_data['current_page'] = 0
    send_results_page(update, context, 0)

def random_book(update: Update, context):
    book = get_random_book()
    if not book:
        update.message.reply_text("❌ 𝐍𝐨 𝐛𝐨𝐨𝐤𝐬 𝐢𝐧 𝐝𝐚𝐭𝐚𝐛𝐚𝐬𝐞.")
        return
    keyboard = [[InlineKeyboardButton(f"📘 {book['original_filename']} ({format_size(book['file_size'])})", callback_data=f"get_{book['id']}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("📖 <b>𝐑𝐚𝐧𝐝𝐨𝐦 𝐁𝐨𝐨𝐤 𝐒𝐮𝐠𝐠𝐞𝐬𝐭𝐢𝐨𝐧:</b>", reply_markup=reply_markup, parse_mode=ParseMode.HTML)

def top_books(update: Update, context):
    books = get_top_books(10)
    if not books:
        update.message.reply_text("❌ 𝐍𝐨 𝐝𝐨𝐰𝐧𝐥𝐨𝐚𝐝 𝐝𝐚𝐭𝐚 𝐲𝐞𝐭.")
        return
    text = "📊 <b>𝐓𝐨𝐩 𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐞𝐝 𝐁𝐨𝐨𝐤𝐬</b>\n\n"
    keyboard = []
    for i, book in enumerate(books, 1):
        text += f"{i}. {book['original_filename']} – {book['download_count']} 𝐝𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐬\n"
        btn_text = f"📘 {book['original_filename'][:30]}..."
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"get_{book['id']}")])
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

def feedback(update: Update, context):
    if len(context.args) < 2:
        update.message.reply_text("𝐔𝐬𝐚𝐠𝐞: /feedback <𝐛𝐨𝐨𝐤_𝐢𝐝> <𝐫𝐚𝐭𝐢𝐧𝐠 1-5> [𝐜𝐨𝐦𝐦𝐞𝐧𝐭]")
        return
    try:
        book_id = int(context.args[0])
        rating = int(context.args[1])
        if rating < 1 or rating > 5:
            raise ValueError
    except:
        update.message.reply_text("𝐈𝐧𝐯𝐚𝐥𝐢𝐝 𝐛𝐨𝐨𝐤 𝐈𝐃 𝐨𝐫 𝐫𝐚𝐭𝐢𝐧𝐠 (𝐦𝐮𝐬𝐭 𝐛𝐞 1-5).")
        return
    comment = ' '.join(context.args[2:]) if len(context.args) > 2 else None
    user_id = update.effective_user.id
    add_feedback(user_id, book_id, rating, comment)
    update.message.reply_text("✅ 𝐓𝐡𝐚𝐧𝐤 𝐲𝐨𝐮 𝐟𝐨𝐫 𝐲𝐨𝐮𝐫 𝐟𝐞𝐞𝐝𝐛𝐚𝐜𝐤!")

def new_request(update: Update, context):
    if update.effective_chat.type != "private":
        update.message.reply_text("𝐏𝐥𝐞𝐚𝐬𝐞 𝐮𝐬𝐞 𝐭𝐡𝐢𝐬 𝐜𝐨𝐦𝐦𝐚𝐧𝐝 𝐢𝐧 𝐩𝐫𝐢𝐯𝐚𝐭𝐞 𝐜𝐡𝐚𝐭 𝐰𝐢𝐭𝐡 𝐦𝐞.")
        return
    if not context.args:
        update.message.reply_text(
            "📝 𝐏𝐥𝐞𝐚𝐬𝐞 𝐩𝐫𝐨𝐯𝐢𝐝𝐞 𝐚 𝐛𝐨𝐨𝐤 𝐧𝐚𝐦𝐞.\n"
            "𝐄𝐱𝐚𝐦𝐩𝐥𝐞: <code>/new_request The Art of War</code>",
            parse_mode=ParseMode.HTML
        )
        return
    book_name = ' '.join(context.args)
    user = update.effective_user
    if OWNER_ID:
        try:
            text = (
                f"📌 <b>𝐍𝐞𝐰 𝐁𝐨𝐨𝐤 𝐑𝐞𝐪𝐮𝐞𝐬𝐭</b>\n\n"
                f"<b>𝐁𝐨𝐨𝐤:</b> <code>{book_name}</code>\n"
                f"<b>𝐔𝐬𝐞𝐫:</b> {user.first_name} (@{user.username})\n"
                f"<b>𝐔𝐬𝐞𝐫 𝐈𝐃:</b> <code>{user.id}</code>\n"
                f"<b>𝐋𝐢𝐧𝐤:</b> <a href=\"tg://user?id={user.id}\">𝐂𝐥𝐢𝐜𝐤 𝐡𝐞𝐫𝐞</a>"
            )
            context.bot.send_message(chat_id=OWNER_ID, text=text, parse_mode=ParseMode.HTML)
            update.message.reply_text(
                "✅ 𝐘𝐨𝐮𝐫 𝐫𝐞𝐪𝐮𝐞𝐬𝐭 𝐡𝐚𝐬 𝐛𝐞𝐞𝐧 𝐬𝐞𝐧𝐭 𝐭𝐨 𝐭𝐡𝐞 𝐛𝐨𝐭 𝐨𝐰𝐧𝐞𝐫. 𝐖𝐞'𝐥𝐥 𝐭𝐫𝐲 𝐭𝐨 𝐚𝐝𝐝 𝐢𝐭 𝐬𝐨𝐨𝐧!"
            )
        except Exception as e:
            logger.error(f"Failed to send request to owner: {e}")
            update.message.reply_text("❌ 𝐒𝐨𝐫𝐫𝐲, 𝐜𝐨𝐮𝐥𝐝 𝐧𝐨𝐭 𝐬𝐞𝐧𝐝 𝐲𝐨𝐮𝐫 𝐫𝐞𝐪𝐮𝐞𝐬𝐭. 𝐏𝐥𝐞𝐚𝐬𝐞 𝐭𝐫𝐲 𝐥𝐚𝐭𝐞𝐫.")
    else:
        update.message.reply_text("𝐎𝐰𝐧𝐞𝐫 𝐧𝐨𝐭 𝐜𝐨𝐧𝐟𝐢𝐠𝐮𝐫𝐞𝐝.")

# ==================== Admin Commands ====================

@owner_only
def users(update: Update, context):
    count = get_total_users()
    update.message.reply_text(f"👥 <b>𝐓𝐨𝐭𝐚𝐥 𝐮𝐬𝐞𝐫𝐬:</b> {count}", parse_mode=ParseMode.HTML)

@owner_only
def broadcast(update: Update, context):
    if not context.args:
        update.message.reply_text("𝐔𝐬𝐚𝐠𝐞: <code>/broadcast &lt;𝐦𝐞𝐬𝐬𝐚𝐠𝐞&gt;</code>", parse_mode=ParseMode.HTML)
        return
    message = ' '.join(context.args)
    users = get_all_users()
    success = 0
    for uid in users:
        try:
            context.bot.send_message(uid, message)
            success += 1
            time.sleep(0.05)
        except Exception as e:
            logger.error(f"Broadcast to {uid} failed: {e}")
    update.message.reply_text(f"📢 𝐁𝐫𝐨𝐚𝐝𝐜𝐚𝐬𝐭 𝐬𝐞𝐧𝐭 𝐭𝐨 {success}/{len(users)} 𝐮𝐬𝐞𝐫𝐬.")
    log_to_channel(context.bot, f"Broadcast sent by owner: {message[:50]}...")

@owner_only
def lock(update: Update, context):
    set_bot_locked(True)
    update.message.reply_text("🔒 𝐁𝐨𝐭 𝐢𝐬 𝐧𝐨𝐰 𝐥𝐨𝐜𝐤𝐞𝐝. 𝐎𝐧𝐥𝐲 𝐨𝐰𝐧𝐞𝐫 𝐜𝐚𝐧 𝐮𝐬𝐞 𝐜𝐨𝐦𝐦𝐚𝐧𝐝𝐬.")
    log_to_channel(context.bot, "Bot locked by owner.")

@owner_only
def unlock(update: Update, context):
    set_bot_locked(False)
    update.message.reply_text("🔓 𝐁𝐨𝐭 𝐢𝐬 𝐧𝐨𝐰 𝐮𝐧𝐥𝐨𝐜𝐤𝐞𝐝 𝐟𝐨𝐫 𝐞𝐯𝐞𝐫𝐲𝐨𝐧𝐞.")
    log_to_channel(context.bot, "Bot unlocked by owner.")

@owner_only
def import_db(update: Update, context):
    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        update.message.reply_text("𝐏𝐥𝐞𝐚𝐬𝐞 𝐫𝐞𝐩𝐥𝐲 𝐭𝐨 𝐚 𝐝𝐚𝐭𝐚𝐛𝐚𝐬𝐞 𝐟𝐢𝐥𝐞 𝐰𝐢𝐭𝐡 /import")
        return

    file = update.message.reply_to_message.document
    if not file.file_name.endswith('.db'):
        update.message.reply_text("❌ 𝐏𝐥𝐞𝐚𝐬𝐞 𝐬𝐞𝐧𝐝 𝐚 𝐯𝐚𝐥𝐢𝐝 .𝐝𝐛 𝐟𝐢𝐥𝐞")
        return

    file_id = file.file_id
    new_file = context.bot.get_file(file_id)
    new_file.download('imported.db')

    import os
    import shutil
    try:
        shutil.copy2('imported.db', 'bot_data.db')
        os.remove('imported.db')
        update.message.reply_text("✅ 𝐃𝐚𝐭𝐚𝐛𝐚𝐬𝐞 𝐢𝐦𝐩𝐨𝐫𝐭𝐞𝐝 𝐬𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲!")
        log_to_channel(context.bot, "Database imported by owner.")
    except Exception as e:
        update.message.reply_text(f"❌ 𝐈𝐦𝐩𝐨𝐫𝐭 𝐟𝐚𝐢𝐥𝐞𝐝: {e}")

@owner_only
def export_db(update: Update, context):
    try:
        with open('bot_data.db', 'rb') as f:
            update.message.reply_document(document=f, filename='bot_data.db')
    except Exception as e:
        update.message.reply_text(f"❌ 𝐄𝐱𝐩𝐨𝐫𝐭 𝐟𝐚𝐢𝐥𝐞𝐝: {e}")

@owner_only
def delete_db(update: Update, context):
    update.message.reply_text("⚠️ <b>𝐓𝐡𝐢𝐬 𝐰𝐢𝐥𝐥 𝐝𝐞𝐥𝐞𝐭𝐞 𝐚𝐥𝐥 𝐝𝐚𝐭𝐚.</b>\n𝐓𝐲𝐩𝐞 <code>/confirm_delete</code> 𝐭𝐨 𝐩𝐫𝐨𝐜𝐞𝐞𝐝.", parse_mode=ParseMode.HTML)
    context.user_data['confirm_delete'] = True

@owner_only
def confirm_delete(update: Update, context):
    if context.user_data.get('confirm_delete'):
        from database import get_db, init_db
        with get_db() as conn:
            conn.execute("DROP TABLE IF EXISTS files")
            conn.execute("DROP TABLE IF EXISTS users")
            conn.execute("DROP TABLE IF EXISTS settings")
            conn.execute("DROP TABLE IF EXISTS categories")
            conn.execute("DROP TABLE IF EXISTS book_categories")
            conn.execute("DROP TABLE IF EXISTS feedback")
            conn.execute("DROP TABLE IF EXISTS downloads")
            conn.execute("DROP TABLE IF EXISTS user_warnings")
            conn.execute("DROP TABLE IF EXISTS user_badges")
            conn.execute("DROP TABLE IF EXISTS reading_challenges")
        init_db()
        update.message.reply_text("✅ 𝐃𝐚𝐭𝐚𝐛𝐚𝐬𝐞 𝐜𝐥𝐞𝐚𝐫𝐞𝐝.")
        log_to_channel(context.bot, "Database deleted by owner.")
        context.user_data['confirm_delete'] = False
    else:
        update.message.reply_text("𝐍𝐨 𝐩𝐞𝐧𝐝𝐢𝐧𝐠 𝐝𝐞𝐥𝐞𝐭𝐞 𝐫𝐞𝐪𝐮𝐞𝐬𝐭.")

@owner_only
def warn_user(update: Update, context):
    if len(context.args) < 2:
        update.message.reply_text("𝐔𝐬𝐚𝐠𝐞: /warn <𝐮𝐬𝐞𝐫_𝐢𝐝> <𝐫𝐞𝐚𝐬𝐨𝐧>")
        return
    try:
        user_id = int(context.args[0])
        reason = ' '.join(context.args[1:])
    except:
        update.message.reply_text("𝐈𝐧𝐯𝐚𝐥𝐢𝐝 𝐮𝐬𝐞𝐫 𝐈𝐃.")
        return

    count = warn_user(user_id, update.effective_user.id, reason)
    update.message.reply_text(f"⚠️ 𝐔𝐬𝐞𝐫 {user_id} 𝐰𝐚𝐫𝐧𝐞𝐝. 𝐓𝐨𝐭𝐚𝐥 𝐰𝐚𝐫𝐧𝐢𝐧𝐠𝐬: {count}")

    if count >= 3:
        from database import ban_user
        ban_user(user_id)
        update.message.reply_text(f"🚫 𝐔𝐬𝐞𝐫 {user_id} 𝐡𝐚𝐬 𝐛𝐞𝐞𝐧 𝐛𝐚𝐧𝐧𝐞𝐝 𝐝𝐮𝐞 𝐭𝐨 𝐦𝐮𝐥𝐭𝐢𝐩𝐥𝐞 𝐰𝐚𝐫𝐧𝐢𝐧𝐠𝐬.")
        log_to_channel(context.bot, f"User {user_id} banned for 3 warnings.")

# ==================== Group Welcome Handler ====================

def new_chat_members(update: Update, context):
    """Send welcome message when bot is added to a group."""
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            update.message.reply_text(
                "👋 𝐓𝐡𝐚𝐧𝐤𝐬 𝐟𝐨𝐫 𝐚𝐝𝐝𝐢𝐧𝐠 𝐦𝐞! 𝐈'𝐦 𝐚 𝐏𝐃𝐅 𝐥𝐢𝐛𝐫𝐚𝐫𝐲 𝐛𝐨𝐭.\n\n"
                "📚 𝐔𝐬𝐞 <code>#book &lt;𝐧𝐚𝐦𝐞&gt;</code> 𝐨𝐫 <code>/book &lt;𝐧𝐚𝐦𝐞&gt;</code> 𝐭𝐨 𝐬𝐞𝐚𝐫𝐜𝐡 𝐟𝐨𝐫 𝐛𝐨𝐨𝐤𝐬.\n"
                "📝 𝐑𝐞𝐪𝐮𝐞𝐬𝐭 𝐛𝐨𝐨𝐤𝐬 𝐰𝐢𝐭𝐡 <code>#request &lt;𝐧𝐚𝐦𝐞&gt;</code>.\n\n"
                "𝐇𝐚𝐩𝐩𝐲 𝐫𝐞𝐚𝐝𝐢𝐧𝐠! 📖",
                parse_mode=ParseMode.HTML
            )
            break

# ==================== Handler Registration ====================

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
        CommandHandler("random", random_book, Filters.chat_type.groups),
        CommandHandler("top", top_books, Filters.chat_type.groups),
        CommandHandler("feedback", feedback, Filters.chat_type.groups),
        CommandHandler("warn", warn_user, Filters.chat_type.groups),
        MessageHandler(Filters.status_update.new_chat_members, new_chat_members),
    ]
