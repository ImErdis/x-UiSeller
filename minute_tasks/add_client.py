# add_client.py
from configuration import Config
from utilities import api_call
from models.server import Server

config = Config()
servers_db = config.get_db().servers
add_queue_db = config.get_db().add_queue  # New MongoDB collection for adding clients queue


def add_job(account, server: Server) -> bool:
    # Enqueue the job to the database instead of a local dictionary
    add_queue_db.insert_one({'account': account, 'server': server.mongo_id})
    return True


def cron():
    # Fetch all jobs from the add queue
    current_queue = list(add_queue_db.find({}))

    # If the queue is empty, just return
    if not current_queue:
        return

    # Group the accounts by server
    grouped_accounts = {}
    for job in current_queue:
        if job['server'] not in grouped_accounts:
            grouped_accounts[job['server']] = []
        grouped_accounts[job['server']].append(job['account'])

    server_ids = list(grouped_accounts.keys())
    servers = [Server.model_validate(data) for data in servers_db.find({'_id': {'$in': server_ids}})]

    for server in servers:
        accounts_to_add = grouped_accounts[server.mongo_id]
        server.add_client(accounts_to_add)

        # After adding clients for a server, remove those jobs from the queue
        add_queue_db.delete_many({'server': server.mongo_id, 'account': {'$in': accounts_to_add}})
