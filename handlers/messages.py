from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReactionTypeEmoji
from telegram.ext import filters, MessageHandler, ContextTypes
from database import search_files, update_user, is_bot_locked
from utils import random_reaction, format_size, check_subscription, log_to_channel
from config import RESULTS_PER_PAGE, FORCE_SUB_CHANNEL, OWNER_ID
import logging
import asyncio

logger = logging.getLogger(__name__)

async def group_message_handler(update: Update, context):
    """Handle all messages in groups: react, then search if text."""
    # React with random emoji (try, but ignore failures)
    try:
        emoji = random_reaction()
        await update.message.react([ReactionTypeEmoji(emoji=emoji)])
    except Exception as e:
        logger.debug(f"Reaction failed: {e}")

    user = update.effective_user
    if not user:
        return

    # Update user in DB
    update_user(user.id, user.first_name, user.username)

    # Lock check: allow only owner if locked
    if is_bot_locked() and user.id != OWNER_ID:
        return

    # Force subscribe check
    if not await check_subscription(user.id, context.bot):
        keyboard = [[InlineKeyboardButton("🔔 Join Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL[1:]}")]]
        await update.message.reply_text(
            "⚠️ You must join our channel to search for books.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # If it's a text message, perform search
    if update.message.text:
        query = update.message.text.strip()
        if not query:
            return

        # Optional: handle #request specially
        if query.lower().startswith("#request"):
            # Could log or notify owner, but for now just inform user
            await update.message.reply_text(
                "📝 Your request has been noted. We'll try to add it if it's non-copyright."
            )
            await log_to_channel(context.bot, f"📌 Book request from {user.first_name}: {query[8:].strip()}")
            return

        results = search_files(query)
        if not results:
            await update.message.reply_text("❌ No books found matching your query.")
            await log_to_channel(context.bot, f"Search '{query}' by {user.first_name} – no results")
            return

        total = len(results)
        context.user_data['search_results'] = results
        context.user_data['current_page'] = 0

        await send_results_page(update, context, page=0)

async def send_results_page(update, context, page):
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
    await update.message.reply_text(
        f"📚 Found {total} results (page {page+1}/{ (total+RESULTS_PER_PAGE-1)//RESULTS_PER_PAGE }):",
        reply_markup=reply_markup
    )

# Handler for all messages in groups
group_message_handler_obj = MessageHandler(
    filters.ChatType.GROUPS & filters.ALL,
    group_message_handler
)
