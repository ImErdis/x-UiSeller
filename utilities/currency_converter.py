from configuration import Config

# Initialize configurations and database connection
config = Config()
currencies_db = config.get_db().currencies


def converter(base: str, to: str = 'IRT'):
    currency = currencies_db.find_one({'name': base})
    if not currency:
        raise NameError
    return currency['price'][to]
