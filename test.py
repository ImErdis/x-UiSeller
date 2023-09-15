import json

from configuration import Config
from utilities import api_call
from models.server import Server
from utilities.share import generate_vmess_link, generate_vless_link
import base64
import json

config = Config()
servers = config.get_db().servers

inbound = servers.find({})[0]
inbound = Server.model_validate(inbound)
# print(inbound.url)

response = api_call.get_inbound(inbound.url, inbound.panel_username, inbound.panel_username, 2)
inbound_r = response.json()['obj']
del inbound_r['settings']
print(inbound_r)

print(generate_vless_link(inbound_r, inbound.connect_domain, '7c4cbcea-7691-42c2-8ca1-656b61f3b8fc', inbound.name))
# # inbound_r['streamSettings'] = json.loads(inbound_r['streamSettings'])
# inbound_r['streamSettings'] = json.loads(inbound_r['streamSettings'])
# print(inbound_r['streamSettings'])
# link = V2rayShareLink.vmess(
#     remark=inbound.name,
#     address=f'{inbound.connect_domain}',
#     port=inbound_r['port'],
#     id='2ab850dd-863f-4b88-d309-a54f10f92efa',
#     net=inbound_r['streamSettings']['network'],
#     path=inbound_r['streamSettings']['wsSettings']['path']
# )
# print(link)
# pattern = r'[a-fA-F0-9]{24}'
# object_ids = re.findall(pattern, text)
#
# # Convert hexadecimal strings to actual ObjectIds
# object_ids = [ObjectId(oid) for oid in object_ids]
#
# print(object_ids)