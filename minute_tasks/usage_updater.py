from telegram import helpers

from configuration import Config
from models.server import Server
import logging

from minute_tasks.send_notification import add_job
from models.subscription import Subscription

config = Config()
subscriptions_db = config.get_db().subscriptions
servers_db = config.get_db().servers


def cron():
    servers = list(servers_db.find({}))

    for server_dict in servers:
        try:
            server = Server.model_validate(server_dict)
        except Exception as e:
            logging.error(f"Error validating server {server_dict.get('_id', 'unknown')}: {e}")
            continue  # Skip to the next server if validation fails

        try:
            clients = server.get_clients()
            server.reset_traffic()
        except Exception as e:
            logging.error(f"Server operation failed for {server.mongo_id}: {e}")
            continue  # Skip to the next server if there's a network-related issue

        for client in clients:
            try:
                # Use .get() for safe access with a default value of 0 if not found
                usage = (client.get('up', 0) + client.get('down', 0)) / (1024 ** 3)
                subscription_data = subscriptions_db.find_one({f'servers.{server.mongo_id}': client['email']})
                if subscription_data:
                    try:
                        subscription = Subscription.model_validate(subscription_data)
                        # Check if subscription usage is within expected limits before proceeding
                        if subscription.traffic - subscription.usage >= subscription.traffic * 0.1 >= subscription.traffic - (subscription.usage + usage):
                            add_job(f'⚠ کاربر گرامی، کمتر از **ده‌درصد** حجم خریداری شده اشتراک  `{helpers.escape_markdown(subscription.name, version=2)}`   باقی مانده.', subscription.user_id)
                    except Exception as e:
                        logging.error(f"Error validating subscription data: {e}")

                subscriptions_db.update_one(
                    {f'servers.{server.mongo_id}': client['email']},
                    {'$inc': {
                        f'servers.{server.mongo_id}.1': usage,
                        'usage': usage
                    }}
                )
            except KeyError as e:
                logging.warning(f"Missing key {e} in client data for server {server.mongo_id}")
            except Exception as e:
                logging.error(
                    f"Error updating usage for client {client.get('email', 'unknown')} on server {server.mongo_id}: {e}")
