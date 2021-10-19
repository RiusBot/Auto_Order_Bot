import re
import json
import base64
import logging
from typing import List, Tuple
from src.config import config
# from src.image_recognition import image_recognize


def parse_pro(message: str):
    symbol_list = []
    action = None
    try:
        pro_message = base64.b64decode(message.encode("ascii")).decode("ascii")
        pro_message = json.loads(pro_message)
        symbol_list = pro_message["symbol_list"]
        action = pro_message["action"]
        if config["exchange_setting"]["exchange"] == "ftx":
            if config["order_setting"]["target"] == "FUTURE":
                symbol_list = [i.replace("/USDT", "-PERP") for i in symbol_list]
            else:
                symbol_list = [i.replace("/USDT", "/USD") for i in symbol_list]
            symbol_list[0] = symbol_list[0].replace("1000SHIB", "SHIB")

    except Exception:
        logging.info("Not encoded message.")
    logging.info(f"symbol_list: {symbol_list}, action: {action}")
    return symbol_list, action


def parse_symbol_regex(message: str) -> List[str]:
    # regex
    try:
        symbol_list = re.findall('#[^\s]+', message)
        logging.info(f"Regex parsing: {symbol_list}")
        return symbol_list
    except Exception:
        logging.error("Failed")
        logging.exception("")
        return []


def parse_symbol_tokens(message: str):
    # check each token
    try:
        symbol_list = []
        if "setup" in message:
            for token in re.split("\n| ", message):
                if token:
                    token = re.compile("[^a-zA-Z0-9]").sub('', token)
                    symbol_list.append(token)
        logging.info(f"Backup parsing: {symbol_list}")
        return symbol_list
    except Exception:
        logging.error("Failed")
        logging.exception("")
        return []


def parse_symbol_filter(message: str):
    # filter strange typing
    try:
        symbol_list = []
        firstline = message.split('\n')[0]
        for keyword in (config["keywords"]["long"] + config["keywords"]["short"]):
            for m in re.compile(keyword).finditer(firstline):
                token = firstline[:m.start()]
                token = re.compile("[^a-zA-Z0-9]").sub('', token)
                symbol_list.append(token)
                logging.info(f"Filter parsing: {symbol_list}")
                return symbol_list
        return symbol_list
    except Exception:
        logging.error("Failed")
        logging.exception("")
        return []


def parse_symbol(message: str, img_path: str):
    symbol_list1 = parse_symbol_regex(message)
    symbol_list2 = parse_symbol_tokens(message)
    symbol_list3 = parse_symbol_filter(message)
    symbol_list = list(set(symbol_list1) | set(symbol_list2) | set(symbol_list3))

    # if img_path is not None:
    #     img_symbol_list = image_recognize(img_path)
    #     symbol_list = list(set(symbol_list) | set(img_symbol_list))

    logging.info(f"Parse symbol: {symbol_list}")
    return symbol_list


def parse_action(message: str):
    action = None
    if any(map(message.split().__contains__, config["keywords"]["long"])):
        action = "buy"
    elif any(map(message.split().__contains__, config["keywords"]["short"])):
        action = "sell"

    logging.info(f"Parse action: {action}")
    return action


def parse_symbol_substitute(message: str):
    symbol_map = {
        'α': "a",
        "ℓ": "l",
        "ι": "i",
        "¢": "c",
        "є": "e",
        "$": "s",
        "0": "o"
    }
    for i in range(26):
        symbol_map[chr(ord("Ⓐ") + i)] = chr(ord('a') + i)
    for i in range(26):
        symbol_map[chr(ord("ⓐ") + i)] = chr(ord('a') + i)

    # substitute
    new_str = ""
    for c in message:
        if c in symbol_map:
            new_str += symbol_map[c]
        else:
            new_str += c
    return new_str


def parse(message: str, base: str, img_path) -> Tuple[List[str], str]:
    if config["telegram_setting"]["signal"] == "Rose":
        message = message.lower()
        message = parse_symbol_substitute(message)
        symbol_list = parse_symbol(message, img_path)
        action = parse_action(message) if symbol_list else None
    elif config["telegram_setting"]["signal"] == "Perpetual":
        symbol_list = re.findall('#[^\s]+', message)
        symbol_list = [i.replace('#', '') for i in symbol_list]
        action = None
        if "看漲" in message:
            action = "buy"
        elif "看跌" in message:
            action = "sell"
    return symbol_list, action
