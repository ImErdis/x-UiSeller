import json
import uuid
import httpx
import datetime


def generate_client(totalGB, expiryTime, email, idi=None) -> dict:
    """
    Generate a client dictionary with specified parameters.

    Args:
        totalGB (float): Total gigabytes for the client.
        expiryTime (int): Expiry time in seconds.
        email (str): Email of the client.
        idi (UUID, optional): Client ID (defaults to a new UUID if not provided).

    Returns:
        dict: A dictionary representing the client with specified attributes.
    """
    if not idi:
        idi = uuid.uuid4()
    return {
        'id': f'{idi}',
        'enable': True,
        'email': email,
        'tgId': "",
        "subId": "",
        'totalGB': int(totalGB * 1024 * 1024 * 1024),
        'expiryTime': int((datetime.datetime.now() + datetime.timedelta(seconds=expiryTime)).timestamp() * 1000)
    }


def get_inbounds(url, username, password) -> httpx.Response:
    """
    Get inbounds from a specified URL using authentication.

    Args:
        url (str): URL to the service.
        username (str): Username for authentication.
        password (str): Password for authentication.

    Returns:
        httpx.Response: HTTP response object containing the inbounds data.
    """
    with httpx.Client() as client:
        body = {
            "username": username,
            "password": password
        }
        client.post(url + '/login', data=body)
        r = client.get(url + '/xui/API/inbounds/')
        return r


def update_inbound(url, username, password, idi, data):
    """
    Update an inbound using authentication.

    Args:
        url (str): URL to the service.
        username (str): Username for authentication.
        password (str): Password for authentication.
        idi: Identifier for the inbound.
        data (dict): Data to update the inbound.

    Returns:
        httpx.Response: HTTP response object indicating the success or failure of the update.
    """
    with httpx.Client() as client:
        body = {
            "username": username,
            "password": password
        }
        client.post(url + '/login', data=body)
        r = client.post(f'{url}/xui/API/inbounds/update/{idi}', json=data)
        return r


def get_inbound(url: str, username: str, password: str, idi: int) -> httpx.Response:
    """
    Get a specific inbound by ID using authentication.

    Args:
        url (str): URL to the service.
        username (str): Username for authentication.
        password (str): Password for authentication.
        idi (int): Identifier for the inbound.

    Returns:
        httpx.Response: HTTP response object containing the specific inbound data.
    """
    with httpx.Client() as client:
        body = {
            "username": username,
            "password": password
        }
        client.post(url + '/login', data=body)
        r = client.get(f'{url}/xui/API/inbounds/get/{idi}')
        return r


def add_clients(url, username, password, idi, users) -> httpx.Response:
    """
    Add clients to an inbound using authentication.

    Args:
        url (str): URL to the service.
        username (str): Username for authentication.
        password (str): Password for authentication.
        idi: Identifier for the inbound.
        users (list): List of users to add to the inbound.

    Returns:
        httpx.Response: HTTP response object indicating the success or failure of the operation.
    """
    with httpx.Client() as client:
        body = {
            "username": username,
            "password": password
        }
        client.post(url + '/login', data=body)
        body = {
            "id": idi,
            "settings": json.dumps({
                "clients": users
            })
        }
        r = client.post(url + '/xui/API/inbounds/addClient', data=body)
        return r


def remove_client(url, username, password, idi, _id) -> httpx.Response:
    """
    Remove a client from an inbound using authentication.

    Args:
        url (str): URL to the service.
        username (str): Username for authentication.
        password (str): Password for authentication.
        idi: Identifier for the inbound.
        _id: Identifier for the client to remove.

    Returns:
        httpx.Response: HTTP response object indicating the success or failure of the removal.
    """
    with httpx.Client() as client:
        body = {
            "username": username,
            "password": password
        }
        client.post(url + '/login', data=body)
        r = client.post(url + f'/xui/API/inbounds/{idi}/delClient/{_id}', data=body)
        return r


def reset_inbound_traffic(url, username, password, idi) -> httpx.Response:
    """
    Reset the traffic for an inbound using authentication.

    Args:
        url (str): URL to the service.
        username (str): Username for authentication.
        password (str): Password for authentication.
        idi: Identifier for the inbound.

    Returns:
        httpx.Response: HTTP response object indicating the success or failure of the reset.
    """
    with httpx.Client() as client:
        body = {
            "username": username,
            "password": password
        }
        client.post(url + '/login', data=body)
        r = client.post(url + f'/xui/API/inbounds/resetAllClientTraffics/{idi}')
        return r


def edit_client(url, username, password, idi, _id, user) -> httpx.Response:
    """
    Edit a client in an inbound using authentication.

    Args:
        url (str): URL to the service.
        username (str): Username for authentication.
        password (str): Password for authentication.
        idi: Identifier for the inbound.
        _id: Identifier for the client to edit.
        user (dict): User data for editing.

    Returns:
        httpx.Response: HTTP response object indicating the success or failure of the edit operation.
    """
    with httpx.Client() as client:
        body = {
            "username": username,
            "password": password
        }
        client.post(url + '/login', data=body)
        body = {
            "id": idi,
            "settings": json.dumps({
                "clients": [user]
            })
        }
        r = client.post(url + f'/xui/API/inbounds/updateClient/{_id}', data=body)
        return r


def get_client(url, username, password, email) -> httpx.Response:
    """
    Get client information by email using authentication.

    Args:
        url (str): URL to the service.
        username (str): Username for authentication.
        password (str): Password for authentication.
        email (str): Email of the client to retrieve information for.

    Returns:
        httpx.Response: HTTP response object containing client information.
    """
    with httpx.Client() as client:
        body = {
            "username": username,
            "password": password
        }
        client.post(url + '/login', data=body)
        r = client.get(url + f'/xui/API/inbounds/getClientTraffics/{email}')
        return r
