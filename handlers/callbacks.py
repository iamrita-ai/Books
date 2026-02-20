from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ContextTypes
from database import get_file_by_id, search_files
from config import OWNER_ID, FORCE_SUB_CHANNEL, RESULTS_PER_PAGE
import logging

logger = logging.getLogger(__name__)

async def button_callback(update: Update, context):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("get_"):
        file_id_num = int(data[4:])
        file_record = get_file_by_id(file_id_num)
        if file_record:
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=file_record['file_id'],
                reply_to_message_id=query.message.message_id
            )
        else:
            await query.edit_message_text("❌ File not found.")

    elif data.startswith("page_"):
        page = int(data[5:])
        context.user_data['current_page'] = page
        await send_results_page(query, context, page)

    elif data == "info":
        text = (
            "📚 *PDF Library Bot*\n"
            f"Owner: [Click here](tg://user?id={OWNER_ID})\n"
            f"Channel: {FORCE_SUB_CHANNEL}\n"
            "Send any part of a book name to search."
        )
        await query.edit_message_text(text, parse_mode='Markdown')

async def send_results_page(query, context, page):
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
    await query.edit_message_text(
        f"📚 Found {total} results (page {page+1}/{ (total+RESULTS_PER_PAGE-1)//RESULTS_PER_PAGE }):",
        reply_markup=reply_markup
    )

# Handler
callback_handler = CallbackQueryHandler(button_callback)
