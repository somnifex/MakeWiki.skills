import argparse


def main(argv=None):
    p = argparse.ArgumentParser(prog="web")
    p.add_argument("--build", action="store_true")
    return p.parse_args(argv)
