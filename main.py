import asyncio
import threading
import time

from telegram.ext import Application, CallbackQueryHandler
from handlers.index import index
from conversations.index import conversations
from callback.index import handlers
from telegram.ext import CommandHandler
from configuration import Config
from minute_tasks import add_client, delete_client, usage_updater, usage_expiry_scanner, currency_scanner, invoice_check

import logging

from models.prices import Prices

import sys


class StreamToLogger(object):
    """
    Fake file-like stream object that redirects writes to a logger instance.
    """
    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        temp_linebuf = self.linebuf + buf
        self.linebuf = ''
        for line in temp_linebuf.splitlines(True):
            # From the io.TextIOWrapper docs:
            #   On output, if newline is None, any '\n' characters written
            #   are translated to the system default line separator.
            # By default sys.stdout.write() expects '\n' newlines and then
            # translates them so this is still cross platform.
            if line[-1] == '\n':
                self.logger.log(self.log_level, line.rstrip())
            else:
                self.linebuf += line

    def flush(self):
        if self.linebuf != '':
            self.logger.log(self.log_level, self.linebuf.rstrip())
        self.linebuf = ''


logging.basicConfig(
    level=logging.INFO,
    format="%(name)s: %(asctime)s | %(levelname)s | %(filename)s:%(lineno)s | %(process)d >>> %(message)s",
    filename="out.log",
    filemode='a'
)

stdout_logger = logging.getLogger('STDOUT')
sl = StreamToLogger(stdout_logger, logging.INFO)
sys.stdout = sl

stderr_logger = logging.getLogger('STDERR')
sl = StreamToLogger(stderr_logger, logging.ERROR)
sys.stderr = sl

config = Config('configuration.yaml')
config.show_label()
subscriptions = config.get_db().subscriptions

def run_periodically(function, interval, *args):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        if asyncio.iscoroutinefunction(function):
            loop.run_until_complete(function(*args))
        else:
            function(*args)
        time.sleep(interval)


def main():
    Prices(name="Default", plans=config.traffic_plans).commit_changes()
    application = Application.builder().token(config.token).build()
    job_queue = application.job_queue

    for k, v in index().items():
        application.add_handler(CommandHandler(k, v))
    for k, v in handlers().items():
        application.add_handler(CallbackQueryHandler(v, pattern=k))
    for convo in conversations():
        application.add_handler(convo)

    add_user_cron = threading.Thread(target=run_periodically, args=(add_client.cron, 1))
    remove_user_cron = threading.Thread(target=run_periodically, args=(delete_client.cron, 1))
    usage_updater_cron = threading.Thread(target=run_periodically, args=(usage_updater.cron, 15))
    usage_expiry_scanner_cron = threading.Thread(target=run_periodically, args=(usage_expiry_scanner.cron, 60))
    usd_currency_scanner_cron = threading.Thread(target=run_periodically, args=(currency_scanner.usd_cron, 3600))
    crypto_currency_scanner_cron = threading.Thread(target=run_periodically, args=(currency_scanner.crypto_cron, 60))

    add_user_cron.start()
    remove_user_cron.start()
    usage_updater_cron.start()
    usage_expiry_scanner_cron.start()
    usd_currency_scanner_cron.start()
    crypto_currency_scanner_cron.start()
    job_queue.run_repeating(invoice_check.cron_job, interval=30)
    application.run_polling()

main()
