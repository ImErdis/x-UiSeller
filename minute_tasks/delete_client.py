import time
from collections import defaultdict

from bson import ObjectId

from configuration import Config
from models.server import Server

config = Config()
servers_db = config.get_db().servers
delete_queue_db = config.get_db().delete_queue

def add_job(uuid: str, server: ObjectId) -> bool:
    delete_queue_db.insert_one({'uuid': uuid, 'server': server})
    return True

def cron():
    # Fetch all jobs from the delete queue
    current_queue = list(delete_queue_db.find({}))

    # Group jobs by server
    jobs_by_server = defaultdict(list)
    for job in current_queue:
        jobs_by_server[job['server']].append(job)

    for server_id, jobs in jobs_by_server.items():
        # Fetch the server associated with these jobs
        server_data = servers_db.find_one({'_id': server_id})
        if server_data:
            server = Server.model_validate(server_data)

            # Delete clients associated with this server
            for job in jobs:
                server.delete_client(job['uuid'])
                # Remove the job from the queue immediately after processing
                delete_queue_db.delete_one({'_id': job['_id']})
                time.sleep(0.2)  # Sleep between client deletions
