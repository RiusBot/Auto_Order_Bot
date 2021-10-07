import re
import os
import sys
import time
import json
import asyncio
import pandas as pd
import logging
import traceback
from telethon import TelegramClient, events, sync
from src.exchange import ExchangeClient
from src.config import config
from typing import List, Tuple
import PySimpleGUI as sg


exchange_client = None
telegram_client = None
signal_channel = None
notify_channel = None
window = None


class StdHandler:
    def __init__(self):
        self.file = open(config["log_setting"]["log_path"], 'a')

    def remove_invalid_char(self, s: str):
        astral = re.compile(r'([^\x00-\uffff])')
        new_str = ""
        for i, ss in enumerate(re.split(astral, s)):
            if not i % 2:
                new_str += ss
            else:
                new_str += '?'
        return new_str

    def write(self, s: str):
        s = self.remove_invalid_char(s)
        self.file.write(s)
        window['log'].print(s, end="")

    def flush(self):
        return


class LogHandler():
    def __init__(self):
        self.parse = None
        self.symbol = None
        self.action = None
        self.margin_level = None
        self.order = None
        self.result = None
        self.error = None
        self.info = ""

    def to_log(self):
        return {
            "parse": self.parse,
            "symbols": self.symbol,
            "action": self.action,
            "margin_level": self.margin_level,
            "order": self.order,
            "result": self.result,
            "error": self.error,
            "info": self.info,
        }

    def save(self):
        path = config["log_setting"]["bot_log_path"]
        if not os.path.exists(path):
            pd.DataFrame({key: [] for key in self.to_log()}).to_csv(path, index=False)
        df = pd.read_csv(path)
        df = df.append(self.to_log(), ignore_index=True)
        df.to_csv(path, index=False)

    def __str__(self):
        return json.dumps(self.to_log(), indent=4)

    async def notify(self, message):
        await message.forward_to(notify_channel)
        await telegram_client.send_message(notify_channel, f"Bot reaction:\n{str(self)}")


def get_all_dialogs():
    logging.info("get dialogs")
    all_dialogs = []
    for dialog in telegram_client.iter_dialogs():
        all_dialogs.append(
            {
                "name": dialog.name,
                "id": dialog.id
            }
        )
    logging.debug(f"{all_dialogs}")
    return all_dialogs


def error_handler(func):
    async def warp(event):
        log = LogHandler()
        try:
            await func(log, event)
        except Exception:
            logging.exception("")
            log.error = traceback.format_exc()

        try:
            await log.notify(event.message)
        except Exception as e:
            logging.exception("")
            log.error = traceback.format_exc()
            log.info = str(e)

        log.save()
        print("Bot Reaction:")
        print(str(log))
        print("=============================================")
        print()
        print()

    return warp


@error_handler
async def message_handle(log, event):

    sys.stdout = StdHandler()
    sys.stderr = StdHandler()

    logging.info("")
    logging.info("New message")
    logging.info("=============================================")
    logging.info(event.text)
    logging.info("=============================================")
    print(exchange_client)

    latency = event.date.timestamp() - time.time()
    if latency > float(config["other_setting"]["maximum_latency"]):
        msg = f"latency {latency} > {config['other_setting']['maximum_latency']} too high !!  Rejected."
        logging.info(msg)
        log.info = msg
        return

    img_path = None
    # if config["other_setting"]["use_image"]:
    #     img_path = await telegram_client.download_media(event.photo, 'download_photos')
    symbol_list, action = ExchangeClient(config).parse(event.text, img_path)
    log.parse = True

    if symbol_list:
        log.symbol = symbol_list
    if action:
        log.action = action

    if not symbol_list or action is None:
        return

    if action != "buy":
        return

    order_list, result_list, margin_level = ExchangeClient(config).run(symbol_list)
    log.margin_level = margin_level
    log.order = order_list
    log.result = result_list


def get_channels(config: dict):
    logging.debug("Get channels")
    signal_channel = telegram_client.get_entity(config["telegram_setting"]["signal_channel"])
    notify_channel = telegram_client.get_entity(config["telegram_setting"]["notify_channel"])
    if config["telegram_setting"]["test_channel"] is not None:
        test_channel = telegram_client.get_entity(config["telegram_setting"]["test_channel"])
    logging.info(f"Signal channel: {signal_channel.title}")
    logging.info(f"Notify channel: {notify_channel.title}")
    if config["telegram_setting"]["test_channel"] is not None:
        logging.info(f"Test channel: {test_channel.title}")
    return signal_channel, notify_channel, test_channel


async def signal_handler(event):
    await message_handle(event)


def telegram_start(config: dict, window_):
    global exchange_client
    global telegram_client
    global signal_channel
    global notify_channel
    global window

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logging.getLogger().handlers[0].stream = StdHandler()

        window = window_
        exchange_client = ExchangeClient(config)
        telegram_client = TelegramClient(
            'anon',
            config["telegram_setting"]["telegram_api_id"],
            config["telegram_setting"]["telegram_api_hash"],
        )
        telegram_client.start()

        all_dialogs = get_all_dialogs()
        print(all_dialogs)
        signal_channel, notify_channel, test_channel = get_channels(config)

        telegram_client.add_event_handler(
            signal_handler,
            events.NewMessage(from_users=signal_channel, forwards=False)
        )

        if test_channel is not None:
            telegram_client.add_event_handler(
                signal_handler,
                events.NewMessage(from_users=test_channel, forwards=False)
            )

        # for callback, event in telegram_client.list_event_handlers():
        #     window["output"].print(id(callback), type(event))

        logging.info("Start to listen")
        telegram_client.run_until_disconnected()

    except Exception:
        logging.exception("")
        return
