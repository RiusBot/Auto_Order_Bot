import re
import time
import ccxt
import json
import logging
from typing import List, Dict, Tuple
from collections import defaultdict

from src.exchange.parse import parse
from src.config import config


class BinanceClient():

    def __init__(self, config: dict):
        self.config = config
        self.test_only = config["order_setting"]["test_only"]
        self.target = config["order_setting"]["target"]
        self.order_type = "Limit" if config["order_setting"]["limit"] is True else "Market"
        self.hold = config["order_setting"]["hold"]
        self.quantity = float(config["order_setting"]["quantity"])
        self.leverage = float(config["order_setting"]["leverage"])
        self.sl = float(config["order_setting"]["stop_loss"])
        self.tp = float(config["order_setting"]["take_profit"])
        self.margin = float(config["order_setting"]["margin_level_ratio"])
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

            }

        self.exchange = getattr(ccxt, config["exchange_setting"]["exchange"])({
            "enableRateLimit": True,
            "apiKey": config["exchange_setting"]["api_key"],
            "secret": config["exchange_setting"]["api_secret"],
            'options': options,
            'headers': headers
        })

        try:
            self.exchange.check_required_credentials()
        except Exception as e:
            logging.info(f"Authenticate Requirements: {json.dumps(self.exchange.requiredCredentials, indent=4)}")
            raise e

        self.markets = self.exchange.loadMarkets(True)
        logging.debug(self.markets)

    def parse(self, message: str, img_path: str) -> Tuple[List[str], str]:
        base = "/USDT"
        symbol_list, action = parse(message, base, img_path)

        # clean
        symbol_list = [i.replace("#", "").upper() for i in symbol_list]
        symbol_list = [f"{i}{base}" for i in symbol_list]
        symbol_list = [i for i in symbol_list if self.validate_symbol(i)]
        symbol_list = list(set(symbol_list))

        logging.debug(f"Symbols: {symbol_list}")
        logging.debug(f"Action: {action}")
        return symbol_list, action

    def get_volume(self, symbol: str) -> float:
        try:
            return float(self.exchange.fapiPublic_get_ticker_24hr({'symbol': symbol})["volume"])
        except Exception:
            logging.excpetion("")
            logging.error("get volume failed")

    def get_price(self, symbol: str) -> float:
        self.exchange.loadMarkets(True)
        return float(self.exchange.fetchTicker(symbol)['info']["lastPrice"])

    def get_balance(self):
        balance = 0
        if self.target == "SPOT":
            assets = self.exchange.fetch_balance()["info"]["balances"]
            for asset in assets:
                if asset["asset"] == "USDT":
                    balance = asset["free"]
        elif self.target == "MARGIN":
            assets = self.exchange.fetch_balance()["info"]["userAssets"]
            for asset in assets:
                if asset["asset"] == "USDT":
                    balance = asset["free"]
        elif self.target == "FUTURE":
            balance = self.exchange.fetch_balance()["info"]['availableBalance']
        logging.info(f"Balance remain: {balance}")
        return float(balance)

    def get_margin(self, symbol: str) -> float:
        self.exchange.loadMarkets(True)
        margin = None
        if self.target == "SPOT":
            margin = 999
        elif self.target == "MARGIN":
            info = self.exchange.fetch_balance()["info"]
            margin = 999 if info["marginLevel"] is None else float(info["marginLevel"])
        elif self.target == "FUTURE":
            info = self.exchange.fetch_balance()
            maintenance_margin = float(info["info"]["totalMaintMargin"])
            margin_balance = float(info["info"]["totalMarginBalance"])
            if margin_balance == 0:
                marginRatio = 0
            else:
                marginRatio = maintenance_margin / margin_balance
            margin = marginRatio

        logging.info(f"Margin level/ratio: {margin}")
        return margin

    def create_market_buy(self, symbol: str):
        price = self.get_price(symbol)
        amount = self.quantity / price * self.leverage
        logging.info(f"""
            Market Buy {symbol}
            price : {price}
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
            Amount : {amount}
            Price: {price}
        """)
        order = self.exchange.createMarketSellOrder(symbol, amount)
        logging.info(f"Sell average price : {order['average']}")
        return order

    def create_limit_sell(self, symbol: str):
        price = self.get_price(symbol)
        amount = self.quantity / price * self.leverage
        logging.info(f"""
            Limit Sell {symbol}
            Open price : {price}
            Amount : {amount}
        """)
        order = self.exchange.createLimitSellOrder(symbol, amount, price)
        order["average"] = order.get("price", price)
        return order

    def create_oco_order(self, symbol: str, open_order: dict, take_profit: float, stop_loss: float):
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

        if self.target == "FUTURE":
            tp_order_type = "TAKE_PROFIT" if config["order_setting"]["tp_limit"] else "TAKE_PROFIT_MARKET"
            sl_order_type = "STOP" if config["order_setting"]["sl_limit"] else "STOP_MARKET"

            try:
                tp_order = self.exchange.create_order(
                    symbol,
                    type=tp_order_type,
                    side="SELL",
                    amount=amount,
                    params={
                        "stopPrice": tp_price,
                        "closePosition": True,
                        "priceProtect": True
                    }
                )
            except Exception as e:
                logging.error(str(e))
                if "-2021" in e.args[0]:
                    sell_order = self.exchange.createMarketSellOrder(symbol, amount)
                    logging.info("Sell immediately.")
                    return None, None, sell_order

            try:
                sl_order = self.exchange.create_order(
                    symbol,
                    type=sl_order_type,
                    side="SELL",
                    amount=amount,
                    params={
                        "stopPrice": sl_price,
                        "closePosition": True,
                        "priceProtect": True
                    }
                )
            except Exception as e:
                logging.error(str(e))
                if "-2021" in e.args[0]:
                    sell_order = self.exchange.createMarketSellOrder(symbol, amount)
                    logging.info("Sell immediately.")
                    return None, None, sell_order

        elif self.target == "SPOT":
            tp_order_type = "TAKE_PROFIT_LIMIT" if config["order_setting"]["tp_limit"] else "TAKE_PROFIT"
            sl_order_type = "STOP_LOSS_LIMIT" if config["order_setting"]["sl_limit"] else "STOP_LOSS"

            try:
                oco_order = self.exchange.private_post_order_oco({
                    "symbol": symbol.replace("/", ""),
                    "side": "SELL",
                    "quantity": amount,
                    "price": tp_price,
                    "stopPrice": sl_price,
                    "StopLimitPrice": sl_price,
                    "stopLimitTimeInForce": "GTC"
                })
                tp_order, sl_order = self.process_oco_order(oco_order)

            except Exception as e:
                logging.info(str(e))
                if "-2021" in e.args[0]:
                    sell_order = self.exchange.createMarketSellOrder(symbol, amount)
                    logging.info("Sell immediately.")
                    return None, None, sell_order
        elif self.target == "MARGIN":
            try:
                oco_order = self.exchange.sapi_post_margin_order_oco({
                    "symbol": symbol,
                    "side": "SELL",
                    "quantity": amount,
                    "price": tp_price,
                    "stopPrice": sl_price,
                    "StopLimitPrice": sl_price,
                    "stopLimitTimeInForce": "GTC"
                })
                tp_order, sl_order = self.process_oco_order(oco_order)

            except Exception as e:
                logging.info(str(e))
                if "-2021" in e.args[0]:
                    sell_order = self.exchange.createMarketSellOrder(symbol, amount)
                    logging.info("Sell immediately.")
                    return None, None, sell_order

        return tp_order, sl_order, None

    def create_oco_short_order(self, symbol: str, open_order: dict, take_profit: float, stop_loss: float):
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

        if self.target == "FUTURE":
            try:
                tp_order = self.exchange.create_order(
                    symbol,
                    type="TAKE_PROFIT_MARKET",
                    side="BUY",
                    amount=amount,
                    params={
                        "stopPrice": tp_price,
                        "closePosition": True,
                        "priceProtect": True
                    }
                )
            except Exception as e:
                logging.info(str(e))
                if "-2021" in e.args[0]:
                    sell_order = self.exchange.createMarketBuyOrder(symbol, amount)
                    logging.info("Buy immediately.")
                    return None, None, sell_order

            try:
                sl_order = self.exchange.create_order(
                    symbol,
                    type="STOP_MARKET",
                    side="BUY",
                    amount=amount,
                    params={
                        "stopPrice": sl_price,
                        "closePosition": True,
                        "priceProtect": True
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
        return symbol in self.markets

    def risk_control(self, margin: float):
        logging.info(f"Current margin: {margin}, minimum margin: {self.margin}.")
        if self.target == "FUTURE":
            if margin > self.margin:
                logging.info("violtate margin risk !! Give up.")
                return False
        elif self.target == "MARGIN":
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
                    if position.get('symbol') == symbol:
                        side = position.get('side')
                        logging.info(f"{symbol} has {side} position.")
                        if side == "long":
                            return "buy"
                        elif side == "short":
                            return "sell"
                        else:
                            return side

            logging.info(f"{symbol} no duplicate positions.")
        return False

    def giveup_order(self, symbol: str, action: str):
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

        side = self.check_duplicate_and_giveup(symbol)
        if side and side.lower() == action:
            logging.info(f"{symbol} position already exists. No order made.")
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
                orders_list.append("order placed.")
            if tp_order:
                orders_list.append("take profit order placed.")
            if sl_order:
                orders_list.append("stop loss order placed.")

        return orders_list, result_list, margin
