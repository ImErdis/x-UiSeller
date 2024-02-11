import httpx
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient
from configuration import Config

# Initialize configuration
config = Config()

# Initialize an asynchronous MongoDB client and select the database and collection
client = AsyncIOMotorClient(config.mongo_uri)['xui']
notifications_queue = client.notifications_queue  # Ensure the collection name is correct

# Define a keyboard layout for the messages
keyboard = [[InlineKeyboardButton("🖥️ پنل", callback_data="menu")]]
reply_markup = InlineKeyboardMarkup(keyboard)


async def add_job(text, user_id) -> bool:
    """
    Asynchronously adds a notification job to the queue.

    Args:
        text (str): The notification message content.
        user_id (int): The Telegram user ID to send the notification to.

    Returns:
        bool: True if the operation was successful, False otherwise.
    """
    try:
        await notifications_queue.insert_one({'content': text, 'user_id': user_id})
        return True
    except Exception as e:
        print(f"Failed to add job: {e}")  # Logging the exception can help in debugging
        return False


async def cron(bot: Bot):
    """
    The cron job that iterates through the notification queue, sends notifications,
    and removes them from the queue after sending.

    Args:
        bot (Bot): The Telegram Bot instance used for sending messages.
    """
    try:
        current_queue = await notifications_queue.find().to_list(None)  # Retrieve all jobs from the queue
    except Exception as e:
        print(f"Failed to retrieve notification queue: {e}")
        return

    for notification in current_queue:
        try:
            # Attempt to send the notification
            await bot.bot.send_message(notification['user_id'], text=notification['content'],
                                    reply_markup=reply_markup, parse_mode='Markdown')
            # Remove the notification from the queue after successful sending
            await notifications_queue.delete_one({'_id': notification['_id']})
        except Exception as e:
            print(f"Failed to send notification or delete from queue: {e}")
            # Optionally, log the failed notification for retry or review
            continue

