import re
import time
import ccxt
import json
import logging
from typing import List, Dict, Tuple
from collections import defaultdict

from parse import parse



class OKEXClient():

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
        self.exchange = getattr(ccxt, config["exchange_setting"]["exchange"])({
            "enableRateLimit": True,
            "apiKey": config["exchange_setting"]["api_key"],
            "secret": config["exchange_setting"]["api_secret"],
                "password":config["exchange_setting"]["password"],

            'options': {
                "defaultType": self.target.lower(),
                "adjustForTimeDifference": True,
                "verbose": True,
                'brokerId': 'a8a0f2138d1bBCDE'
            }
        })

        try:
            self.exchange.check_required_credentials()
        except Exception as e:
            logging.info(f"Authenticate Requirements: {json.dumps(self.exchange.requiredCredentials, indent=4)}")
            raise e

        self.markets = self.exchange.loadMarkets(True)
        logging.debug(self.markets)

    def parse(self, message: str) -> Tuple[List[str], str]:
        base = "/USDT"
        symbol_list, action = parse(message, base)

        # clean
        symbol_list = [i.replace("#", "").upper() for i in symbol_list]
        symbol_list = [f"{i}{base}" for i in symbol_list]
        symbol_list = [i for i in symbol_list if self.validate_symbol(i)]
        symbol_list = list(set(symbol_list))

        logging.debug(f"Symbols: {symbol_list}")
        logging.debug(f"Action: {action}")
        return symbol_list, action

    def get_price(self, symbol: str) -> float:
        self.exchange.loadMarkets(True)
        return self.exchange.fetchTicker(symbol)['bid']

    def get_balance(self):
        balance = None
        if self.target == "SPOT":
            assets = self.exchange.fetch_balance()["info"]["balances"]
            for asset in assets:
                if asset["asset"] == "USDT":
                    balance = asset["free"]
        elif self.target == "MARGIN":
           for item in self.exchange.fetch_balance()['info']['data']:
                for it in item['details']:
                    if it['ccy'] == "USDT":
                        balance = it['availEq']
        elif self.target == "FUTURE":
            balance = self.exchange.fetch_balance()["info"]['avaiableBalance']
        logging.info(f"Balance remain: {balance}")
        return balance

    def get_margin(self, symbol: str) -> float:
        self.exchange.loadMarkets(True)
        margin = None
        if self.target == "SPOT":
            margin = None
        elif self.target == "MARGIN":
            margin = float(self.exchange.fetch_balance()['info']['data'][0]['details'][0]['mgnRatio'])
        elif self.target == "FUTURE":
            info = self.exchange.fetch_positions()
            maintenance_margin = 0
            for i in info:
                maintenance_margin += i["maintenanceMargin"]
            marginRatio = maintenance_margin / i["collateral"]
            margin = marginRatio

        logging.info(f"Margin level/ratio: {margin}")
        return margin

    def create_market_buy(self, symbol: str):
        price = self.get_price(symbol)
        amount = self.quantity / price * self.leverage
        if self.target == 'MARGIN':
            params={ 
                        'tdMode':'cross' ,
                    'posSide':'long',
                    "ordType":"market",
                'lever': f'{self.leverage}',
                "instType":'SWAP',
                }
        else:
            params={ 
                        'ccy' :"USDT",
                        'px':f'{amount}'
            }
        print(amount)
        order = self.exchange.createMarketBuyOrder(symbol, amount, params = params)
        logging.info(f"""
            Market Buy {symbol}
            Open price : {order['average']}
            Amount : {amount}
        """)
        return order
    
    def create_limit_buy(self, symbol: str):
        price = self.get_price(symbol)
        amount = self.quantity / price * self.leverage
        if self.target == 'MARGIN':
            params={ 
                        'tdMode':'cross' ,
                    'posSide':'long',
                    "ordType":"limit",
                'lever': f'{self.leverage}',
                "instType":'SWAP',
                }
        else:
            params={ 
                    'ccy' :"USDT",
                    "ordType":"limit",
                }
        order = self.exchange.createLimitBuyOrder(symbol, amount, price,params = params)
        order["average"] = order.get("price", price)
        logging.info(f"""
            Market Buy {symbol}
            Open price : {order['average']}
            Amount : {amount}
        """)
        return order
#     def create_market_sell(self, symbol: str):
#             price = self.get_price(symbol)
#             amount = self.quantity / price * self.leverage
#             if self.target == 'margin':
#                 params={ 
#                             'tdMode':'cross' ,
#                         'posSide':'short',
#                         "ordType":"limit",
#                     'lever': f'{self.leverage}',
#                     "instType":'SWAP',
#                     }
#             else:
#                 params={ 
#                             'tdMode':'cross' ,
#                         'ccy' :"USDT",
#                         "ordType":"limit",
#                     }
#             order = self.exchange.createMarketSellOrder(symbol, amount, params = params)
#             logging.info(f"""
#                 Market Buy {symbol}
#                 Open price : {order['average']}
#                 Amount : {amount}
#             """)
#             return order
        
     
#     def create_limit_sell(self, symbol: str):
#         price = self.get_price(symbol)
#         amount = self.quantity / price * self.leverage
#         if self.target == 'MARGIN':
#             params={ 
#                         'tdMode':'cross' ,
#                     'posSide':'short',
#                     "ordType":"limit",
#                 'lever': f'{self.leverage}',
#                 "instType":'SWAP',
#                 }
#         else:
#             params={ 
#                     'tdMode':'cross' ,
#                     'ccy' :"USDT",
#                     "ordType":"limit",
#                 }
#         order = self.exchange.create_limit_sell(symbol, amount, price,params = params)
#         order["average"] = order.get("price", price)
#         logging.info(f"""
#             Market Buy {symbol}
#             Open price : {order['average']}
#             Amount : {amount}
#         """)
#         return order    


    def create_oco_order(self, symbol: str, open_order):
        amount = float(open_order["amount"])
        price = float(open_order["average"])
        tp_price = price * (1 + self.tp)
        sl_price = price * (1 - self.sl)
        logging.info(f"Stop loss: {sl_price} , Take profit : {tp_price}")

        if self.target == "FUTURE":
            try:
                tp_order = self.exchange.create_order(
                    symbol,
                    type="TAKE_PROFIT_MARKET",
                    side="SELL",
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
                    sell_order = self.exchange.createMarketSellOrder(symbol, amount)
                    logging.info("Sell immediately.")
                    return None, None, sell_order

            try:
                sl_order = self.exchange.create_order(
                    symbol,
                    type="STOP_MARKET",
                    side="SELL",
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
                    sell_order = self.exchange.createMarketSellOrder(symbol, amount)
                    logging.info("Sell immediately.")
                    return None, None, sell_order

        elif self.target == "SPOT":
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

    def run(self, symbol_list: str):

        logging.info("Start making order.")
        orders_list = []
        result_list = []
        margin = None
       
            
        for symbol in symbol_list:
            if symbol[-4:] == 'SWAP':
                self.target  = 'MARGIN'
            else:
                self.target  = 'SPOT'

            if self.target != "SPOT":
                margin = self.get_margin(symbol)
                if not self.risk_control(margin):
                    continue

            if self.test_only:
                logging.info("Test only. No order made.")
                continue

            if self.order_type == "Limit":
                open_order = self.create_limit_buy(symbol)
            elif self.order_type == "Market":
                open_order = self.create_market_buy(symbol)

            tp_order = None
            sl_order = None
            if self.sl != 0 and self.tp != 0:
                tp_order, sl_order, sell_order = self.create_oco_order(symbol, open_order)
                if sell_order is not None:
                    result = self.clean_up(open_order, sell_order, msg="oco failed")
                    open_order = None
                    result_list.append(result)

            orders_list.append((open_order, tp_order, sl_order))

        return orders_list, result_list, margin
