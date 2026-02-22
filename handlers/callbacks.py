from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackQueryHandler, CallbackContext
from database import get_file_by_id
from config import OWNER_ID, FORCE_SUB_CHANNEL, RESULTS_PER_PAGE, REQUEST_GROUP
from utils import format_size, build_info_keyboard

def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    data = query.data
    if data.startswith("get_"):
        file_id_num = int(data[4:])
        file_record = get_file_by_id(file_id_num)
        if file_record:
            context.bot.send_document(
                chat_id=query.message.chat_id,
                document=file_record['file_id'],
                reply_to_message_id=query.message.message_id
            )
        else:
            query.edit_message_text("❌ File not found.")

    elif data.startswith("page_"):
        page = int(data[5:])
        context.user_data['current_page'] = page
        results = context.user_data.get('search_results', [])
        if not results:
            query.edit_message_text("❌ No results found.")
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
        query.edit_message_text(
            f"📚 Found <b>{total}</b> results (page {page+1}/{(total+RESULTS_PER_PAGE-1)//RESULTS_PER_PAGE}):",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

    elif data == "info":
        text = (
            "📚 <b>PDF Library Bot</b>\n\n"
            f"👤 <b>Owner:</b> @Xioqui_xin\n"
            f"📢 <b>Channel:</b> {FORCE_SUB_CHANNEL if FORCE_SUB_CHANNEL else 'Not set'}\n"
        )
        if REQUEST_GROUP:
            text += f"📝 <b>Request Group:</b> {REQUEST_GROUP}\n"
        text += "\n🔍 <b>How to search:</b>\n"
        text += "• Type <code>#book name</code> or <code>/book name</code> in any group.\n"
        text += "• Click on a result to get the PDF.\n\n"
        text += "📝 <b>Request a book:</b>\n"
        text += "Use <code>#request name</code> in group, or <code>/new_request name</code> in private.\n\n"
        text += "⚠️ <b>No copyrighted or illegal content</b> – only self-improvement and public domain books."
        query.edit_message_text(text, parse_mode=ParseMode.HTML)

callback_handler = CallbackQueryHandler(button_callback)
