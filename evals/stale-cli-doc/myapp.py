"""myapp CLI."""

import argparse


def _parser():
    p = argparse.ArgumentParser(prog="myapp")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("run")
    sub.add_parser("serve")
    # NOTE: there is NO 'legacy-push' command in this version. It was removed.
    return p


def main(argv=None):
    return _parser().parse_args(argv)
