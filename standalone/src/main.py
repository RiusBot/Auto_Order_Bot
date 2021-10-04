from telethon import TelegramClient
from src.config import config, configure_logging
from src.gui import run_gui
from src.telegram_bot import telegram_start
import argparse


parser = argparse.ArgumentParser(add_help=False, description="Data Driven Identification Criteria for GAI.")
parser.add_argument("--gui", default=False, action="store_true", help="GUI")
args = parser.parse_args()


class MockWindow():
    def __init__(self):
        self.__dict__["print"] = print


def telegram_login():
    telegram_client = TelegramClient(
        'anon',
        config["telegram_setting"]["telegram_api_id"],
        config["telegram_setting"]["telegram_api_hash"],
    )
    telegram_client.start()
    telegram_client.disconnect()


def main():
    telegram_login()
    telegram_start(config, {'log': MockWindow()})


if __name__ == "__main__":
    configure_logging()
    if args.gui:
        run_gui()
    else:
        main()
