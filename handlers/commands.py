from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes, filters
from config import OWNER_ID, BOT_NAME, FORCE_SUB_CHANNEL
from database import (get_total_files, get_total_users, get_db_size, is_bot_locked,
                      set_bot_locked, get_all_users)
from utils import get_uptime, get_memory_usage, get_disk_usage, check_subscription, log_to_channel
import datetime
import logging

logger = logging.getLogger(__name__)

BOT_START_TIME = datetime.datetime.now()

async def _check_and_send_force_sub(update: Update, context) -> bool:
    """Check force subscription; works in both groups and private."""
    user = update.effective_user
    if not user:
        return False
    if not await check_subscription(user.id, context.bot):
        keyboard = [[InlineKeyboardButton("🔔 Join Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL[1:]}")]]
        await update.message.reply_text(
            "⚠️ You must join our channel to use this bot.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return False
    return True

def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != OWNER_ID:
            await update.message.reply_text("⛔ You are not authorized to use this command.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

async def start(update: Update, context):
    """Handle /start in any chat."""
    if not await _check_and_send_force_sub(update, context):
        return

    # Different message for groups vs private
    if update.effective_chat.type == "private":
        text = (
            f"👋 Hello! I'm {BOT_NAME}, a PDF library bot.\n\n"
            "📚 I work **only in groups**. Add me to a group and send any part of a book name to search my library.\n\n"
            "🔍 **Available books**: Self-improvement, Mindset, Hindi literature (e.g., 'The Art of Being Alone', 'Mindset', 'Godan'), and more.\n"
            "⚠️ **No copyrighted or illegal content** – only public domain or author-approved books.\n\n"
            "Need a new book? Request in the group with #request followed by the name."
        )
    else:
        text = (
            f"👋 Hello! I'm {BOT_NAME}, a PDF library bot.\n"
            "Send any part of a book name to search my library.\n\n"
            "⚠️ **No copyrighted or illegal content** – only self-improvement and public domain books."
        )
    await update.message.reply_text(text)

async def help_command(update: Update, context):
    """Handle /help in any chat."""
    if not await _check_and_send_force_sub(update, context):
        return
    text = (
        "📚 *How to use:*\n"
        "• In a group, type any part of a book title to search.\n"
        "• Click on a result button to get the PDF instantly.\n"
        "• Use #request <book name> to suggest new books.\n"
        "• Commands:\n"
        "/start - Welcome message\n"
        "/help - This help\n"
        "/stats - Bot statistics\n\n"
        "📖 *Library contents*: Self-improvement, mindset, Hindi classics (e.g., Godan, Premchand), and more.\n"
        "❌ No pirated or copyrighted material."
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def stats(update: Update, context):
    """Show bot statistics (works in any chat)."""
    if not await _check_and_send_force_sub(update, context):
        return
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

    await update.message.reply_text(text, parse_mode='Markdown')

# ... (other admin commands remain unchanged) ...

def get_handlers():
    """Return list of command handlers."""
    return [
        # Public commands – no chat filter (work in groups and private)
        CommandHandler("start", start),
        CommandHandler("help", help_command),
        CommandHandler("stats", stats),
        # Admin commands – still group-only for safety, but owner can use anywhere
        CommandHandler("users", users, filters=filters.ChatType.GROUPS),
        CommandHandler("broadcast", broadcast, filters=filters.ChatType.GROUPS),
        CommandHandler("lock", lock, filters=filters.ChatType.GROUPS),
        CommandHandler("unlock", unlock, filters=filters.ChatType.GROUPS),
        CommandHandler("import", import_db, filters=filters.ChatType.GROUPS),
        CommandHandler("export", export_db, filters=filters.ChatType.GROUPS),
        CommandHandler("delete_db", delete_db, filters=filters.ChatType.GROUPS),
        CommandHandler("confirm_delete", confirm_delete, filters=filters.ChatType.GROUPS),
    ]
