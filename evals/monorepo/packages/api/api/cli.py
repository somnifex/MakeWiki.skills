import argparse


def main(argv=None):
    p = argparse.ArgumentParser(prog="api")
    p.add_argument("--serve", action="store_true")
    return p.parse_args(argv)
