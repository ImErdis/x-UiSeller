"""
index.py
---------
index all function handlers
"""

# imports here -----------------------
# from conversations import
from conversations import add_servers, add_products, add_referrals, buy_subscriptions, topup, contorl_users_topup, \
    add_prices, search_users, renew_subscriptions

convs = [
    add_servers.conv_handler,
    add_products.conv_handler,
    add_referrals.conv_handler,
    buy_subscriptions.conv_handler,
    renew_subscriptions.conv_handler,
    topup.conv_handler,
    contorl_users_topup.conv_handler,
    add_prices.conv_handler,
    search_users.conv_handler
    # addserver.conv_handler,
    #      createsubscription.conv_handler,
    #      generateacc.conv_handler,
    #      replaceserver.conv_handler,
    #      creategroup.conv_handler,
    #      restoreaccount.conv_handler,
    #      add_reseller.conv_handler,
    #      create_account.conv_handler,
    #      search_account.conv_handler,
    #      renew_account.conv_handler
]


# --------------------------------------
def conversations():
    """

    """
    return convs