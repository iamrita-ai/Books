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
    if not await _check_and_send_force_sub(update, context):
        return

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

@owner_only
async def users(update: Update, context):
    count = get_total_users()
    await update.message.reply_text(f"👥 Total users: {count}")

@owner_only
async def broadcast(update: Update, context):
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    message = ' '.join(context.args)
    users = get_all_users()
    success = 0
    for uid in users:
        try:
            await context.bot.send_message(uid, message)
            success += 1
        except Exception:
            pass
    await update.message.reply_text(f"📢 Broadcast sent to {success}/{len(users)} users.")
    await log_to_channel(context.bot, f"Broadcast sent by owner: {message[:50]}...")

@owner_only
async def lock(update: Update, context):
    set_bot_locked(True)
    await update.message.reply_text("🔒 Bot is now locked. Only owner can use commands.")
    await log_to_channel(context.bot, "Bot locked by owner.")

@owner_only
async def unlock(update: Update, context):
    set_bot_locked(False)
    await update.message.reply_text("🔓 Bot is now unlocked for everyone.")
    await log_to_channel(context.bot, "Bot unlocked by owner.")

@owner_only
async def import_db(update: Update, context):
    await update.message.reply_text("Import not implemented in this version.")

@owner_only
async def export_db(update: Update, context):
    await update.message.reply_document(document=open('bot_data.db', 'rb'))

@owner_only
async def delete_db(update: Update, context):
    await update.message.reply_text("⚠️ This will delete all data. Type /confirm_delete to proceed.")
    context.user_data['confirm_delete'] = True

@owner_only
async def confirm_delete(update: Update, context):
    if context.user_data.get('confirm_delete'):
        from database import get_db, init_db
        with get_db() as conn:
            conn.execute("DROP TABLE IF EXISTS files")
            conn.execute("DROP TABLE IF EXISTS users")
            conn.execute("DROP TABLE IF EXISTS settings")
        init_db()
        await update.message.reply_text("✅ Database cleared.")
        await log_to_channel(context.bot, "Database deleted by owner.")
    else:
        await update.message.reply_text("No pending delete request.")

def get_handlers():
    return [
        CommandHandler("start", start),
        CommandHandler("help", help_command),
        CommandHandler("stats", stats),
        CommandHandler("users", users, filters=filters.ChatType.GROUPS),
        CommandHandler("broadcast", broadcast, filters=filters.ChatType.GROUPS),
        CommandHandler("lock", lock, filters=filters.ChatType.GROUPS),
        CommandHandler("unlock", unlock, filters=filters.ChatType.GROUPS),
        CommandHandler("import", import_db, filters=filters.ChatType.GROUPS),
        CommandHandler("export", export_db, filters=filters.ChatType.GROUPS),
        CommandHandler("delete_db", delete_db, filters=filters.ChatType.GROUPS),
        CommandHandler("confirm_delete", confirm_delete, filters=filters.ChatType.GROUPS),
    ]
