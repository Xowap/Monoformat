import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterator, Optional, Sequence

from .exceptions import *
from .formatters import MonoFormatter


class FormatAction(Enum):
    """
    Outcome of a file formatting
    """

    done = "done"
    skip = "skip"
    error = "error"


@dataclass
class FormatInfo:
    """
    Information about a file formatting
    """

    file_path: Path
    action: FormatAction
    error: Optional[Exception] = None


class MonoExplorer:
    """
    Utility class that can explore directories and format files inside
    """

    def __init__(self, formatter: MonoFormatter, do_not_enter: Sequence[re.Pattern]):
        self.formatter = formatter
        self.do_not_enter = do_not_enter

    def find_files(self, path: Path) -> Iterator[Path]:
        """
        Find all files in the provided path, in accordance with the
        do_not_enter patterns.

        Parameters
        ----------
        path
            Path to explore
        """

        stack = [path]

        while stack:
            current = stack.pop(0)

            if any(pattern.match(current.name) for pattern in self.do_not_enter):
                continue

            if current.is_dir():
                stack.extend(sorted(current.iterdir()))
            else:
                yield current

    def format(self, paths: Sequence[Path]) -> Iterator[FormatInfo]:
        """
        Format all files in the provided paths, in accordance with the
        do_not_enter patterns.

        Parameters
        ----------
        paths
            Paths to explore
        """

        with self.formatter:
            for path in paths:
                for file_path in self.find_files(path):
                    try:
                        self.formatter.format(file_path)
                    except NoFormatterFound:
                        yield FormatInfo(file_path, FormatAction.skip)
                    except Exception as e:
                        yield FormatInfo(file_path, FormatAction.error, e)
                    else:
                        yield FormatInfo(file_path, FormatAction.done)
