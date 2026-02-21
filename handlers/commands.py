def book_search(update: Update, context: CallbackContext):
    """Handle /book command to search for books."""
    user = update.effective_user
    update_user(user.id, user.first_name, user.username)

    # Lock check
    if is_bot_locked() and user.id != OWNER_ID:
        update.message.reply_text("🔒 Bot is currently locked.")
        return

    # Force subscribe check
    if FORCE_SUB_CHANNEL and not check_subscription(user.id, context.bot):
        keyboard = [[InlineKeyboardButton("🔔 Join Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL[1:]}")]]
        update.message.reply_text(
            "⚠️ You must join our channel to search for books.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Check if arguments provided
    if not context.args:
        update.message.reply_text(
            "📚 Please provide a book name.\n"
            "Example: <code>/book The Art of Being Alone</code>",
            parse_mode=ParseMode.HTML
        )
        return

    query = ' '.join(context.args).strip()
    if not query:
        update.message.reply_text("Please enter a valid book name.")
        return

    from database import search_files
    results = search_files(query)
    if not results:
        update.message.reply_text("❌ No books found matching your query.")
        log_to_channel(context.bot, f"Search '{query}' by {user.first_name} – no results")
        return

    context.user_data['search_results'] = results
    context.user_data['current_page'] = 0
    send_results_page(update, context, 0)

# Also need to define send_results_page – it's the same as before, but we'll copy it here or import.
# For simplicity, we'll copy the function inside this file.

def send_results_page(update, context, page):
    from database import search_files  # already imported
    from utils import format_size, build_info_keyboard
    from config import RESULTS_PER_PAGE

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
        f"📚 Found <b>{total}</b> results (page {page+1}/{(total+RESULTS_PER_PAGE-1)//RESULTS_PER_PAGE}):",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

# Then include in get_handlers:
def get_handlers():
    return [
        CommandHandler("start", start),
        CommandHandler("help", help_command),
        CommandHandler("stats", stats, Filters.chat_type.groups),
        CommandHandler("users", users, Filters.chat_type.groups),
        CommandHandler("broadcast", broadcast, Filters.chat_type.groups),
        CommandHandler("lock", lock, Filters.chat_type.groups),
        CommandHandler("unlock", unlock, Filters.chat_type.groups),
        CommandHandler("import", import_db, Filters.chat_type.groups),
        CommandHandler("export", export_db, Filters.chat_type.groups),
        CommandHandler("delete_db", delete_db, Filters.chat_type.groups),
        CommandHandler("confirm_delete", confirm_delete, Filters.chat_type.groups),
        CommandHandler("new_request", new_request, Filters.chat_type.private),
        CommandHandler("book", book_search, Filters.chat_type.groups),  # <-- new
    ]
