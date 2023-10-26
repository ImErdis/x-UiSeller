import base64
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Literal

from flask import Flask, request, render_template, Response

from configuration import Config
from models.subscription import Subscription

config = Config('configuration.yaml')

subscriptions = config.get_db().subscriptions


def bytes_format(value):
    for unit in ['B', 'Kb', 'Mb', 'Gb', 'Tb']:
        if value < 1024.0:
            return f"{value:.1f}{unit}"
        value /= 1024.0


def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
    """Format a date time"""
    if value is None:
        return ""
    if isinstance(value, float):
        value = datetime.fromtimestamp(value)
    return value.strftime(format)


app = Flask(__name__)


def generate_subscription(
        subscription: Subscription,
        config_format: Literal["v2ray", "clash-meta", "clash"],
        as_base64: bool
) -> str:
    if config_format == 'v2ray':
        configs = "\n".join(subscription.get_links().values())
    else:
        raise ValueError(f'Unsupported format "{config_format}"')

    if as_base64:
        configs = base64.b64encode(configs.encode()).decode()

    return configs


app.jinja_env.filters['bytesformat'] = bytes_format
app.jinja_env.filters['datetime'] = format_datetime


@app.route('/subscription', methods=['GET'])
async def response():
    accept_header = request.headers.get("Accept", "")
    user_agent = request.headers.get("User-Agent", "")
    uid = request.args.get('uuid', default='', type=str)
    if not uid:
        return "", 204
    subscription = subscriptions.find_one({'_id': uuid.UUID(uid)})
    if not subscription:
        return "", 204
    subscription = Subscription.model_validate(subscription)
    if not subscription.active:
        return "", 204
    current_time = datetime.now()
    links = [x for x in subscription.get_links().values()]
    links_json = json.dumps(links)
    formatted_links = links_json.replace('"', "'")
    if "text/html" in accept_header:
        return render_template('subscription.html', username=subscription.name,
                               now=current_time,
                               expire=subscription.expiry_time.timestamp(),
                               links=formatted_links, subscription_url=subscription.link,
                               data_limit=subscription.traffic * 1024 ** 3,
                               used_traffic=subscription.usage * 1024 ** 3)

    def get_subscription_user_info(sub) -> dict:
        return {
            "upload": 0,
            "download": subscription.usage * 1024 ** 3,
            "total": subscription.traffic * 1024 ** 3,
            "expire": subscription.expiry_time.timestamp(),
        }

    response_headers = {
        "content-disposition": f'attachment; filename="{subscription.name}"',
        "profile-update-interval": "12",
        "subscription-userinfo": "; ".join(
            f"{key}={val}"
            for key, val in get_subscription_user_info(subscription).items()
            if val is not None
        )
    }

    if re.match('^([Cc]lash-verge|[Cc]lash-?[Mm]eta)', user_agent):
        conf = generate_subscription(subscription, config_format="clash-meta", as_base64=False)
        return Response(response=conf, content_type="text/yaml", headers=response_headers)

    elif re.match('^([Cc]lash|[Ss]tash)', user_agent):
        conf = generate_subscription(subscription, config_format="clash", as_base64=False)
        return Response(response=conf, content_type="text/yaml", headers=response_headers)

    else:
        conf = generate_subscription(subscription, config_format="v2ray", as_base64=True)
        return Response(response=conf, content_type="text/plain", headers=response_headers)

if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=8080)
