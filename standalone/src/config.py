import os
import sys
import yaml
import shutil
import logging


def get_logging_level():
    return os.getenv("LOGGING_LEVEL", "INFO")


def configure_logging():
    logging_level = get_logging_level().upper()
    numeric_level = getattr(logging, logging_level, None)

    if not isinstance(numeric_level, int):
        raise Exception(f"Invalid log level: {numeric_level}")

    logging.basicConfig(
        level=numeric_level,
        datefmt="%Y-%m-%d %H:%M",
        format="[%(asctime)s] [%(levelname)s] [%(module)s]: #%(funcName)s @%(lineno)d: %(message)s",
    )
    logging.info(f"Logging level: {logging_level}")


def save_config(config: dict):
    backup_config(config)
    try:
        path = config["path"]
        path = os.path.join(os.path.dirname(path), "config.yaml")
        config["path"] = path
        with open(path, "w", encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    except Exception as e:
        logging.exception("")
        restore_config(config)
        raise e


def backup_config(config: dict):
    path = config["path"]
    source = path
    destination = os.path.join(os.path.dirname(path), "config_backup.yaml")
    shutil.copyfile(source, destination)


def restore_config(config: dict):
    path = config["path"]
    destination = path
    source = os.path.join(os.path.dirname(path), "config_backup.yaml")
    shutil.copyfile(source, destination)
    os.remove(source)


def load_config() -> dict:

    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
        print("EXE", application_path)
    elif __file__:
        application_path = os.getcwd()
        print("SCRIPT", application_path)

    if os.path.exists(os.path.join(application_path, "config.yaml")):
        path = os.path.join(application_path, "config.yaml")
    else:
        path = os.path.join(application_path, "config_template_okex.yaml")

    with open(path, "r", encoding='utf-8') as f:
        config = yaml.safe_load(f)

    if "listing_setting" not in config:
        config["listing_setting"] = {
            "whitelist_activate": False,
            "blacklist_activate": False,
        }

    if "session" not in config["telegram_setting"]:
        config["telegram_setting"]["session"] = "anon"

    if "make_short" not in config["order_setting"]:
        config["order_setting"]["make_short"] = False

    if "auto_sl_tp" not in config["other_setting"]:
        config["other_setting"]["auto_sl_tp"] = False

    if "sl_limit" not in config["order_setting"]:
        config["order_setting"]["sl_limit"] = False

    if "tp_limit" not in config["order_setting"]:
        config["order_setting"]["tp_limit"] = False

    if "minimum_volume" not in config["order_setting"]:
        config["order_setting"]["minimum_volume"] = 0

    if "fibonacci" not in config["order_setting"]:
        config["order_setting"]["fibonacci"] = 1.0

    config = type_casting(config)
    config["path"] = path
    return config


def type_casting(config: dict):
    for key, value in config["order_setting"].items():
        if isinstance(value, str):
            try:
                value = float(value)
                config["order_setting"][key] = value
            except Exception:
                pass
    return config


configure_logging()
config = load_config()
