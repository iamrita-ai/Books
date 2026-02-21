from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import MessageHandler, Filters, CallbackContext
from database import update_user, is_bot_locked
from utils import check_subscription, log_to_channel, send_reaction
from config import FORCE_SUB_CHANNEL, OWNER_ID
import logging
import queue
import threading
import time
import random

logger = logging.getLogger(__name__)

# Reaction queue with delay
reaction_queue = queue.Queue()
reaction_running = True

def reaction_worker():
    """Process reactions with delay to avoid flooding."""
    while reaction_running:
        try:
            item = reaction_queue.get(timeout=1)
            if item is None:
                continue
            chat_id, message_id, msg_type = item
            emoji_pools = {
                "text": ["❤️", "🔥", "👍", "👏", "🎉", "🤔", "😮", "🤝", "💯", "⚡"],
                "photo": ["❤️", "🔥", "👍", "👏", "😍", "🤩", "✨", "🌟", "🎯", "🏆"],
                "video": ["🔥", "🎬", "👍", "👏", "😎", "💯", "⚡", "🚀", "🎉", "🏅"],
                "sticker": ["😄", "😂", "🤣", "😍", "😎", "🤩", "🎭", "✨", "👍", "👌"],
                "document": ["📄", "📚", "📖", "🔖", "📌", "✅", "👍", "❤️", "🔥", "🎉"]
            }
            emojis = emoji_pools.get(msg_type, emoji_pools["text"])
            num_reactions = random.randint(1, 3)
            for i in range(num_reactions):
                emoji = random.choice(emojis)
                is_big = random.choice([True, False])
                send_reaction(chat_id, message_id, emoji, is_big)
                time.sleep(random.uniform(0.5, 1.5))
            reaction_queue.task_done()
            time.sleep(random.uniform(1, 3))
        except queue.Empty:
            time.sleep(0.1)
        except Exception as e:
            logger.error(f"Reaction worker error: {e}")

reaction_thread = threading.Thread(target=reaction_worker, daemon=True)
reaction_thread.start()

def group_message_handler(update: Update, context: CallbackContext):
    """Handle all messages in groups: react, but do NOT search automatically."""
    if update.message:
        chat_id = update.effective_chat.id
        message_id = update.message.message_id
        msg_type = "text"
        if update.message.photo:
            msg_type = "photo"
        elif update.message.video:
            msg_type = "video"
        elif update.message.sticker:
            msg_type = "sticker"
        elif update.message.document:
            msg_type = "document"
        reaction_queue.put((chat_id, message_id, msg_type))

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
            "⚠️ You must join our channel to use this bot.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Handle #request (but only if it's text)
    if update.message.text:
        query = update.message.text.strip()
        if query.lower().startswith("#request"):
            book_name = query[8:].strip()
            if book_name:
                update.message.reply_text(
                    "📝 Your request has been noted. We'll try to add it if it's non-copyright."
                )
                log_to_channel(context.bot, f"📌 Group request from {user.first_name}: {book_name}")
                if OWNER_ID:
                    try:
                        text = (
                            f"📌 <b>Group Book Request</b>\n\n"
                            f"<b>Book:</b> <code>{book_name}</code>\n"
                            f"<b>User:</b> {user.first_name} (@{user.username})\n"
                            f"<b>User ID:</b> <code>{user.id}</code>\n"
                            f"<b>Group:</b> {update.effective_chat.title}"
                        )
                        context.bot.send_message(chat_id=OWNER_ID, text=text, parse_mode=ParseMode.HTML)
                    except:
                        pass
            else:
                update.message.reply_text("Please specify a book name after #request.")
            return

        # No automatic search for other text messages
        # So we do nothing else

group_message_handler_obj = MessageHandler(
    Filters.chat_type.groups & Filters.all,
    group_message_handler
)
