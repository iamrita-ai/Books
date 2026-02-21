from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import CommandHandler, ContextTypes, filters
from config import OWNER_ID, BOT_NAME, FORCE_SUB_CHANNEL, REQUEST_GROUP
from database import (get_total_files, get_total_users, get_db_size, is_bot_locked,
                      set_bot_locked, get_all_users, update_user)
from utils import get_uptime, get_memory_usage, get_disk_usage, check_subscription, log_to_channel, build_info_keyboard
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
    user = update.effective_user
    update_user(user.id, user.first_name, user.username)

    if update.effective_chat.type == "private":
        text = (
            f"👋 **Hello {user.first_name}!**\n\n"
            f"I'm **{BOT_NAME}**, your personal PDF library assistant.\n\n"
            "📚 **How to use me:**\n"
            "• Add me to a **group** where you want to search for books.\n"
            "• In the group, simply type any part of a book name, and I'll show you matching results.\n"
            "• Click on a result button to instantly get the PDF.\n\n"
            "📖 **Book categories:** Self-improvement, Mindset, Hindi literature, English classics, and more.\n\n"
            "❌ **No copyrighted or illegal content** – only public domain or author-approved books.\n\n"
            "📝 **Request a new book:**\n"
            "Use /new_request command followed by the book name (e.g., `/new_request The Art of War`).\n"
            "Your request will be forwarded to the bot owner.\n\n"
            f"📢 **Join our channel:** {FORCE_SUB_CHANNEL if FORCE_SUB_CHANNEL else 'Not set'}\n"
            "👤 **Owner:** @Xioqui_xin"
        )
    else:
        text = (
            f"👋 **Hello {user.first_name}!**\n\n"
            f"I'm **{BOT_NAME}**, here to help you find PDF books.\n\n"
            "🔍 **To search:** Just type any part of a book name.\n"
            "📌 Example: `mindset` or `godan`\n\n"
            "❌ **No copyrighted content** – only public domain books.\n\n"
            "📝 **Want a new book?** Use #request followed by the book name, e.g., `#request The Art of War`\n"
            "Your request will be noted."
        )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def help_command(update: Update, context):
    text = (
        "📚 **Help & Commands**\n\n"
        "**Group commands:**\n"
        "• `/start` – Welcome message\n"
        "• `/help` – This help\n"
        "• `/stats` – Bot statistics (group only)\n"
        "• `#request <book>` – Request a new book\n\n"
        "**Private chat commands:**\n"
        "• `/new_request <book>` – Request a book (owner will be notified)\n\n"
        "**Admin commands (owner only):**\n"
        "• `/users` – Show total users\n"
        "• `/broadcast <msg>` – Send message to all users\n"
        "• `/lock` – Lock the bot (only owner can use)\n"
        "• `/unlock` – Unlock the bot\n"
        "• `/import` – Import database (placeholder)\n"
        "• `/export` – Export database\n"
        "• `/delete_db` – Delete all data (requires confirmation)\n\n"
        "📖 **Available books:** Self-improvement, Hindi literature, English classics, etc.\n"
        "❌ **No pirated content.**"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

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
        f"📊 **Bot Statistics**\n\n"
        f"⏱️ **Uptime:** {uptime}\n"
        f"📚 **Total PDFs:** {total_files}\n"
        f"👥 **Total Users:** {total_users}\n"
        f"💾 **Database size:** {db_size:.2f} KB\n"
        f"🔐 **Status:** {locked}\n"
    )
    if mem:
        text += f"🧠 **Memory:** {mem:.2f} MB\n"
    if disk:
        text += f"📀 **Disk used:** {disk:.2f} MB\n"

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

@owner_only
async def users(update: Update, context):
    count = get_total_users()
    await update.message.reply_text(f"👥 **Total users:** {count}", parse_mode=ParseMode.MARKDOWN)

@owner_only
async def broadcast(update: Update, context):
    if not context.args:
        await update.message.reply_text("Usage: `/broadcast <message>`", parse_mode=ParseMode.MARKDOWN)
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
    await update.message.reply_text("⚠️ **This will delete all data.**\nType `/confirm_delete` to proceed.", parse_mode=ParseMode.MARKDOWN)
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

async def new_request(update: Update, context):
    """Handle /new_request command in private chat."""
    if update.effective_chat.type != "private":
        await update.message.reply_text("Please use this command in private chat with me.")
        return

    if not context.args:
        await update.message.reply_text(
            "📝 Please provide a book name.\n"
            "Example: `/new_request The Art of War`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    book_name = ' '.join(context.args)
    user = update.effective_user
    # Forward request to owner
    owner_id = OWNER_ID
    if owner_id:
        try:
            text = (
                f"📌 **New Book Request**\n\n"
                f"**Book:** `{book_name}`\n"
                f"**User:** {user.first_name} (@{user.username})\n"
                f"**User ID:** `{user.id}`\n"
                f"**Link:** [Click here](tg://user?id={user.id})"
            )
            await context.bot.send_message(chat_id=owner_id, text=text, parse_mode=ParseMode.MARKDOWN)
            await update.message.reply_text(
                "✅ Your request has been sent to the bot owner. We'll try to add it soon!"
            )
        except Exception as e:
            logger.error(f"Failed to send request to owner: {e}")
            await update.message.reply_text("❌ Sorry, could not send your request. Please try later.")
    else:
        await update.message.reply_text("Owner not configured.")

# Group request handler (via #request)
async def group_request(update: Update, context):
    """Handle #request in groups."""
    if update.effective_chat.type == "private":
        return
    if update.message and update.message.text:
        query = update.message.text.strip()
        if query.lower().startswith("#request"):
            book_name = query[8:].strip()
            if book_name:
                user = update.effective_user
                # Log to channel
                await log_to_channel(context.bot, f"📌 Group request from {user.first_name}: {book_name}")
                # Optionally forward to owner
                owner_id = OWNER_ID
                if owner_id:
                    try:
                        text = (
                            f"📌 **Group Book Request**\n\n"
                            f"**Book:** `{book_name}`\n"
                            f"**User:** {user.first_name} (@{user.username})\n"
                            f"**User ID:** `{user.id}`\n"
                            f"**Group:** {update.effective_chat.title}"
                        )
                        await context.bot.send_message(chat_id=owner_id, text=text, parse_mode=ParseMode.MARKDOWN)
                    except:
                        pass
                await update.message.reply_text("📝 Your request has been noted. We'll try to add it if it's non-copyright.")
            else:
                await update.message.reply_text("Please specify a book name after #request.")

def get_handlers():
    return [
        CommandHandler("start", start),
        CommandHandler("help", help_command),
        CommandHandler("stats", stats, filters=filters.ChatType.GROUPS),
        CommandHandler("users", users, filters=filters.ChatType.GROUPS),
        CommandHandler("broadcast", broadcast, filters=filters.ChatType.GROUPS),
        CommandHandler("lock", lock, filters=filters.ChatType.GROUPS),
        CommandHandler("unlock", unlock, filters=filters.ChatType.GROUPS),
        CommandHandler("import", import_db, filters=filters.ChatType.GROUPS),
        CommandHandler("export", export_db, filters=filters.ChatType.GROUPS),
        CommandHandler("delete_db", delete_db, filters=filters.ChatType.GROUPS),
        CommandHandler("confirm_delete", confirm_delete, filters=filters.ChatType.GROUPS),
        CommandHandler("new_request", new_request, filters=filters.ChatType.PRIVATE),
    ]
