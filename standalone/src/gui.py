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
                sg.Radio("Perpetual Data", "telegram signal", key="P_signal", disabled=True, default=False),
                sg.Radio("Rose Premium", "telegram signal", key="R_signal", default=True),
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
                        [sg.Text("Stop Loss"), sg.In(size=15, key="stop_loss"), sg.Text("%")],
                        [sg.Text("Take Profit"), sg.In(size=15, key="take_profit"), sg.Text("%")],
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
                    [sg.Checkbox('use_image', default=False, key="use_image", disabled=True)],
                    [sg.Text("maximum latency"), sg.In(size=15, key="maximum_latency")],
                ],
                element_justification="left"
            )
        ]],
        element_justification="center",
        visible=True
    )
    return layout


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
                window[key].update(value=value)

        # exchange setting
        for key, value in config["exchange_setting"].items():
            window[key].update(value=value)

        # Order setting
        for key, value in config["order_setting"].items():
            window[key].update(value=value)

        # Other setting
        for key, value in config["other_setting"].items():
            window[key].update(value=value)

    except Exception:
        logging.exception("")
        sg.Popup(f"Config parsing error !!\n\n{traceback.format_exc()}")


def validate_config(config: dict):
    if (config["order_setting"]["stop_loss"] == 0) ^ (config["order_setting"]["take_profit"] == 0):
        raise Exception("Stop loss and Take profit has to be both zero or both set.")


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
            elif key == "signal_channel":
                continue
            else:
                config["telegram_setting"][key] = window[key].get()

        # exchange setting
        config["exchange_setting"]["exchange"] = window["exchange"].get()
        config["exchange_setting"]["api_key"] = window["api_key"].get()
        config["exchange_setting"]["api_secret"] = window["api_secret"].get()
        config["exchange_setting"]["subaccount"] = window["subaccount"].get()

        # order setting
        for key in config["order_setting"]:
            config["order_setting"][key] = window[key].get()

        # other setting
        for key in config["other_setting"]:
            config["other_setting"][key] = window[key].get()

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
    layout = [
        [sg.TabGroup(
            [[
                sg.Tab("Setting", setting_tab, element_justification="center"),
                sg.Tab("Run", main_tab, element_justification="center")
            ]]
        )]
    ]

    window = sg.Window("Auto Order Bot Pro", layout, finalize=True)
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
