import telegram
from bson import ObjectId
from telegram.ext import CallbackContext
from configuration import Config
from models.user import User, Roles
from models.referral import Referral

# Initialize the configuration
config = Config()

# Access the 'users' database from the configuration
users = config.get_db().users
referrals = config.get_db().referrals


def process_user(chat: telegram.User, context: CallbackContext):
    # Attempt to find the user in the database
    user_data = users.find_one({'_id': chat.id})

    if user_data:
        # If the user exists, create a User object using the retrieved data
        user = User.model_validate(user_data)
    else:
        # If the user doesn't exist, create a new User object
        user = User(_id=int(chat.id))
        if context.args:
            if context.args[0].startswith('refu'):
                referrer = users.find_one({'_id': int(context.args[0][4:])})
                if referrer:
                    referrer = User.model_validate(referrer)
                    user.referrer = {
                        'type': 'User',
                        'id': referrer.id
                    }
            if context.args[0].startswith('refs'):
                referrer = referrals.find_one({'_id': ObjectId(context.args[0][4:])})
                if referrer:
                    referrer = Referral.model_validate(referrer)
                    user.referrer = {
                        'type': 'System',
                        'id': referrer.mongo_id
                    }

        # Check if the user is an admin based on the configured admin ID
        if config.admin == chat.id:
            user.change_role(Roles.Admin.value)

        # Insert the user into the database
        users.insert_one(user.model_dump())

    return user