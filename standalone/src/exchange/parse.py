import re
import logging
from typing import List, Tuple


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
            for token in message.split(" "):
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
        for m in re.compile("buy").finditer(firstline):
            token = firstline[:m.start()]
            token = re.compile("[^a-zA-Z0-9]").sub('', token)
            symbol_list.append(token)
            logging.info(f"Filter parsing: {symbol_list}")
            break
        return symbol_list
    except Exception:
        logging.error("Failed")
        logging.exception("")
        return []


def parse_symbol(message: str):
    symbol_list1 = parse_symbol_regex(message)
    symbol_list2 = parse_symbol_tokens(message)
    symbol_list3 = parse_symbol_filter(message)
    symbol_list = list(set(symbol_list1) | set(symbol_list2) | set(symbol_list3))
    logging.info(f"Parse symbol: {symbol_list}")
    return symbol_list


def parse_action(message: str):
    action = None
    substring_list = ["buy", "long"]
    if any(map(message.split().__contains__, substring_list)):
        action = "buy"
    substring_list = ["close", "closed", "cut", "stop", "stopped", "reach", "reached", "sell"]
    if any(map(message.split().__contains__, substring_list)):
        action = "sell"
    logging.info(f"Parse action: {action}")
    return action


# def parse_symbol_substitute(message: str, symbol_list: List[str]):
def parse_symbol_substitute(message: str,):

    symbol_map = {
        'α': "a",
        "ℓ": "l",
        "ι": "i",
        "¢": "c",
        "є": "e",
        "$": "s",
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


def parse_justin(message: str):
    action = None
    symbol_list = []

    if "今天" in message and "進" in message:
        action = "buy"
        symbol_list = parse_justin_symbol(message)
    elif "今天" in message and "出" in message:
        action = "sell"
        symbol_list = parse_justin_symbol(message)

    return symbol_list, action


def parse_justin_symbol(message: str):
    message = re.compile('[^a-zA-Z0-9\n]').sub('', message)
    symbol_list = []
    lines = [i.strip() for i in message.split('\n') if i.strip()]
    for line in lines:
        symbol = ""
        for c in line:
            if c.isalpha():
                symbol += c
            else:
                break
        symbol_list.append(symbol)
    return symbol_list


def parse_daily(message: str):
    action = None
    if "long" in message.lower():
        action = "buy"
    elif "short" in message.lower():
        action = "sell"

    sl = None
    tp = None
    entry = None
    symbol_list = []
    lines = [i for i in message.split('\n') if i]
    for e, line in enumerate(lines):
        if e == 0:
            symbol_list = [i.replace("USDT", "").upper() for i in line.split(' ') if i]
            continue

        key, value = line.split(':')
        key, value = key.strip().lower(), value.strip().lower()

        if "entry" in key:
            entry = float(value.split(' ')[0])
        elif "target" in key:
            tp = float(value.split(' ')[0])
        elif "stop loss" in key:
            sl = float(value.split(' ')[0])

    if sl is None and entry is not None and tp is not None:
        if action == "buy":
            sl = entry - (tp - entry)
        elif action == "sell":
            sl = entry + (entry - tp)

    return symbol_list, action, tp, sl


def parse(message: str, base: str, img_path) -> Tuple[List[str], str]:
    tp, sl = None, None
    if config["telegram_setting"]["signal"] == "Rose":
        message = message.lower()
        message = parse_symbol_substitute(message)
        symbol_list = parse_symbol(message, img_path)
        action = parse_action(message)
    elif config["telegram_setting"]["signal"] == "Perpetual":
        symbol_list = re.findall('#[^\s]+', message)
        symbol_list = [i.replace('#', '') for i in symbol_list]
        action = None
        if "看漲" in message:
            action = "buy"
        elif "看跌" in message:
            action = "sell"
    elif config["telegram_setting"]["signal"] == "Sentiment":
        message = re.compile('[^a-zA-Z\n ]').sub('', message)
        symbol_list = message.split(' ')[:1]
        action = None
        if "Overheated" in message or "FOMO" in message:
            action = "sell"
        elif "Fear" in message:
            action = "buy"
    elif config["telegram_setting"]["signal"] == "Justin":
        symbol_list, action = parse_justin(message)
    elif config["telegram_setting"]["signal"] == "Daily":
        symbol_list, action, tp, sl = parse_daily(message)
    return symbol_list, action, tp, sl
