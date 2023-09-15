from configuration import Config
from models.server import Server

config = Config()
subscriptions_db = config.get_db().subscriptions
servers_db = config.get_db().servers


def cron():
    servers = list(servers_db.find({}))

    for server in servers:
        server = Server.model_validate(server)
        clients = server.get_clients()
        server.reset_traffic()
        for client in clients:
            usage = (client['up'] + client['down']) / (1024 ** 3)
            subscriptions_db.update_one(
                {f'servers.{server.mongo_id}': client['email']},
                {'$inc': {
                    f'servers.{server.mongo_id}.1': usage,
                    'usage': usage
                }}
            )
