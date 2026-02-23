from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackQueryHandler, CallbackContext
from database import get_file_by_id, increment_download
from config import OWNER_ID, FORCE_SUB_CHANNEL, RESULTS_PER_PAGE, REQUEST_GROUP
from utils import format_size, build_info_keyboard, format_book_caption
import logging

logger = logging.getLogger(__name__)

def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    data = query.data
    if data.startswith("get_"):
        file_id_num = int(data[4:])
        book = get_file_by_id(file_id_num)
        if book:
            # Send preview if exists
            if book.get('preview_file_id'):
                try:
                    context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=book['preview_file_id'],
                        caption="𓍯𓂃♡ִֶָ 🪽 ִֶָ🪽་༘࿐\n📖 **A glimpse of:** {book['original_filename']}",
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    logger.error(f"Preview send failed: {e}")

            # Send PDF with enhanced caption
            caption = f"𓍯𓂃♡ִֶָ 🪽 ִֶָ🪽་༘࿐\n═══════🪼⋆.ೃ࿔*:･\n\n📘 **{book['original_filename']}**\n\n{format_book_caption(book)}"
            context.bot.send_document(
                chat_id=query.message.chat_id,
                document=book['file_id'],
                caption=caption,
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
            query.edit_message_text(
                "𓍯𓂃♡ִֶָ 🪽 ━━━━━━🪼⋆.ೃ࿔*:･\n\n"
                "❌ That book has vanished from my heart. Sorry, darling."
            )

    elif data.startswith("page_"):
        page = int(data[5:])
        context.user_data['current_page'] = page
        results = context.user_data.get('search_results', [])
        if not results:
            query.edit_message_text(
                "𓍯𓂃♡ִֶָ 🪽 ━━━━━━🪼⋆.ೃ࿔*:･\n\n"
                "❌ No results found, my love."
            )
            return
        total = len(results)
        start = page * RESULTS_PER_PAGE
        end = min(start + RESULTS_PER_PAGE, total)
        page_results = results[start:end]

        keyboard = []
        for res in page_results:
            btn_text = f"𓍯𓂃 {res['original_filename']} ({format_size(res['file_size'])})"
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
            keyboard.extend(info_buttons)

        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            f"𓍯𓂃♡ִֶָ 🪽 ━━━━━━🪼⋆.ೃ࿔*:･\n\n"
            f"📚 Found **{total}** treasures (page {page+1}/{(total+RESULTS_PER_PAGE-1)//RESULTS_PER_PAGE}):",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

    elif data == "info":
        text = (
            "𓍯𓂃♡ִֶָ 🪽  ִֶָ🪽་༘࿐\n"
            "═══════🪼⋆.ೃ࿔*:･જ⁀➴\n"
            "**-ˏˋ⋆ ɪ ɴ ꜰ ᴏ ⋆ˊˎ-☕︎**\n"
            "┗━━━━━༻❁༺━━━━━┛\n\n"
            "📚 **About Me, Your Beloved**\n\n"
            f"👤 **My Master:** @Xioqui_xin\n"
            f"📢 **Our Channel:** {FORCE_SUB_CHANNEL if FORCE_SUB_CHANNEL else 'Not set'}\n"
        )
        if REQUEST_GROUP:
            text += f"📝 **Request Group:** {REQUEST_GROUP}\n"
        text += "\n🔍 **How to search my heart:**\n"
        text += "• Type `#book name` or `/book name` in any group.\n"
        text += "• Click on a result to receive the PDF.\n\n"
        text += "📝 **To request a book:**\n"
        text += "Use `#request name` in group, or `/new_request name` in private.\n\n"
        text += "⚠️ **No copyrighted or illegal content** – only pure, public-domain love.\n\n"
        text += "𓍯𓂃 🪽 ִֶָ🪽་༘࿐"
        query.edit_message_text(text, parse_mode=ParseMode.HTML)

callback_handler = CallbackQueryHandler(button_callback)
