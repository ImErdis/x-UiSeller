import re

from bson import ObjectId
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

from callback.lists import list_referrals
from configuration import Config
from models.user import Roles
from models.referral import Referral
from utilities.menus import referrals_list
from utilities.user_handlers import process_user

config = Config()
subscriptions_db = config.get_db().subscriptions
referrals_db = config.get_db().referrals


async def control(update: Update, context):
    """Sends a message with Contact information."""

    # Process user data and retrieve query
    query = update.callback_query
    user = process_user(query.from_user, context)

    # If the user is not an admin, return
    if user.role != Roles.Admin:
        return

    # Retrieve the referral from the database
    match = re.findall(r"\{(.*?)}", query.data)
    referral = referrals_db.find_one({'_id': ObjectId(match[0])})
    if not referral:
        return

    await query.answer()

    referral = Referral.model_validate(referral)

    text = f"""💼 اطلاعات *رفرال*.
    
 👥 *تعداد زیرمجموعه ها*:{referral.amount}
💰 *کل خرید*: {referral.total_charge:,} تومان

🔋 لینک *دعوت* زیرمجموعه:
`{referral.link}`
    """

    keyboard = [
        [InlineKeyboardButton("❌ حذف رفرال", callback_data=f"control-referrals_delete{{{referral.mongo_id}}}")],
        [InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the message with inline keyboard
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


# A function that deletes a referral from the database
async def delete(update: Update, context):
    """Deletes a referral from the database."""

    # Process user data and retrieve query
    query = update.callback_query
    user = process_user(query.from_user, context)

    # If the user is not an admin, return
    if user.role != Roles.Admin:
        return

    # Retrieve the referral from the database
    match = re.findall(r"\{(.*?)}", query.data)
    referral = referrals_db.find_one({'_id': ObjectId(match[0])})
    if not referral:
        return

    # Delete the referral from the database
    referrals_db.delete_one({'_id': ObjectId(match[0])})
    await query.answer('رفرال با موفقیت حذف شد.')

    text = "🗒 لیست رفرال های *کنونی* ربات به شرح زیر میباشد."
    reply_markup = referrals_list(1)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
