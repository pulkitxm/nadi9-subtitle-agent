import argparse

from nadi9 import __version__


def main() -> None:
    parser = argparse.ArgumentParser(description="Evidence-grounded Nadi-9 subtitle proposals")
    parser.add_argument("--version", action="version", version=__version__)
    parser.parse_args()
    parser.print_help()


if __name__ == "__main__":
    main()
