"""
index.py
---------
index all function handlers
"""

# imports here -----------------------
from callback.control_products import control_products, change_product_status
from callback.contact_info import contact_info
from callback.users.user_info import user_info
from callback.lists import list_users, list_products, list_servers, list_referrals, list_subscriptions, list_prices
from callback.menu import menu
from callback.subscriptions.connect_url import connect_url
from callback.subscriptions.get_test import get_test
from callback.subscriptions.info import info
from callback.users.control import control as control_users
from callback.referrals.control import control as control_referrals
from callback.referrals.control import delete as control_referrals_delete

command_map = {
    '^menu$': menu,
    '^contact_info$': contact_info,
    '^user_info$': user_info,
    '^list-users': list_users,
    '^list-servers': list_servers,
    '^list-products': list_products,
    '^list-subscriptions': list_subscriptions,
    '^list-referrals': list_referrals,
    '^list-prices': list_prices,
    '^control-products{': control_products,
    '^control-products_status{': change_product_status,
    '^test-subscriptions$': get_test,
    '^connect_url-subscriptions{': connect_url,
    '^control-subscriptions{': info,
    '^control-users{': control_users,
    '^control-referrals{': control_referrals,
    '^control-referrals_delete{': control_referrals_delete,

}


# --------------------------------------
def handlers():
    """

    """
    return command_map

