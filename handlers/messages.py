from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import MessageHandler, Filters, CallbackContext
from database import search_files, update_user, is_bot_locked
from utils import random_reaction, format_size, check_subscription, log_to_channel, build_info_keyboard
from config import RESULTS_PER_PAGE, FORCE_SUB_CHANNEL, OWNER_ID
import logging

logger = logging.getLogger(__name__)

def group_message_handler(update: Update, context: CallbackContext):
    # Reactions not supported in this version – silently skip
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

        # Handle #request
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
                            f"📌 **Group Book Request**\n\n"
                            f"**Book:** `{book_name}`\n"
                            f"**User:** {user.first_name} (@{user.username})\n"
                            f"**User ID:** `{user.id}`\n"
                            f"**Group:** {update.effective_chat.title}"
                        )
                        context.bot.send_message(chat_id=OWNER_ID, text=text, parse_mode=ParseMode.MARKDOWN)
                    except:
                        pass
            else:
                update.message.reply_text("Please specify a book name after #request.")
            return

        results = search_files(query)
        if not results:
            update.message.reply_text("❌ No books found matching your query.")
            log_to_channel(context.bot, f"Search '{query}' by {user.first_name} – no results")
            return

        context.user_data['search_results'] = results
        context.user_data['current_page'] = 0
        send_results_page(update, context, 0)

def send_results_page(update: Update, context: CallbackContext, page):
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
        f"📚 Found **{total}** results (page {page+1}/{(total+RESULTS_PER_PAGE-1)//RESULTS_PER_PAGE}):",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

group_message_handler_obj = MessageHandler(
    Filters.group & Filters.text,
    group_message_handler
)
