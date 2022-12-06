import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterator, Optional, Sequence

from pathspec import pathspec

from .exceptions import *
from .formatters import MonoFormatter


class FormatAction(Enum):
    """
    Outcome of a file formatting
    """

    kept = "kept"
    formatted = "formatted"
    skipped = "skipped"
    failed = "failed"


@dataclass
class FormatInfo:
    """
    Information about a file formatting
    """

    file_path: Path
    action: FormatAction
    error: Optional[Exception] = None


class GitIgnore:
    """
    A wrapper around pathspec that helps checking if a file should be
    considered or not during a scan
    """

    def __init__(self, root: Path, path: Path):
        """
        The root is the root of the authority of the file while the path is
        the path for the file. For example .git/info/exclude rules over the
        same files as .gitignore.
        """

        self.path = path
        self.root = root

        with open(path) as f:
            self.spec = pathspec.PathSpec.from_lines("gitwildmatch", f)

    def should_ignore(self, path: Path) -> bool:
        """
        For a given path, indicates if it should be ignored. If the path is
        outside the root then ignore the problem and say the file shouldn't
        be ignored.
        """

        try:
            return self.spec.match_file(path.relative_to(self.root))
        except ValueError:
            return False


class MonoExplorer:
    """
    Utility class that can explore directories and format files inside
    """

    def __init__(
        self,
        formatter: MonoFormatter,
        do_not_enter: Sequence[re.Pattern],
        ignore_files: Sequence[Path],
    ):
        self.formatter = formatter
        self.do_not_enter = do_not_enter
        self.ignore_files = ignore_files

    def find_ignore_files(self, path: Path) -> Iterator[GitIgnore]:
        """ "
        Find all .gitignore (or .formatignore or whatever is listed in
        ignore_files) that could be ruling over the provide path and yield
        them.
        """

        for parent in path.parents:
            for ignore_file in self.ignore_files:
                if ignore_file.is_absolute():
                    ignore_path = ignore_file
                else:
                    ignore_path = parent / ignore_file

                if ignore_path.exists():
                    yield GitIgnore(parent, ignore_path)

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

            if any(
                checker.should_ignore(current)
                for checker in self.find_ignore_files(current)
            ):
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
                        changed = self.formatter.format(file_path)
                    except NoFormatterFound:
                        yield FormatInfo(file_path, FormatAction.skipped)
                    except Exception as e:
                        yield FormatInfo(file_path, FormatAction.failed, e)
                    else:
                        yield FormatInfo(
                            file_path,
                            FormatAction.formatted if changed else FormatAction.kept,
                        )
