import datetime

from configuration import Config
from minute_tasks import delete_client
from models.subscription import Subscription

config = Config()
subscriptions_db = config.get_db().subscriptions


def cron():
    expired_subscriptions = list(subscriptions_db.find({
        'active': True,
        '$or': [
            {'expiry_time': {'$lte': datetime.datetime.now()}},
            {'$expr': {'$gt': ['$usage', '$traffic']}}
        ]
    }))

    for subscription_data in expired_subscriptions:
        subscription = Subscription.model_validate(subscription_data)
        for server in subscription.servers.keys():
            delete_client.add_job(str(subscription.mongo_id), server)
        subscriptions_db.update_one({'_id': subscription.mongo_id}, {'$set': {'active': False}})
