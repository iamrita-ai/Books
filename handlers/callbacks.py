from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackQueryHandler, CallbackContext
from database import get_file_by_id, increment_download
from config import OWNER_ID, FORCE_SUB_CHANNEL, RESULTS_PER_PAGE, REQUEST_GROUP
from utils import format_size, build_info_keyboard
import logging

logger = logging.getLogger(__name__)

def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    data = query.data
    if data.startswith("get_"):
        file_id_num = int(data[4:])
        file_record = get_file_by_id(file_id_num)
        if file_record:
            # If preview exists, send it first
            if file_record.get('preview_file_id'):
                try:
                    context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=file_record['preview_file_id'],
                        caption=f"📖 <b>𝐏𝐫𝐞𝐯𝐢𝐞𝐰 𝐨𝐟:</b> {file_record.get('original_filename', '𝐁𝐨𝐨𝐤')}",
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    logger.error(f"Preview send failed: {e}")

            # Send the PDF
            context.bot.send_document(
                chat_id=query.message.chat_id,
                document=file_record['file_id'],
                caption=f"📘 <b>{file_record.get('original_filename', '𝐁𝐨𝐨𝐤')}</b>\n📦 𝐒𝐢𝐳𝐞: {format_size(file_record.get('file_size', 0))}",
                parse_mode=ParseMode.HTML,
                reply_to_message_id=query.message.message_id
            )

            # Track download
            try:
                user_id = update.effective_user.id
                increment_download(file_id_num, user_id)
            except Exception as e:
                logger.error(f"Failed to track download: {e}")

            # Delete the results message
            try:
                query.message.delete()
            except Exception as e:
                logger.error(f"Failed to delete message: {e}")
        else:
            query.edit_message_text("❌ 𝐅𝐢𝐥𝐞 𝐧𝐨𝐭 𝐟𝐨𝐮𝐧𝐝.")

    elif data.startswith("page_"):
        page = int(data[5:])
        context.user_data['current_page'] = page
        results = context.user_data.get('search_results', [])
        if not results:
            query.edit_message_text("❌ 𝐍𝐨 𝐫𝐞𝐬𝐮𝐥𝐭𝐬 𝐟𝐨𝐮𝐧𝐝.")
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
            nav_buttons.append(InlineKeyboardButton("◀️ 𝐏𝐫𝐞𝐯", callback_data=f"page_{page-1}"))
        if end < total:
            nav_buttons.append(InlineKeyboardButton("𝐍𝐞𝐱𝐭 ▶️", callback_data=f"page_{page+1}"))
        if nav_buttons:
            keyboard.append(nav_buttons)

        info_buttons = build_info_keyboard()
        if info_buttons:
            keyboard.append(info_buttons)

        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            f"📚 𝐅𝐨𝐮𝐧𝐝 <b>{total}</b> 𝐫𝐞𝐬𝐮𝐥𝐭𝐬 (𝐩𝐚𝐠𝐞 {page+1}/{(total+RESULTS_PER_PAGE-1)//RESULTS_PER_PAGE}):",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

    elif data == "info":
        text = (
            "📚 <b>𝐏𝐃𝐅 𝐋𝐢𝐛𝐫𝐚𝐫𝐲 𝐁𝐨𝐭</b>\n\n"
            f"👤 <b>𝐎𝐰𝐧𝐞𝐫:</b> @Xioqui_xin\n"
            f"📢 <b>𝐂𝐡𝐚𝐧𝐧𝐞𝐥:</b> {FORCE_SUB_CHANNEL if FORCE_SUB_CHANNEL else '𝐍𝐨𝐭 𝐬𝐞𝐭'}\n"
        )
        if REQUEST_GROUP:
            text += f"📝 <b>𝐑𝐞𝐪𝐮𝐞𝐬𝐭 𝐆𝐫𝐨𝐮𝐩:</b> {REQUEST_GROUP}\n"
        text += "\n🔍 <b>𝐇𝐨𝐰 𝐭𝐨 𝐬𝐞𝐚𝐫𝐜𝐡:</b>\n"
        text += "• 𝐓𝐲𝐩𝐞 <code>#book 𝐧𝐚𝐦𝐞</code> 𝐨𝐫 <code>/book 𝐧𝐚𝐦𝐞</code> 𝐢𝐧 𝐚𝐧𝐲 𝐠𝐫𝐨𝐮𝐩.\n"
        text += "• 𝐂𝐥𝐢𝐜𝐤 𝐨𝐧 𝐚 𝐫𝐞𝐬𝐮𝐥𝐭 𝐭𝐨 𝐠𝐞𝐭 𝐭𝐡𝐞 𝐏𝐃𝐅.\n\n"
        text += "📝 <b>𝐑𝐞𝐪𝐮𝐞𝐬𝐭 𝐚 𝐛𝐨𝐨𝐤:</b>\n"
        text += "𝐔𝐬𝐞 <code>#request 𝐧𝐚𝐦𝐞</code> 𝐢𝐧 𝐠𝐫𝐨𝐮𝐩, 𝐨𝐫 <code>/new_request 𝐧𝐚𝐦𝐞</code> 𝐢𝐧 𝐩𝐫𝐢𝐯𝐚𝐭𝐞.\n\n"
        text += "⚠️ <b>𝐍𝐨 𝐜𝐨𝐩𝐲𝐫𝐢𝐠𝐡𝐭𝐞𝐝 𝐨𝐫 𝐢𝐥𝐥𝐞𝐠𝐚𝐥 𝐜𝐨𝐧𝐭𝐞𝐧𝐭</b> – 𝐨𝐧𝐥𝐲 𝐬𝐞𝐥𝐟-𝐢𝐦𝐩𝐫𝐨𝐯𝐞𝐦𝐞𝐧𝐭 𝐚𝐧𝐝 𝐩𝐮𝐛𝐥𝐢𝐜 𝐝𝐨𝐦𝐚𝐢𝐧 𝐛𝐨𝐨𝐤𝐬."
        query.edit_message_text(text, parse_mode=ParseMode.HTML)

callback_handler = CallbackQueryHandler(button_callback)
