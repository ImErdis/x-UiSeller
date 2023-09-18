import pymongo as pymongo
import yaml


class Config:

    def __init__(self, path='configuration.yaml'):
        with open(path, 'r', encoding='utf-8') as stream:  # added encoding='utf-8'
            self.config = yaml.safe_load(stream)
        stream.close()
        self.mode = self.config['mode']
        self.token = self.config[self.mode][0]['token']
        self.botname = self.config[self.mode][0]['botname']
        self.username = self.config[self.mode][0]['username']
        self.support_id = self.config[self.mode][0]['support-id']
        self.channel_id = self.config[self.mode][0]['channel-id']
        self.punch_line = self.config[self.mode][0]['punch-line']
        self.test_traffic = float(self.config[self.mode][0]['test-subscription-traffic'])
        self.test_time = int(self.config[self.mode][0]['test-subscription-time'])
        self.subscription_domain = self.config[self.mode][0]['subscription-domain']
        self.payment_key = self.config[self.mode][0]['cryptomus-payment-key']
        self.merchant_uuid = self.config[self.mode][0]['cryptomus-merchant-uuid']
        self.portal_url = self.config[self.mode][0]['irr-portal'][0]['link']
        self.portal_key = self.config[self.mode][0]['irr-portal'][0]['key']
        self.traffic_plans = self.config[self.mode][0]['traffic-plans']
        client = pymongo.MongoClient(self.config[self.mode][0]['database'], uuidRepresentation="standard")
        self.db = client.xui
        self.admin = self.config[self.mode][0]['admin']

    def get_mode(self):
        return self.mode

    def get_support_id(self):
        return self.support_id

    def get_channel_id(self):
        return self.channel_id

    def get_token(self):
        """return token from the configuration file
        """
        return self.config[self.mode][0]['token']

    def get_botname(self):

        return self.config[self.mode][0]['botname']

    def get_username(self):

        return self.config[self.mode][0]['username']

    def get_db(self):

        return self.db

    def show_label(self):
        from ansimarkup import ansiprint as print
        from pyfiglet import figlet_format
        print("<yellow>"+figlet_format(self.botname)+"</yellow>")
        print("<yellow>@"+ self.username +"</yellow>\n<green>https://t.me/" + self.username+'</green>' )
        if self.mode == 'dev':
            print('<red>'+ self.mode + '-mode</red>')