#!/usr/bin/env python3
import re
from argparse import ArgumentParser
from pathlib import Path
from signal import SIGTERM, signal
from sys import stderr
from typing import NamedTuple, Optional, Sequence

from .explorer import FormatAction, MonoExplorer
from .formatters import MonoFormatter


class Args(NamedTuple):
    """
    Command line arguments
    """

    do_not_enter: Sequence[re.Pattern]
    path: Sequence[Path]


def parse_args(argv: Optional[Sequence[str]] = None) -> Args:
    """
    Parse command line arguments

    Parameters
    ----------
    argv
        Command line arguments (optional, in case you want to override
        sys.argv)
    """

    parser = ArgumentParser()

    parser.add_argument(
        "-d",
        "--do-not-enter",
        type=re.compile,
        action="append",
        default=[
            re.compile(
                r"(\.git|\.hg|\.mypy_cache|\.nox|\.tox|\.venv|_build"
                r"|buck-out|build|dist|node_modules|webpack_bundles"
                r"|\.idea|\.vscode|__pycache__|\.pytest_cache|migrations)"
            )
        ],
    )
    parser.add_argument("path", type=Path, nargs="+")

    return Args(**parser.parse_args(argv).__dict__)


def sigterm_handler(_, __):
    """
    Handle SIGTERM signal by raising an exception
    """

    raise SystemExit(1)


def main(argv: Optional[Sequence[str]] = None):
    """
    Main entry point. This is the function that will be called when you run
    monoformat from the command line. You can also call it from your own
    code by supplying a custom argv.

    Parameters
    ----------
    argv
        Command line arguments (optional, in case you want to override
        sys.argv)
    """

    args = parse_args(argv)

    explorer = MonoExplorer(MonoFormatter.default(), args.do_not_enter)

    for info in explorer.format(args.path):
        if info.action == FormatAction.kept:
            print(f"[ Kept      ]  {info.file_path}")
        if info.action == FormatAction.formatted:
            print(f"[ Formatted ]  {info.file_path}")
        elif info.action == FormatAction.skip:
            print(f"[ Skipped   ]  {info.file_path}")
        elif info.action == FormatAction.error:
            print(f"[ Error     ]  {info.file_path}")


def __main__():
    """
    Entry point for the monoformat command line script. Different from main()
    because here we setup some things that you might not want to setup if you
    call main() form your own code.
    """

    signal(SIGTERM, sigterm_handler)

    try:
        main()
    except KeyboardInterrupt:
        stderr.write("ok, bye\n")
        exit(1)


if __name__ == "__main__":
    __main__()
