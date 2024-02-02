import logging
from configuration import Config
from models.server import Server

config = Config()
servers_db = config.get_db().servers
add_queue_db = config.get_db().add_queue  # MongoDB collection for adding clients queue


def add_job(account, server: Server) -> bool:
    try:
        add_queue_db.insert_one({'account': account, 'server': server.mongo_id})
        logging.info(f"Enqueued job for account: {account} on server: {server.mongo_id}")
        return True
    except Exception as e:
        logging.error(f"Failed to enqueue job for account: {account} on server: {server.mongo_id}. Error: {e}")
        return False


def cron():
    try:
        current_queue = list(add_queue_db.find({}))
    except Exception as e:
        logging.error(f"Failed to fetch jobs from the queue. Error: {e}")
        return

    if not current_queue:
        logging.info("The add queue is empty.")
        return

    grouped_accounts = {}
    for job in current_queue:
        grouped_accounts.setdefault(job['server'], []).append(job['account'])

    server_ids = list(grouped_accounts.keys())
    try:
        servers = [Server.model_validate(data) for data in servers_db.find({'_id': {'$in': server_ids}})]
    except Exception as e:
        logging.error(f"Error validating servers. Error: {e}")
        return

    for server in servers:
        accounts_to_add = grouped_accounts[server.mongo_id]
        try:
            server.add_client(accounts_to_add)
            add_queue_db.delete_many({'server': server.mongo_id, 'account': {'$in': accounts_to_add}})
            logging.info(f"Successfully added clients for server: {server.mongo_id}")
        except Exception as e:
            logging.error(f"Failed to add clients for server: {server.mongo_id}. Error: {e}")
