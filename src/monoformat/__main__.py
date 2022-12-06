#!/usr/bin/env python3
import re
from argparse import ArgumentParser
from pathlib import Path
from signal import SIGTERM, signal
from sys import stderr
from traceback import print_exception
from typing import NamedTuple, Optional, Sequence

import colorama

from .explorer import FormatAction, MonoExplorer
from .formatters import MonoFormatter


class Args(NamedTuple):
    """
    Command line arguments
    """

    do_not_enter: Sequence[re.Pattern]
    path: Sequence[Path]
    ignore_files: Sequence[Path]
    py_src_path: Sequence[str]
    print_exceptions: bool


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
                r"^\.(git|hg|venv|idea|vscode|tox|mypy_cache)|node_modules|package-lock.json$"
            ),
        ],
        help=(
            "A regular expression defining directories that should not be "
            "entered (defaults to .git, .hg, .venv, .idea, .vscode, .tox, "
            ".mypy_cache, node_modules)"
        ),
    )
    parser.add_argument(
        "-i",
        "--ignore-files",
        type=Path,
        action="append",
        help=(
            "A list of files to look out for that contain ignore rules "
            "(.gitignore, .git/info/exclude and .formatignore by default)"
        ),
        default=[Path(".gitignore"), Path(".git/info/exclude"), Path(".formatignore")],
    )
    parser.add_argument(
        "--py-src-path",
        type=str,
        help=(
            "When sorting imports, we look for the root of a Git repo and "
            "then we look for those glob patterns as Python source code "
            "roots. If a file is matched, its parent directory will be chosen."
        ),
        action="append",
        default=[
            ".",
            "*/manage.py",
            "src",
            "tests",
            "test",
            "*/src",
            "*/tests",
            "*/test",
        ],
    )
    parser.add_argument(
        "--print-exceptions",
        action="store_true",
        help="Print formatter exceptions",
    )
    parser.add_argument(
        "path",
        type=Path,
        nargs="+",
        help="Paths to format (directories or files)",
    )

    return Args(**parser.parse_args(argv).__dict__)


def sigterm_handler(_, __):
    """
    Handle SIGTERM signal by raising an exception
    """

    raise SystemExit(1)


def print_action(
    color: str,
    action: str,
    file: str | Path,
    is_file_bold: bool = False,
    action_width: int = 9,
):
    """
    Print a formatted action line
    """

    print(
        f"[ {color}{action:<{action_width}}{colorama.Style.RESET_ALL} ]  "
        f"{colorama.Style.BRIGHT if is_file_bold else ''}{file}{colorama.Style.RESET_ALL}"
    )


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
    colorama.init()

    explorer = MonoExplorer(
        formatter=MonoFormatter.default(context=dict(py_src_path=args.py_src_path)),
        do_not_enter=args.do_not_enter,
        ignore_files=args.ignore_files,
    )

    for info in explorer.format(args.path):
        if info.action == FormatAction.kept:
            print_action(
                colorama.Fore.CYAN,
                info.action.value,
                info.file_path,
            )
        if info.action == FormatAction.formatted:
            print_action(
                colorama.Fore.GREEN,
                info.action.value,
                info.file_path,
                is_file_bold=True,
            )
        elif info.action == FormatAction.skipped:
            print_action(
                colorama.Fore.LIGHTBLACK_EX,
                info.action.value,
                info.file_path,
            )
        elif info.action == FormatAction.failed:
            print_action(
                colorama.Fore.RED,
                info.action.value,
                info.file_path,
                is_file_bold=True,
            )

            if args.print_exceptions:
                print_exception(info.error)


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
