from src.config import config, configure_logging
from src.gui import run_gui
import argparse


parser = argparse.ArgumentParser(add_help=False, description="Data Driven Identification Criteria for GAI.")
parser.add_argument("--gui", default=False, action="store_true", help="GUI")
args = parser.parse_args()


def main():
    pass


if __name__ == "__main__":
    configure_logging()
    if args.gui:
        run_gui()
    else:
        main()
