import httpx
from configuration import Config

# Initialize configurations and database connection
config = Config()
currencies_db = config.get_db().currencies


def usd_cron():
    """Updates the USD price in the database."""
    with httpx.Client(follow_redirects=True) as client:
        response = client.get(
            url='https://abantether.com/api/v1/otc/coin-price/',
            headers={
                'Authorization': 'Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2NDYxMDkiLCJpYXQiOjE3MDY4ODg5ODQsImV4cCI6MTczODQyNDk4NH0.5yKVzoRDShALiYBHOpHOSolaZ2AG5x8JENQ_Jeq1lsA'}
        )

    # Only proceed if we get a successful response
    if response.status_code == 200:
        data = response.json()
        if 'USDT' in data:
            usdt_data = data['USDT']
            # Check if USD already exists in the database
            if currencies_db.find_one({'name': 'USD'}):
                currencies_db.update_one({'name': 'USD'}, {'$set': {'price': {'USD': 1, 'IRT': float(usdt_data['irtPriceBuy'])}}})
            else:
                # If not, insert a new USD entry
                currencies_db.insert_one({'name': 'USD', 'price': {'USD': 1, 'IRT': float(usdt_data['irtPriceBuy'])}})
            if currencies_db.find_one({'name': 'IRT'}):
                currencies_db.update_one({'name': 'IRT'}, {'$set': {'price': {'USD': 1/float(usdt_data['irtPriceBuy']), 'IRT': 1}}})
            else:
                currencies_db.insert_one({'name': 'IRT', 'price': {'USD': 1/float(usdt_data['irtPriceBuy']), 'IRT': 1}})


def crypto_cron():
    """Updates the crypto prices in the database based on USD conversion."""
    response = httpx.get(url='https://api.cryptomus.com/v1/exchange-rate/USD/list')

    # Only proceed if we get a successful response
    if response.status_code == 200:
        usd_irt_entry = currencies_db.find_one({'name': 'USD'})

        # If we can't find the USD entry in the database, exit the function
        if not usd_irt_entry:
            return

        usd_irt = usd_irt_entry['price']['IRT']

        for currency in response.json()['result']:
            price_usd = 1 / float(currency['course'])
            price_irt = float(price_usd) * float(usd_irt)

            # Check if this crypto currency already exists in the database
            if currencies_db.find_one({'name': currency['to']}):
                currencies_db.update_one({'name': currency['to']},
                                         {'$set': {'price': {'USD': price_usd, 'IRT': price_irt}}})
            else:
                # If not, insert a new crypto currency entry
                currencies_db.insert_one({'name': currency['to'], 'price': {'USD': price_usd, 'IRT': price_irt}})
