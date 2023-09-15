from telegram import Update
from telegram.ext import ConversationHandler
from utilities.menus import start_menu
from configuration import Config
from utilities.user_handlers import process_user

# Initialize the configuration
config = Config()


async def menu(update: Update, context):
    """Sends a welcome message with inline buttons."""
    query = update.callback_query
    await query.answer()

    # Process the user and retrieve or create a User object
    user = process_user(update.callback_query.from_user, context)

    # Create the reply markup for the start menu
    reply_markup = start_menu(user)

    # Welcome message text
    text = f"""👋 به ربات *{config.get_botname()}* خوش آمدید!

_"{config.punch_line}"_

🌐 از اینکه سرویس های مارا انتخاب کردید متشکریم"""

    # Send the welcome message with the reply markup
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return ConversationHandler.END
