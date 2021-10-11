import ccxt
import json
import base64
import traceback
import logging
import threading
import PySimpleGUI as sg
from telethon import TelegramClient
from src.exchange import ExchangeClient
from src.exchange.parse import parse_pro
from src.config import config, save_config, type_casting
from src.telegram_bot import telegram_start


def telegram_setting_layout():
    layout = sg.Frame(
        "Telegram Setting",
        [
            # [sg.Combo(["Perpetual Data", "Rose Premium"])],
            [
                sg.Radio("Perpetual Data", "telegram signal", key="P_signal"),
                sg.Radio("Rose Premium", "telegram signal", key="R_signal"),
                # sg.Radio("Notification", "telegram signal", key="N_signal")
            ],

            [
                sg.Column(
                    [
                        [sg.Text("Telegram ID"), sg.In(key="telegram_api_id")],
                        [sg.Text("Telegram Hash"), sg.In(key="telegram_api_hash")],
                        [sg.Text("Signal channel"), sg.In(key="signal_channel")],  # , sg.Button("Browse", key="all_dialog1")
                        [sg.Text("Nofify channel"), sg.In(key="notify_channel")],  # , sg.Button("Browse", key="all_dialog2")
                        [sg.Text("Testing channel"), sg.In(key="test_channel")],  # , sg.Button("Browse", key="all_dialog3")
                        [sg.Button("Login", key="login")],
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
                        [sg.Text("Exchange"), sg.Combo(ccxt.exchanges, size=42, key="exchange")],
                        [sg.Text("API Key"), sg.In(key="api_key")],
                        [sg.Text("API Secret"), sg.In(key="api_secret")],
                        [sg.Text("Subaccount"), sg.In(key="subaccount")],
                    ],
                    element_justification="right"
                )
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
                        [sg.Radio('Limit', "order_type", key="limit")],
                        [sg.Radio("Market", "order_type", key="market")],
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
                        [sg.Text("Stop Loss"), sg.In(size=15, key="stop_loss"), sg.Text("")],
                        [sg.Text("Take Profit"), sg.In(size=15, key="take_profit"), sg.Text("")],
                    ],
                    element_justification="right"
                ),
                sg.Column(
                    [
                        [sg.Text("minimum margin level/ratio"), sg.In(size=15, key="margin_level_ratio")],
                        [sg.Text("hold", visible=False), sg.In(size=15, key="hold", visible=False)]
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
                    [sg.Checkbox('pro', default=False, key="pro")],
                    [sg.Text("maximum latency"), sg.In(size=15, key="maximum_latency")],
                ],
                element_justification="left"
            )
        ]],
        element_justification="center",
        visible=True
    )
    return layout


def test_layout():
    return [
        [sg.Frame(
            "Generate encoded message",
            [
                [sg.Text("symbol  : "), sg.Input(key="symbol")],
                [sg.Text("action    : "), sg.Input(key="action")],
                [sg.Button("generate", key="generate")],
                [sg.Text("encoded :"), sg.Input(key="gen_output")],
            ]
        )],
        [sg.Frame(
            "Parsing",
            [
                [sg.Text("Input message"), sg.Multiline(size=(100, 10), key="test_input")],
                [sg.Text("Results           "), sg.Multiline(size=(100, 2), key="test_output")],
                [sg.Button("Parse", key="parse")],
            ]
        )],
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
            else:
                try:
                    window[key].update(value=value)
                except Exception:
                    pass

        # exchange setting
        for key, value in config["exchange_setting"].items():
            try:
                window[key].update(value=value)
            except Exception:
                pass

        # Order setting
        for key, value in config["order_setting"].items():
            try:
                window[key].update(value=value)
            except Exception:
                pass

        # Other setting
        for key, value in config["other_setting"].items():
            try:
                window[key].update(value=value)
            except Exception:
                pass

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


def update_config(window):
    try:
        validate_config(config)

        # telegram setting
        for key in config["telegram_setting"]:
            if key == "signal":
                if window["R_signal"].get() is True:
                    config["telegram_setting"]["signal"] = "Rose"
                elif window["P_signal"].get() is True:
                    config["telegram_setting"]["signal"] = "Perpetual"
            elif key == "signal_channel":
                continue
            else:
                try:
                    config["telegram_setting"][key] = window[key].get()
                except Exception:
                    pass

        # exchange setting
        for key in config["exchange_setting"]:
            try:
                config["exchange_setting"][key] = window[key].get()
            except Exception:
                pass

        # order setting
        for key in config["order_setting"]:
            try:
                config["order_setting"][key] = window[key].get()
            except Exception:
                pass

        # other setting
        for key in config["other_setting"]:
            try:
                config["other_setting"][key] = window[key].get()
            except Exception:
                pass

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
        # password=lambda: sg.popup_get_text("Please enter your 2FA password")
    )
    telegram_client.disconnect()


def run_gui():
    sg.theme('DarkAmber')
    setting_tab = [
        [
            telegram_setting_layout(),
            sg.VerticalSeparator(pad=None),
            sg.Column([[exchange_setting_layout()], [other_setting_layout()]])
        ],
        [order_setting_layout()],
        [save_setting_layout()],
    ]
    main_tab = [
        [sg.Button("Start")],
        [sg.Multiline(size=(120, 30), key="log", reroute_stderr=True)]
    ]
    test_tab = test_layout()
    layout = [
        [sg.TabGroup(
            [[
                sg.Tab("Setting", setting_tab, element_justification="center"),
                sg.Tab("Run", main_tab, element_justification="center"),
                sg.Tab("Test", test_tab, element_justification="left")
            ]]
        )]
    ]

    window = sg.Window("Auto Order Bot Pro", layout, finalize=True)
    config_setup(window)

    # window["gen_output"].BackgroundColor = window["symbol"].BackgroundColor

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Exit"):
            break
        if event == "login":
            telegram_login()
            sg.Popup("Login Success.")
        if event == "Save":
            update_config(window)
        if event == "parse":
            test_input = window["test_input"].get()
            if config["other_setting"]["pro"]:
                symbol_list, action = parse_pro(test_input)
            else:
                symbol_list, action = ExchangeClient(config).parse(test_input, None)
            test_output = f"symbol_list: {symbol_list}\naction: {action}"
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
