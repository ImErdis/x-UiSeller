import base64
import json
import urllib.parse as urlparse
from typing import Union


def generate_vmess_link(data: dict, address: str, id: str, remark: str) -> Union[str, None]:
    """
    Generates a vmess link based on the provided data.

    :param data: A dictionary containing the configuration details.
    :param address: The server address.
    :param id: The user ID.
    :param remark: A remark or description for the link.
    :return: A vmess link as a string, or None if an error occurs.
    """
    try:
        stream_settings = json.loads(data.get('streamSettings', '{}'))
        sniffing = json.loads(data.get('sniffing', '{}'))
        tls_settings = stream_settings.get('tlsSettings', {})

        network = stream_settings.get('network')
        if network in ['ws', 'tcp']:
            payload = {
                'add': address,
                'aid': '0',
                'id': str(id),
                'net': network,
                'port': data['port'],
                'ps': remark,
                'scy': 'auto',
                'tls': stream_settings.get('security', ''),
                'v': '2',
                'sni': tls_settings.get('settings', {}).get('serverName', ''),
                'fo': ','.join(sniffing.get('destOverride', [])),
                'alpn': ','.join(tls_settings.get('alpn', ['http/1.1']))
            }
            if network == 'ws':
                ws_settings = stream_settings['wsSettings']
                payload.update({
                    'host': ws_settings['headers'].get('Host', ''),
                    'path': ws_settings['path'],
                    'type': ws_settings['headers'].get('type', '')
                })
            elif network == 'tcp':
                header_settings = stream_settings.get('tcpSettings', {}).get('header', {})
                payload['type'] = header_settings.get('type', '') if header_settings.get('type') == 'http' else ''

            encoded_payload = base64.b64encode(json.dumps(payload, sort_keys=True).encode('utf-8')).decode()
            return "vmess://" + encoded_payload
        else:
            return None
    except (KeyError, json.JSONDecodeError):
        return None


def generate_vless_link(data: dict, address: str, id: str, remark: str) -> str:
    """
    Generates a vless link based on the provided JSON input.

    :param data: A dictionary containing the configuration details.
    :param address: The server address.
    :param id: The user ID.
    :param remark: A remark or description for the link.
    :return: A vless link as a string.
    """
    port = data.get('port', 8080)
    stream_settings = json.loads(data.get('streamSettings', '{}'))
    net = stream_settings.get('network', 'ws')
    tls = stream_settings.get('security', 'none')

    # Initialize default values
    payload = {
        "security": tls,
        "type": net,
        "host": '',
        "headerType": '',
        "path": '',
        "sni": '',
        "fp": '',
        "alpn": '',
        "pbk": '',
        "sid": '',
        "spx": ''
    }

    if net == 'ws':
        ws_settings = stream_settings.get('wsSettings', {})
        payload['path'] = ws_settings.get('path', '/')
        payload['host'] = ws_settings.get('headers', {}).get('Host', '')
    elif net == 'tcp':
        tcp_settings = stream_settings.get('tcpSettings', {})
        payload['headerType'] = tcp_settings.get('header', {}).get('type', '')

    if tls in ['tls', 'reality']:
        tls_settings = stream_settings.get(f'{tls}Settings', {})
        payload.update({
            'sni': tls_settings.get('serverNames', [])[0] if tls_settings.get('serverNames') else '',
            'fp': tls_settings.get('settings', {}).get('fingerprint', ''),
            'alpn': ','.join(tls_settings.get('alpn', [])),
            'pbk': tls_settings.get('settings', {}).get('publicKey', ''),
            'sid': tls_settings.get('shortIds', [])[0] if tls_settings.get('shortIds') else '',
            'spx': tls_settings.get('settings', {}).get('spiderX', '')
        })

    return "vless://" + \
        f"{id}@{address}:{port}?" + \
        urlparse.urlencode(payload) + f"#{urlparse.quote(remark)}"
