import base64
import datetime
import uuid

from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Dict, Tuple, List, Type, Optional, Any, Union

from models.server import Server
from utilities.api_call import generate_client, get_inbound
from utilities.unique_generators import generate_unique_email, generate_unique_uuid
from utilities import share
from minute_tasks.add_client import add_job
from configuration import Config

config = Config()
servers_db = config.get_db().servers
subscriptions_db = config.get_db().subscriptions


class Subscription(BaseModel):
    """
    Subscription Model representing user subscriptions.
    """
    mongo_id: uuid.UUID = Field(default_factory=lambda: generate_unique_uuid(subscriptions_db), alias="_id",
                                description="The MongoDB Object ID")
    active: bool = True
    expiry_time: datetime.datetime
    name: str
    pause: bool = False
    product: ObjectId
    servers: Dict[ObjectId, Tuple[str, float]] = Field(default_factory=dict,
                                                       description="A dictionary with ObjectId keys and Tuple of ("
                                                                   "str, float) values")
    traffic: float
    usage: float = 0.0
    user_id: int

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, (self.expiry_time - datetime.datetime.now()).total_seconds())

    @property
    def uuid_decoded(self):
        return base64.b64encode(self.mongo_id.bytes).rstrip(b"=").decode("utf-8")

    def initiate_on_servers(self) -> bool:
        """
        Initiate the subscriptions on servers.
        """
        if subscriptions_db.find_one({'_id': self.mongo_id}):
            raise ValueError(f'{self.name} Already initiated')

        server_ids = [ObjectId(x) for x in self.servers.keys()]
        servers = [Server.model_validate(data) for data in servers_db.find({'_id': {'$in': server_ids}})]

        for server in servers:
            client = generate_client(self.traffic, int(self.remaining_seconds),
                                     self.servers[server.mongo_id][0], f'{self.mongo_id}')
            add_job(client, server)

        return True

    def add_servers(self, servers: List[Server]) -> bool:
        for server in servers:
            if server.mongo_id in self.servers:
                continue

            self.servers[server.mongo_id] = (generate_unique_email(server.mongo_id), 0.0)

        return True

    def get_links(self) -> Dict[ObjectId, str]:
        server_ids = [ObjectId(x) for x in self.servers.keys()]
        servers = [Server.model_validate(data) for data in servers_db.find({'_id': {'$in': server_ids}})]

        links = {}
        for server in servers:
            response = get_inbound(server.url, server.panel_username, server.panel_password, server.inbound_id)
            response = response.json()['obj']
            del response['settings']

            if response['protocol'] == 'vmess':
                links[server.mongo_id] = share.generate_vmess_link(response, server.connect_domain, f'{self.mongo_id}',
                                                                   f'{self.name} {server.name}')
            if response['protocol'] == 'vless':
                links[server.mongo_id] = share.generate_vless_link(response, server.connect_domain, f'{self.mongo_id}',
                                                                   f'{self.name} {server.name}')

        return links

    def get_links_message(self) -> str:
        text = ''

        for server_id, link in self.get_links().items():
            server = Server.model_validate(servers_db.find_one({'_id': ObjectId(server_id)}))
            text += f'`{link}`\n{server.name}\n\n'

        return text

    def model_dump(self, **kwargs):
        output = super().model_dump(**kwargs)
        output['servers'] = {str(key): value for key, value in self.servers.items()}
        return output

    @classmethod
    def model_validate(
        cls: type[BaseModel],
        obj: Any,
        *,
        strict: Union[bool, None] = None,
        from_attributes: Union[bool, None] = None,
        context: Union[Dict[str, Any], None] = None,
    ) -> 'Subscription':
        if isinstance(obj, dict):
            obj['servers'] = {ObjectId(key): value for key, value in obj['servers'].items()}
        return super().model_validate(obj, strict=strict, from_attributes=from_attributes, context=context)

    class Config:
        arbitrary_types_allowed = True
