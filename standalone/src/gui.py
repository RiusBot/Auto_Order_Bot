import ccxt
import traceback
import logging
import threading
import PySimpleGUI as sg
from telethon import TelegramClient
from src.config import config, save_config, type_casting
from src.telegram_bot import telegram_start, get_all_dialogs


def telegram_setting_layout():
    layout = sg.Frame(
        "Telegram Setting",
        [
            # [sg.Combo(["Perpetual Data", "Rose Premium"])],
            [
                sg.Radio("Perpetual", "telegram signal", key="P_signal"),
                sg.Radio("Rose Premium", "telegram signal", key="R_signal"),
                sg.Radio("Sentiment", "telegram signal", key="S_signal"),
                sg.Radio("Justin", "telegram signal", key="J_signal"),
                sg.Radio("Scalp", "telegram signal", key="D_signal")
            ],

            [
                sg.Column(
                    [

                        [sg.Text("Telegram ID"), sg.In(key="telegram_api_id")],
                        [sg.Text("Telegram Hash"), sg.In(key="telegram_api_hash")],
                        [sg.Text("Session name"), sg.In(key="session")],
                        [sg.Text("Signal channel"), sg.In(key="signal_channel")],
                        # , sg.Button("Browse", key="all_dialog1")
                        [sg.Text("Nofify channel"), sg.In(key="notify_channel")],
                        # , sg.Button("Browse", key="all_dialog2")
                        [sg.Text("Testing channel"), sg.In(key="test_channel")],
                        # , sg.Button("Browse", key="all_dialog3")
                        [sg.Button("Login", key="login")]
                    ],
                    element_justification="right"
                )
            ]
        ],
        element_justification="center"
    )
    return layout


def exchange_setting_layout():
    layout = sg.Frame(
        "Exchange Setting",
        [
            [
                sg.Column(
                    [
                        [sg.Text("Exchange"), sg.Combo(ccxt.exchanges, size=14, key="exchange"), sg.Text("Subaccount"),
                         sg.In(size=14, key="subaccount")],
                        [sg.Text("API Key"), sg.In(size=44, key="api_key")],
                        [sg.Text("API Secret"), sg.In(size=44, key="api_secret")]
                    ],
                    element_justification="right"
                ),

            ]
        ],
        element_justification="center"
    )
    return layout


def order_setting_layout():
    layout = sg.Frame(
        "Order setting",
        [
            [
                sg.Column(
                    [
                        [sg.Text("Target"), sg.Combo(["SPOT", "MARGIN", "FUTURE"], size=15, key="target")],
                        [sg.Checkbox('Test only', default=True, key="test_only")],
                        [sg.Checkbox('No duplicate order', default=True, key="no_duplicate")],
                        [sg.Checkbox('Make short order', default=True, key="make_short")],
                        [sg.Radio('Limit', "order_type", key="limit"), sg.Radio("Market", "order_type", key="market")]
                    ],
                    element_justification="left"
                ),
                sg.Column(
                    [
                        [sg.Text("Quantity"), sg.In(size=15, key="quantity")],
                        [sg.Text("Leverage"), sg.In(size=15, key="leverage")],
                        [sg.Text("Minimum margin level/ratio"), sg.In(size=15, key="margin_level_ratio")],
                        [sg.Text("Perpetual minimum 24 volume"), sg.In(size=15, key="minimum_volume")],
                    ],
                    element_justification="right"
                ),
                sg.Column(
                    [
                        [sg.Text("Stop Loss "), sg.In(size=15, key="stop_loss"), sg.Text("")],
                        [sg.Text("Take Profit"), sg.In(size=15, key="take_profit"), sg.Text("")],
                        [sg.Text("Fibonacci  "), sg.In(size=15, key="fibonacci"), sg.Text("")],
                        [sg.Text("hold", visible=False), sg.In(size=15, key="hold", visible=False)],
                        [sg.Checkbox('SL limit', default=True, key="sl_limit"),
                         sg.Checkbox('TP limit', default=True, key="tp_limit")]
                    ],
                    element_justification="right"
                ),
            ],
        ],
        element_justification="center"
    )
    return layout


def new_order_setting_layout():
    layout = [[
        sg.Column(
            [
                [sg.Text("Target"), sg.Combo(["SPOT", "MARGIN", "FUTURE"], size=15, key="target")],
                [sg.Checkbox('Test only', default=True, key="test_only")],
                [sg.Checkbox('Limit only', default=False, key="limit_only")],
                [sg.Checkbox("Isolate only", default=False, disabled=True, key="isolate_only")],
            ],
            element_justification="left"
        ),
        sg.Column(
            [
                [sg.Text("Quantity"), sg.In(size=15, key="quantity")],
                [sg.Text("Leverage"), sg.In(size=15, key="leverage")],
            ],
            element_justification="right"
        ),
        sg.Column(
            [
                [sg.Text("Stop Loss"), sg.In(size=15, key="stop_loss"), sg.Text("%")],
                [sg.Text("Take Profit"), sg.In(size=15, key="take_profit"), sg.Text("%")],
                # [sg.Text("Trailing Stop"), sg.In(size=15, key="trailing_stop"), sg.Text("%")],
            ],
            element_justification="right"
        ),
        sg.Column(
            [
                [sg.Text("minimum margin level"), sg.In(size=15, key="minimum_margin_level")],
                [sg.Text("")]
            ],
            element_justification="right"
        ),
    ]]
    return layout


def save_setting_layout():
    layout = sg.Button("Save")
    # layout = sg.Frame(
    #     "Saving Setting",
    #     [[
    #         sg.Column(
    #             [
    #                 [sg.Text("Save Config"), sg.In(), sg.FileBrowse()],
    #                 [sg.Text("Load Config"), sg.In(), sg.FileBrowse()],
    #                 [sg.Text("Log Path"), sg.In(), sg.FileBrowse()],
    #             ],
    #             element_justification="right"
    #         ),
    #     ]],
    #     element_justification="center"
    # )
    return layout


def other_setting_layout():
    layout = sg.Frame(
        "Other setting",
        [[
            sg.Column(
                [
                    [sg.Checkbox('Rose For Bot', default=False, key="pro")],
                    [sg.Checkbox('Auto SL TP', default=False, key="auto_sl_tp")],
                    [sg.Text("Maximum latency"), sg.In(size=5, key="maximum_latency")],
                ],
                element_justification="left"
            ),
            sg.VerticalSeparator(pad=None),
            sg.Column(
                [
                    [sg.Text("Trigger keywords for Rose channel")],
                    [sg.Text("Long"), sg.In(size=22, key="long")],
                    [sg.Text("Short"), sg.In(size=22, key="short")],
                ],
                element_justification="right"
            ),
        ]],
        element_justification="center",
        visible=True
    )
    return layout


def Generate_encoded_message_layout():
    layout = sg.Frame(
        "Generate encoded message",
        [
            [
                sg.Column(
                    [
                        [sg.Text("symbol:"), sg.Input(key="symbol", size=(24, 5))],
                        [sg.Text("action:"), sg.Input(key="action", size=(24, 5))],
                        [sg.Button("Generate", key="generate")],
                        [sg.Text("encoded:"), sg.Input(key="gen_output", size=(24, 5))],
                    ],
                    element_justification="right"
                ),

            ]
        ],
        element_justification="right"
    )
    return layout


def Parsing_layout():
    layout = sg.Frame(
        "Parsing",
        [
            [
                sg.Column(
                    [
                        [sg.Text("Input\nmessage"), sg.Multiline(size=(24, 10), key="test_input")],
                        [sg.Text("Results"), sg.Multiline(size=(24, 3), key="test_output")],
                        [sg.Button("Parse", key="parse")],
                    ],
                    element_justification="right"
                )

            ]
        ],
        element_justification="right"
    )
    return layout


def Start_layout():
    layout = sg.Frame(
        "Run",
        [
            [
                sg.Column(
                    [
                        [sg.Button("Start")],
                        [sg.Multiline(size=(95, 30), key="log", reroute_stderr=True)]
                    ],
                    element_justification="center"
                ),

            ]
        ],
        element_justification="left",
    )
    return layout


def listing_layout():
    exchange = getattr(ccxt, config["exchange_setting"]["exchange"])()
    exchange.loadMarkets()
    return [
        [
            sg.Column([
                [sg.Text("All markets"), sg.In(key="search_target", size=(15, 5)), sg.Button("search", key="search")],
                [sg.Listbox(values=list(exchange.markets.keys()), size=(40, 20), key="markets")],
                [sg.Button("whitelist", key="white_add"), sg.Button("blacklist", key="black_add")]
            ]),
            sg.Column([
                [sg.Checkbox("Activate whitelist", key="whitelist_activate")],
                [sg.Listbox(values=config["listing_setting"]["whitelist"], size=(40, 20), key="whitelist")],
                [sg.Button("remove", key="white_rm")]
            ]),
            sg.Column([
                [sg.Checkbox("Activate blacklist", key="blacklist_activate")],
                [sg.Listbox(values=config["listing_setting"]["blacklist"], size=(40, 20), key="blacklist")],
                [sg.Button("remove", key="black_rm")]
            ])
        ],
        [sg.HorizontalSeparator(pad=None)],
        [save_setting_layout()]
    ]


def config_setup(window):
    try:
        # telegram setting
        for key, value in config["telegram_setting"].items():
            if key == "signal":
                if value == "Rose":
                    window["R_signal"].update(value=True)
                elif value == "Perpetual":
                    window["P_signal"].update(value=True)
                elif value == "Sentiment":
                    window["S_signal"].update(value=True)
                elif value == "Justin":
                    window["J_signal"].update(value=True)
                elif value == "Daily":
                    window["D_signal"].update(value=True)
            else:
                window[key].update(value=value)

        # exchange setting
        for key, value in config["exchange_setting"].items():
            window[key].update(value=value)

        # Order setting
        for key, value in config["order_setting"].items():
            window[key].update(value=value)

    except Exception:
        logging.exception("")
        sg.Popup(f"Config parsing error !!\n\n{traceback.format_exc()}")


def validate_config(config: dict):
    if (config["order_setting"]["stop_loss"] == 0) ^ (config["order_setting"]["take_profit"] == 0):
        raise Exception("Stop loss and Take profit has to be both zero or both set.")

    if not (config["order_setting"]["stop_loss"] >= 0 and config["order_setting"]["stop_loss"] <= 1):
        raise Exception("0 <= Stop loss <= 1.")

    if not (config["order_setting"]["take_profit"] >= 0 and config["order_setting"]["take_profit"] <= 1):
        raise Exception("0 <= Take profit <= 1.")
    #
    # if not (config["order_setting"]["trailing_stop"] >= 0 and config["order_setting"]["trailing_stop"] <= 1):
    #     raise Exception("0 <= Trailing stop <= 1.")


def update_config(window):
    try:
        validate_config(config)

        # telegram setting
        for key in config["telegram_setting"]:
            if key == "signal":
                if window["R_signal"]:
                    config["telegram_setting"]["signal"] = "Rose"
                elif window["P_signal"] is True:
                    config["telegram_setting"]["signal"] = "Perpetual"
                elif window["S_signal"].get() is True:
                    config["telegram_setting"]["signal"] = "Sentiment"
                elif window["J_signal"].get() is True:
                    config["telegram_setting"]["signal"] = "Justin"
                elif window["D_signal"].get() is True:
                    config["telegram_setting"]["signal"] = "Daily"
            elif key == "signal_channel":
                continue
            else:
                config["telegram_setting"][key] = window[key].get()

        # exchange setting
        config["exchange_setting"]["exchange"] = window["exchange"].get()
        config["exchange_setting"]["api_key"] = window["api_key"].get()
        config["exchange_setting"]["api_secret"] = window["api_secret"].get()

        # order setting
        for key in config["order_setting"]:
            config["order_setting"][key] = window[key].get()

        type_casting(config)
        save_config(config)
        sg.Popup(f"Update complete !!")
    except Exception:
        logging.exception("")
        sg.Popup(f"Update config failed !!\n\n{traceback.format_exc()}")


def telegram_login():
    telegram_client = TelegramClient(
        'anon',
        config["telegram_setting"]["telegram_api_id"],
        config["telegram_setting"]["telegram_api_hash"],
    )
    telegram_client.start(
        phone=lambda: sg.popup_get_text("Please enter your phone"),
        code_callback=lambda: sg.popup_get_text("Please enter the code you recieved"),
    )
    telegram_client.disconnect()


def run_gui():
    sg.theme('DarkAmber')
    setting_tab = [
        [
            telegram_setting_layout(),
            sg.VerticalSeparator(pad=None),
            sg.Column([[exchange_setting_layout()],
                       [other_setting_layout()]])
        ],
        [order_setting_layout()],
        [save_setting_layout()],
    ]
    main_tab = [
        [
            Start_layout(),
            sg.Frame(
                "Test",
                [
                    [
                        sg.Column(
                            [
                                [Generate_encoded_message_layout()],
                                [Parsing_layout()]
                            ],
                            element_justification="center"
                        )
                    ]
                ]
            )
        ],
    ]
    listing_tab = listing_layout()
    layout = [
        [sg.TabGroup(
            [[
                sg.Tab("Setting", setting_tab, element_justification="center"),
                sg.Tab("Run", main_tab, element_justification="center"),
                sg.Tab("Listing", listing_tab, element_justification="center")
            ]]
        )]
    ]

    window = sg.Window("Auto Order Bot", layout, finalize=True)
    config_setup(window)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Exit"):
            break
        if event == "login":
            telegram_login()
            sg.Popup("Login Success.")
        if event == "Save":
            update_config(window)
        if event == "Save0":
            try:
                whitelist = window["whitelist"].get_list_values()
                blacklist = window["blacklist"].get_list_values()
                config["listing_setting"]["whitelist"] = whitelist
                config["listing_setting"]["blacklist"] = blacklist
                save_lists(config)
                config["listing_setting"]["whitelist_activate"] = window["whitelist_activate"].get()
                config["listing_setting"]["blacklist_activate"] = window["blacklist_activate"].get()
                sg.popup("Listing Saved !!")
            except Exception:
                logging.exception("")
                sg.Popup(f"Save listing failed !!\n\n{traceback.format_exc()}")
        if event == "parse":
            test_input = window["test_input"].get()
            if config["other_setting"]["pro"]:
                symbol_list, action, tp, sl = parse_pro(test_input)
                test_output = f"symbol_list: {symbol_list}\naction: {action}\nstop loss: {sl}\ntake profit: {tp}"
            else:
                symbol_list, action, tp, sl = ExchangeClient(config).parse(test_input, None)
                test_output = f"symbol_list: {symbol_list}\naction: {action}\ntp: {tp}\nsl: {sl}"
            window["test_output"].update("")
            window["test_output"].print(test_output)
        if event == "generate":
            secret_msg = {
                "symbol_list": [window["symbol"].get()],
                "action": window["action"].get()
            }
            secret_msg = base64.b64encode(json.dumps(secret_msg).encode("ascii")).decode('ascii')
            window["gen_output"].update(secret_msg)
        if event == "Start":
            try:
                telegram_thread = threading.Thread(target=telegram_start, args=(config, window), daemon=True)
                if not telegram_thread.is_alive():
                    telegram_thread.start()
            except Exception:
                logging.exception("")
                sg.Popup(f"Update config failed !!\n\n{traceback.format_exc()}")

    window.close()


if __name__ == '__main__':
    try:
        run_gui()
    except Exception as e:
        logging.exception("")
        print(str(e))
