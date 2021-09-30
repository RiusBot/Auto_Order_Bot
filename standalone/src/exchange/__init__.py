import ccxt
import json
import logging
from typing import List

from .binance import BinanceClient
from .ftx import FTXClient


def ExchangeClient(config):
    exchange = config["exchange_setting"]["exchange"]
    if exchange == "binance":
        return BinanceClient(config)
    elif exchange == "ftx":
        return FTXClient(config)
    else:
        raise Exception(f"{exchange} exchange not supported")
