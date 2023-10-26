import json
from ipaddress import IPv4Address

from bson import ObjectId
from pydantic import BaseModel, Field, constr
from pydantic.v1 import validator

from configuration import Config
from utilities.api_call import (add_clients, get_client, get_inbound,
                                remove_client, reset_inbound_traffic)
from utilities.share import generate_vless_link, generate_vmess_link

config = Config()
servers_db = config.get_db().servers


class Server(BaseModel):
    """
    Represents a server configuration.

    Attributes:
        mongo_id (ObjectId): The MongoDB document ID.
        name (str): The name of the server.
        inbound_id (int): The inbound ID.
        ip_address (IPv4Address): The IP address of the server.
        panel_port (int): The port for panel access.
        panel_username (str): The username for panel access.
        panel_password (str): The password for panel access.
        connect_domain (str): The domain for connecting to the server.
        scheme (str): The URL scheme (default is "http").

    Methods:
        validate_port(v): Validates the panel port.
        get_link(data, uuid): Generates a link based on the protocol.
        id: Property to access the MongoDB ID.
        url: Constructs and returns the URL.

    """
    mongo_id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    name: str
    inbound_id: int
    ip_address: IPv4Address  # Use IPv4Address for stricter IP validation.
    panel_port: int
    panel_username: str
    panel_password: constr(min_length=1)  # Ensure the password is not empty.
    connect_domain: str
    scheme: str = "http"  # Default to "http". Can be overridden if needed.

    @validator("panel_port")
    def validate_port(self, v):
        """
        Validates that the panel port is within a valid range (0-65535).

        Args:
            v (int): The panel port to validate.

        Returns:
            int: The validated panel port.

        Raises:
            ValueError: If the port is not within the valid range.
        """
        if not 0 <= v <= 65535:
            raise ValueError("Panel port must be between 0 and 65535")
        return v

    def get_link(self, data, uuid):
        """
        Generates a link based on the protocol (vless or vmess).

        Args:
            data (dict): Protocol-specific data.
            uuid (str): The UUID for the link.

        Returns:
            str: The generated link.
        """
        if data['protocol'] == 'vless':
            return generate_vless_link(data, self.connect_domain, uuid, self.name)
        if data['protocol'] == 'vmess':
            return generate_vmess_link(data, self.connect_domain, uuid, self.name)

    @property
    def id(self):
        """
        Property to access the MongoDB ID.

        Returns:
            ObjectId: The MongoDB document ID.
        """
        return self._id

    @property
    def url(self) -> str:
        """
        Constructs and returns the URL.

        Returns:
            str: The constructed URL.
        """
        return f"{self.scheme}://{self.ip_address}:{self.panel_port}"

    def reset_traffic(self):
        """
        Resets the traffic for the server.
        """
        return reset_inbound_traffic(self.url, self.panel_username, self.panel_password, self.inbound_id)

    def add_client(self, data: list):
        """
        Adds a client to the server.

        Args:
            data (list): The list containing client data.

        Returns:
            str: The generated link.
        """
        return add_clients(self.url, self.panel_username, self.panel_password, self.inbound_id, data)

    def delete_client(self, uuid):
        """
        Deletes a client from the server.

        Args:
            uuid (str): The UUID of the client to delete.
        """
        return remove_client(self.url, self.panel_username, self.panel_password, self.inbound_id, uuid)

    def get_clients(self):
        """
        Gets all clients from the server.

        Returns:
            list: The list of clients.
        """
        response = get_inbound(self.url, self.panel_username,
                               self.panel_password, self.inbound_id)
        data = response.json()['obj']
        settings = json.loads(data['settings'])
        clients_data = settings['clients']
        clients = []
        for client in clients_data:
            data = get_client(self.url, self.panel_username, self.panel_password, client['email'])
            if data.status_code == 200:
                clients.append(data.json()['obj'])

        return clients

    class Config:
        arbitrary_types_allowed = True
