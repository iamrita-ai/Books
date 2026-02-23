from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, ChatAction
from telegram.ext import MessageHandler, Filters, CallbackContext
from database import search_files, update_user, is_bot_locked, is_user_banned
from utils import format_size, check_subscription, log_to_channel, build_info_keyboard, send_reaction, safe_reply_text
from config import RESULTS_PER_PAGE, FORCE_SUB_CHANNEL, OWNER_ID
import logging
import queue
import threading
import time
import random
import re

logger = logging.getLogger(__name__)

reaction_queue = queue.Queue()
reaction_running = True

def reaction_worker():
    while reaction_running:
        try:
            chat_id, message_id, msg_type = reaction_queue.get(timeout=1)
            # Use only valid Telegram reaction emojis
            emoji_pools = {
                "text": ["👍", "❤️", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱", "🎉", "🤩", "🙏", "👌", "🕊️", "🤝", "😍", "😘", "💯", "💪", "🍓"],
                "photo": ["❤️", "🔥", "👍", "👏", "😍", "🤩", "✨", "🌟", "🎯", "🏆"],
                "video": ["🔥", "🎬", "👍", "👏", "😎", "💯", "⚡", "🚀", "🎉", "🏅"],
                "sticker": ["😄", "😂", "🤣", "😍", "😎", "🤩", "🎭", "✨", "👍", "👌"],
                "document": ["📄", "📚", "📖", "🔖", "📌", "✅", "👍", "❤️", "🔥", "🎉"]
            }
            emojis = emoji_pools.get(msg_type, emoji_pools["text"])
            num_reactions = random.randint(1, 2)  # Reduce to avoid flood
            for i in range(num_reactions):
                emoji = random.choice(emojis)
                is_big = (i == 0) and random.choice([True, False])  # Only first maybe big
                send_reaction(chat_id, message_id, emoji, is_big)
                time.sleep(random.uniform(0.5, 1.0))  # Slightly longer delay
            reaction_queue.task_done()
        except queue.Empty:
            time.sleep(0.1)
        except Exception as e:
            logger.error(f"Reaction worker error: {e}")

reaction_thread = threading.Thread(target=reaction_worker, daemon=True)
reaction_thread.start()

def delete_message(context: CallbackContext):
    job = context.job
    chat_id, message_id = job.context
    try:
        context.bot.delete_message(chat_id, message_id)
    except Exception as e:
        logger.error(f"Auto-delete failed: {e}")

def is_admin(update: Update, context, user_id):
    """Check if user is admin in the group."""
    try:
        member = context.bot.get_chat_member(update.effective_chat.id, user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

def group_message_handler(update: Update, context: CallbackContext):
    # Show typing animation
    context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

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

    # Check if user is banned
    if is_user_banned(user.id):
        return

    update_user(user.id, user.first_name, user.username)

    # Link spam prevention
    if update.message.text and not is_admin(update, context, user.id) and user.id != OWNER_ID:
        # Check for links
        text = update.message.text
        link_pattern = r'(https?://|t\.me/|www\.)[^\s]+'
        if re.search(link_pattern, text, re.IGNORECASE):
            try:
                update.message.delete()
                logger.info(f"Deleted spam message from {user.id} containing link")
                # Optionally warn user
                # warn_user(user.id, context.bot.id, "Sending links")
            except Exception as e:
                logger.error(f"Failed to delete spam message: {e}")
            return

    if is_bot_locked() and user.id != OWNER_ID:
        return

    if FORCE_SUB_CHANNEL and not check_subscription(user.id, context.bot):
        keyboard = [[InlineKeyboardButton("🔔 Join Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL[1:]}")]]
        update.message.reply_text(
            "⚠️ You must join our channel to search for books.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Schedule auto-delete after 24 hours
    context.job_queue.run_once(delete_message, 86400, context=(chat_id, message_id))

    if update.message.text:
        text = update.message.text.strip()

        if not (text.startswith('/book') or text.startswith('#book') or text.startswith('#request')):
            return

        if text.lower().startswith('#request'):
            book_name = text[8:].strip()
            if book_name:
                safe_reply_text(update.message, "📝 Your request has been noted. We'll try to add it if it's non-copyright.")
                log_to_channel(context.bot, f"📌 Group request from {user.first_name}: {book_name}")
                if OWNER_ID:
                    try:
                        msg = (
                            f"📌 <b>Group Book Request</b>\n\n"
                            f"<b>Book:</b> <code>{book_name}</code>\n"
                            f"<b>User:</b> {user.first_name} (@{user.username})\n"
                            f"<b>User ID:</b> <code>{user.id}</code>\n"
                            f"<b>Group:</b> {update.effective_chat.title}"
                        )
                        context.bot.send_message(chat_id=OWNER_ID, text=msg, parse_mode=ParseMode.HTML)
                    except:
                        pass
            else:
                update.message.reply_text("Please specify a book name after #request.")
            return

        if text.lower().startswith('#book'):
            query = text[5:].strip()
        elif text.lower().startswith('/book'):
            query = text[5:].strip()
        else:
            return

        if not query:
            update.message.reply_text("Please provide a book name after #book or /book.")
            return

        results = search_files(query)
        if not results:
            safe_reply_text(update.message, "❌ No books found matching your query.")
            log_to_channel(context.bot, f"Search '{query}' by {user.first_name} – no results")
            return

        context.user_data['search_results'] = results
        context.user_data['current_page'] = 0
        try:
            send_results_page(update, context, 0)
        except Exception as e:
            logger.error(f"Error in send_results_page: {e}", exc_info=True)
            update.message.reply_text("❌ An error occurred while displaying results.")

def send_results_page(update: Update, context: CallbackContext, page):
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
        # info_buttons is a list of rows, so extend keyboard with those rows
        keyboard.extend(info_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        f"📚 Found <b>{total}</b> results (page {page+1}/{(total+RESULTS_PER_PAGE-1)//RESULTS_PER_PAGE}):",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

group_message_handler_obj = MessageHandler(
    Filters.chat_type.groups & Filters.all,
    group_message_handler
)
