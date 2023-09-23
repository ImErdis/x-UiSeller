import telegram
from telegram import Update, InlineKeyboardButton
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

    keyboard = []

    # Check if user is joined in the enforced channels
    for enforced_channel in config.enforced_channels:
        try:
            member = await update.get_bot().get_chat_member(chat_id=enforced_channel['id'], user_id=user.id)
            if not any([member.status == x for x in [telegram.constants.ChatMemberStatus.MEMBER, telegram.constants.ChatMemberStatus.ADMINISTRATOR, telegram.constants.ChatMemberStatus.OWNER, telegram.constants.ChatMemberStatus.RESTRICTED]]):
                keyboard.append([InlineKeyboardButton(f'Channel {len(keyboard) + 1}', url=enforced_channel['link'])])
        except telegram.error.Forbidden:
            continue
        except telegram.error.BadRequest:
            continue

    # Create the reply markup for the start menu
    reply_markup = start_menu(user)

    punch_line = f'_"{config.punch_line}"_'

    # Welcome message text
    text = f"""👋 به ربات *{config.get_botname()}* خوش آمدید!
    
{punch_line if config.punch_line else None}

🌐 از اینکه سرویس های مارا انتخاب کردید متشکریم"""

    # Send the welcome message with the reply markup
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return ConversationHandler.END
