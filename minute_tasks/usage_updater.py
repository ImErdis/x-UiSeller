from configuration import Config
from models.server import Server
import logging

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
