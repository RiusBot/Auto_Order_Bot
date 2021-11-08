import re
import time
import ccxt
import json
import logging
from typing import List, Dict, Tuple
from collections import defaultdict

from src.exchange.parse import parse
from src.config import config


class FTXClient():

    def __init__(self, config: dict):
        self.config = config
        self.test_only = config["order_setting"]["test_only"]
        self.target = config["order_setting"]["target"]
        self.order_type = "Limit" if config["order_setting"]["limit"] is True else "Market"
        self.hold = config["order_setting"]["hold"]
        self.quantity = config["order_setting"]["quantity"]
        self.leverage = config["order_setting"]["leverage"]
        self.sl = config["order_setting"]["stop_loss"]
        self.tp = config["order_setting"]["take_profit"]
        self.margin = config["order_setting"]["margin_level_ratio"]
        self.subaccount = config["exchange_setting"]["subaccount"]
        self.no_duplicate = config["order_setting"]["no_duplicate"]

        options = {
            "defaultType": self.target.lower(),
            "adjustForTimeDifference": True,
            "verbose": True
        }
        headers = {}

        if self.subaccount:
            headers = {
                'FTX-SUBACCOUNT': self.subaccount
            }

        logging.info(f"headers: {headers}")
        self.exchange = getattr(ccxt, config["exchange_setting"]["exchange"])({
            "enableRateLimit": True,
            "apiKey": config["exchange_setting"]["api_key"],
            "secret": config["exchange_setting"]["api_secret"],
            'options': options,
            'headers': headers,
        })

        try:
            self.exchange.check_required_credentials()
        except Exception as e:
            logging.info(f"Authenticate Requirements: {json.dumps(self.exchange.requiredCredentials, indent=4)}")
            raise e

        self.markets = self.exchange.loadMarkets(True)
        logging.debug(self.markets)

    def parse(self, message: str, img_path: str) -> Tuple[List[str], str]:
        base = "-PERP" if self.target == "FUTURE" else "/USD"
        symbol_list, action = parse(message, base, img_path)

        # clean
        symbol_list = [i.replace("#", "").upper() for i in symbol_list]
        symbol_list = [f"{i}{base}" for i in symbol_list]
        symbol_list = [i for i in symbol_list if self.validate_symbol(i)]
        symbol_list = list(set(symbol_list))

        logging.info(f"Symbols: {symbol_list}")
        logging.info(f"Action: {action}")
        return symbol_list, action

    def get_volume(self, symbol: str) -> float:
        try:
            self.exchange.loadMarkets(True)
            symbol = symbol.replace("USDT", "USD")
            market = self.exchange.markets[symbol]
            info = market["info"]
            return float(info["volumeUsd24h"])
        except Exception:
            logging.excpetion("")
            logging.error("get volume failed")

    def get_price(self, symbol: str) -> float:
        self.exchange.loadMarkets(True)
        symbol = symbol.replace("USDT", "USD")
        return float(self.exchange.fetchTicker(symbol)['bid'])

    def get_balance(self):
        balance = 0
        info = self.exchange.fetch_balance()["info"]
        for coin in info["reuslt"]:
            if coin['coin'] == "USD":
                balance = coin["availableWithoutBorrow"]
        return float(balance)

    def get_margin(self, symbol: str) -> float:
        self.exchange.loadMarkets(True)
        margin = self.exchange.private_get_account()["result"]["marginFraction"]
        return 999 if margin is None else float(margin)

    def create_market_buy(self, symbol: str):
        price = self.get_price(symbol)
        amount = self.quantity / price * self.leverage
        logging.info(f"""
            Market Buy {symbol}
            Open price : {price}
            Amount : {amount}
        """)
        order = self.exchange.createMarketBuyOrder(symbol, amount)
        logging.info(f"Open average price : {order['average']}")
        return order

    def create_limit_buy(self, symbol: str):
        price = self.get_price(symbol)
        amount = self.quantity / price * self.leverage
        logging.info(f"""
            Limit Buy {symbol}
            Open price : {price}
            Amount : {amount}
        """)
        order = self.exchange.createLimitBuyOrder(symbol, amount, price)
        order["average"] = order.get("price", price)
        return order

    def create_market_sell(self, symbol: str):
        price = self.get_price(symbol)
        amount = self.quantity / price * self.leverage
        logging.info(f"""
            Market Sell {symbol}
            Open price : {price}
            Amount : {amount}
        """)
        order = self.exchange.createMarketSellOrder(symbol, amount)
        logging.info(f"Sell average price : {order['average']}")
        return order

    def create_limit_sell(self, symbol: str):
        price = self.get_price(symbol)
        amount = self.quantity / price * self.leverage
        order = self.exchange.createLimitSellOrder(symbol, amount, price)
        order["average"] = order.get("price", price)
        logging.info(f"""
            Limit Sell {symbol}
            Open price : {order['average']}
            Amount : {amount}
        """)
        return order

    def create_oco_order(self, symbol: str, open_order: dict, take_profit: float, stop_loss: float):
        open_order = self.exchange.fetchOrder(open_order["id"])
        amount = float(open_order["amount"])
        price = float(open_order["average"]) if open_order.get("average") else float(open_order["price"])
        tp_price = price * (1 + self.tp)
        sl_price = price * (1 - self.sl)

        if config["other_setting"]["auto_sl_tp"] and take_profit is not None:
            tp_price = take_profit
        if config["other_setting"]["auto_sl_tp"] and stop_loss is not None:
            sl_price = stop_loss

        logging.info(f"Stop loss: {sl_price} , Take profit : {tp_price}")
        tp_order = None
        sl_order = None

        try:
            params = {
                "market": symbol,
                "side": "sell",
                "triggerPrice": tp_price,
                "size": amount,
                "type": "takeProfit",
                "reduceOnly": True
            }
            if config["order_setting"]["tp_limit"]:
                params["orderPrice"] = tp_price

            tp_order = self.exchange.private_post_conditional_orders(
                params=params
            )
        except Exception as e:
            logging.error(str(e))
            if "-2021" in e.args[0]:
                sell_order = self.exchange.createMarketSellOrder(symbol, amount)
                logging.info("Sell immediately.")
                return None, None, sell_order

        try:
            params = {
                "market": symbol,
                "side": "sell",
                "triggerPrice": sl_price,
                "size": amount,
                "type": "stop",
                "reduceOnly": True
            }
            if config["order_setting"]["sl_limit"]:
                params["orderPrice"] = sl_price
            sl_order = self.exchange.private_post_conditional_orders(
                params=params
            )
        except Exception as e:
            logging.error(str(e))
            if "-2021" in e.args[0]:
                sell_order = self.exchange.createMarketSellOrder(symbol, amount)
                logging.info("Sell immediately.")
                return None, None, sell_order

        return tp_order, sl_order, None

    def create_oco_short_order(self, symbol: str, open_order: dict, take_profit: float, stop_loss: float):
        open_order = self.exchange.fetchOrder(open_order["id"])
        amount = float(open_order["amount"])
        price = float(open_order["average"]) if open_order.get("average") else float(open_order["price"])
        tp_price = price * (1 - self.tp)
        sl_price = price * (1 + self.sl)

        if config["other_setting"]["auto_sl_tp"] and take_profit is not None:
            tp_price = take_profit
        if config["other_setting"]["auto_sl_tp"] and stop_loss is not None:
            sl_price = stop_loss

        logging.info(f"Stop loss: {sl_price} , Take profit : {tp_price}")
        tp_order = None
        sl_order = None

        try:
            tp_order = self.exchange.private_post_conditional_orders(
                params={
                    "market": symbol,
                    "side": "buy",
                    "triggerPrice": tp_price,
                    "size": amount,
                    "type": "takeProfit",
                    "reduceOnly": True
                }
            )
        except Exception as e:
            logging.info(str(e))
            if "-2021" in e.args[0]:
                sell_order = self.exchange.createMarketBuyOrder(symbol, amount)
                logging.info("Buy immediately.")
                return None, None, sell_order

        try:
            sl_order = self.exchange.private_post_conditional_orders(
                params={
                    "market": symbol,
                    "side": "buy",
                    "triggerPrice": sl_price,
                    "size": amount,
                    "type": "stop",
                    "reduceOnly": True
                }
            )
        except Exception as e:
            logging.info(str(e))
            if "-2021" in e.args[0]:
                sell_order = self.exchange.createMarketBuyOrder(symbol, amount)
                logging.info("Buy immediately.")
                return None, None, sell_order

        return tp_order, sl_order, None

    def process_oco_order(self, oco_order):
        tp_order = None
        sl_order = None
        for order in oco_order["orderReports"]:
            if order["type"] == "STOP_LOSS_LIMIT":
                sl_order = order
            else:
                tp_order = order
        return tp_order, sl_order

    def check_orders(self, open_order, tp_order, sl_order):
        tp_order_info = self.exchange.fetchOrder(tp_order["id"], tp_order["symbol"])
        sl_order_info = self.exchange.fetchOrder(sl_order["id"], sl_order["symbol"])
        final_order = None

        if tp_order_info["status"] == "open":
            self.exchange.cancelOrder(tp_order["id"], tp_order["symbol"])
        elif tp_order_info["status"] == "closed":
            final_order = tp_order_info

        if sl_order_info["status"] == "open":
            self.exchange.cancelOrder(sl_order["id"], sl_order["symbol"])
        elif sl_order_info["status"] == "closed":
            final_order = sl_order_info

        if final_order is None:
            symbol, amount = open_order["symbol"], open_order["amount"]
            final_order = self.exchange.createMarketSellOrder(symbol, amount)

        logging.info(f"Close at price : {final_order['average']}")
        return final_order

    def clean_up(self, open_order, close_order, msg: str):
        amount = float(close_order["amount"])
        open_average = float(open_order["average"])
        close_average = float(close_order["average"])
        profit = (close_average - open_average) * amount
        percent = (close_order / open_average) - 1
        result = {
            "open_price": open_average,
            "close_price": close_average,
            "amount": amount,
            "profit": profit,
            "percent": percent,
            "balance": self.get_balance(),
            "message": msg
        }
        return result

    def validate_symbol(self, symbol: str):
        self.markets = self.exchange.loadMarkets(True)
        valid = symbol in self.markets
        logging.info(f"{symbol} valid: {valid}")
        return valid

    def risk_control(self, margin: float):
        logging.info(f"Current margin: {margin}, minimum margin: {self.margin}.")
        if margin < self.margin:
            logging.info("violtate margin risk !! Give up.")
            return False
        logging.info("Margin check valid.")
        return True

    def check_duplicate_and_giveup(self, symbol: str):
        if self.no_duplicate:
            if self.target == "SPOT" or self.target == "MARGIN":
                logging.info("check spot duplicate")
                token = symbol.split('/')[0]
                asset = self.exchange.fetch_balance()["total"]
                amount = float(asset.get(token, 0))
                price = self.get_price(symbol)
                notional = amount * price
                return True if notional > 1 else False
            elif self.target == "FUTURE":
                logging.info("check future duplicate")
                positions = self.exchange.fetchPositions()
                for position in positions:
                    if "symbol" in position:
                        position = position.get("info", {})

                    if position.get('future') == symbol and position.get('entryPrice') and position.get('side'):
                        side = position['side']
                        logging.info(f"{symbol} has {side} position.")
                        return side

            logging.info(f"{symbol} No duplicate positions")
        return False

    def giveup_order(self, symbol: str, action: str):

        side = self.check_duplicate_and_giveup(symbol)
        if side and side == action:
            logging.info(f"{symbol} position already exists. No order made.")
            return True

        if self.target != "SPOT":
            margin = self.get_margin(symbol)
            if not self.risk_control(margin):
                return True

        if self.test_only:
            logging.info("Test only. No order made.")
            return True

        if action == "sell" and self.target != "FUTURE":
            logging.info("Sell order only for future")
            return True

        if config["order_setting"]["minimum_volume"]:
            volume = self.get_volume(symbol)
            if volume is not None:
                if config["order_setting"]["minimum_volume"] > volume:
                    return True

        return False

    def run(self, symbol_list: str, action: str, take_profit: float, stop_loss: float):

        logging.info("Start making order.")
        orders_list = []
        result_list = []
        margin = None

        for symbol in symbol_list:

            if self.giveup_order(symbol, action):
                logging.info("give up order.")
                continue

            open_order = None
            tp_order = None
            sl_order = None

            if action == "buy":
                if self.order_type == "Limit":
                    open_order = self.create_limit_buy(symbol)
                elif self.order_type == "Market":
                    open_order = self.create_market_buy(symbol)
            elif action == "sell":
                if self.order_type == "Limit":
                    open_order = self.create_limit_sell(symbol)
                elif self.order_type == "Market":
                    open_order = self.create_market_sell(symbol)

            if open_order and self.sl != 0 and self.tp != 0:

                if action == "buy":
                    tp_order, sl_order, sell_order = self.create_oco_order(symbol, open_order, take_profit, stop_loss)
                elif action == "sell":
                    tp_order, sl_order, sell_order = self.create_oco_short_order(symbol, open_order, take_profit, stop_loss)

                if sell_order is not None:
                    result = self.clean_up(open_order, sell_order, msg="oco failed")
                    open_order = None
                    result_list.append(result)

            if open_order:
                orders_list.append("buy order placed.")
            if tp_order:
                orders_list.append("take profit order placed.")
            if sl_order:
                orders_list.append("stop loss order placed.")

        return orders_list, result_list, margin
