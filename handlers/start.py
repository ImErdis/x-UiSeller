import telegram.constants
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from utilities.menus import start_menu
from configuration import Config
from utilities.user_handlers import process_user

# Initialize the configuration
config = Config()


async def start(update: Update, context):
    """Sends a welcome message with inline buttons."""
    # Process the user and retrieve or create a User object
    user = process_user(update.message.from_user, context)

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

    if keyboard:
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = '🔌 لطفا برای استفاده از خدمات ما در کانال های زیر عضو شوید. '
        return await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    # Create the reply markup for the start menu
    reply_markup = start_menu(user)

    # Welcome message text
    text = f"""👋 به ربات *{config.get_botname()}* خوش آمدید!
    
_"{config.punch_line}"_

🌐 از اینکه سرویس های مارا انتخاب کردید متشکریم"""

    # Send the welcome message with the reply markup
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
