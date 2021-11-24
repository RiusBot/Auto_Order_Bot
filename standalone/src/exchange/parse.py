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


def parse(message: str, base: str) -> Tuple[List[str], str]:
    message = message.lower()
    message = parse_symbol_substitute(message)
    symbol_list = parse_symbol(message)
    action = parse_action(message) if symbol_list else None
    return symbol_list, action
