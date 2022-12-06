import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterator, Mapping, MutableMapping, Optional, Sequence, Set

from black import Mode, TargetVersion, WriteBack, format_file_in_place
from isort import Config
from isort.main import sort_imports
from node_edge import NodeEngine

from .exceptions import *

__all__ = [
    "BaseFormatter",
    "PythonFormatter",
    "PrettierFormatter",
    "MonoFormatter",
]


class BaseFormatter(ABC):
    """
    Basic interface for a formatter.
    """

    def __init__(self, **_):
        """
        Useless init, just eating up the kwargs so that the context mechanic
        can work.
        """

    @abstractmethod
    def format(self, file_path: Path) -> bool:
        """
        Implement this to format in place the provided file.

        Returns True if the file was formatted, False otherwise.
        """

        raise NotImplementedError

    def start(self) -> None:
        """
        Start anything you need to start (if anything) to start this formatter
        """

    def stop(self) -> None:
        """
        Cleanup what you did in start().
        """


class PythonFormatter(BaseFormatter):
    """
    In charge of formatting Python code
    """

    def __init__(self, py_src_path: Sequence[str], **_):
        super().__init__()
        self.py_src_path = py_src_path
        self.source_dirs_cache: MutableMapping[Path, Set[Path]] = {}

    def detect_repo_root(self, file_path: Path) -> Optional[Path]:
        """
        Detect the root of the repo by looking for a .git directory
        """

        path = file_path.absolute()

        while not (path / ".git").is_dir():
            path = path.parent
            if path == path.parent:
                return None

        return path

    def _find_source_dirs(self, root: Path) -> Iterator[Path]:
        """
        Underlying implementation of find_source_dirs that can then be cached
        """

        if not root:
            return

        for pattern in self.py_src_path:
            if pattern == "." or pattern == "./":
                yield root
            else:
                for match in root.glob(pattern):
                    if match.is_file():
                        yield match.parent
                    elif match.is_dir():
                        yield match

    def find_source_dirs(self, file_path: Path) -> Set[Path]:
        """
        Find the source directories of the project by looking for a .git
        directory and then looking for a src directory.
        """

        root = self.detect_repo_root(file_path)

        if root not in self.source_dirs_cache:
            self.source_dirs_cache[root] = set(self._find_source_dirs(root))

        return self.source_dirs_cache[root]

    def format(self, file_path: Path) -> bool:
        """
        We use both isort and black to format Python code
        """

        att = sort_imports(
            file_name=f"{file_path}",
            config=Config(
                profile="black",
                quiet=True,
                src_paths=set(self.find_source_dirs(file_path)),
            ),
        )
        changed = format_file_in_place(
            file_path,
            fast=False,
            mode=Mode(target_versions={TargetVersion.PY310}),
            write_back=WriteBack.YES,
        )

        return not att.incorrectly_sorted or changed


class PrettierFormatter(BaseFormatter):
    def __init__(self, **_):
        super().__init__()
        self.ne = NodeEngine(
            {
                "dependencies": {
                    "prettier": "^2.8.0",
                    "@prettier/plugin-php": "^0.19.0",
                    "prettier-plugin-svelte": "^2.7.0",
                }
            }
        )
        self.prettier = None

    def start(self) -> None:
        """
        Starting the NodeEngine and getting the prettier module
        """

        self.ne.start()
        self.prettier = self.ne.import_from("prettier")

    def stop(self) -> None:
        """
        Stopping the NodeEngine
        """

        self.ne.stop()

    def format(self, file_path: Path) -> bool:
        """
        We use prettier to format the code
        """

        info = self.prettier.getFileInfo(f"{file_path}")

        if not (parser := info.get("inferredParser")):
            raise ValueError(f"Could not infer parser for {file_path}")

        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        formatted = self.prettier.format(
            content,
            {
                "parser": parser,
                "trailingComma": "es5",
                "tabWidth": 4,
                "proseWrap": "always",
            },
        )

        if formatted == content:
            return False

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(formatted)

        return True


class MonoFormatter:
    """
    A global formatter that for each file will decide which formatter to use
    and will use it to format the file. If you want to use it with the default
    formatters, you can use the `Monoformat.default()` function to get a
    pre-configured instance.
    """

    def __init__(self, formatters: Mapping[re.Pattern, BaseFormatter]):
        self.formatters = formatters

    @classmethod
    def default(cls, context: Mapping[str, Any]) -> "MonoFormatter":
        """
        Generates a pre-configured instance
        """

        return cls(
            {
                re.compile(r".*\.py$", re.IGNORECASE): PythonFormatter(**context),
                re.compile(
                    r".*\.([jt]sx?|json|md|vue|php|html?|svelte|ya?ml|(s?c|le)ss)$",
                    re.IGNORECASE,
                ): PrettierFormatter(**context),
            }
        )

    def __enter__(self):
        """
        Starting all the formatters and what they need to start
        """

        for formatter in self.formatters.values():
            formatter.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Stopping all the formatters and what they need to stop, if some of them
        raised an exception, we will record it and raise a global exception in
        the end. This gives a chance to the other formatters to stop without
        being interrupted.
        """

        exceptions = []

        for formatter in self.formatters.values():
            try:
                formatter.stop()
            except Exception as e:
                exceptions.append(e)

        # raise the group of exceptions
        if exceptions:
            raise StopError("One or more formatters failed to stop", exceptions)

    def start(self):
        """
        In case you don't want to use this as a context manager
        """

        self.__enter__()

    def stop(self):
        """
        In case you don't want to use this as a context manager
        """

        self.__exit__(None, None, None)

    def format(self, file_path: Path) -> bool:
        """
        For a given file, finds the right formatter and attempts formatting
        """

        for pattern, formatter in self.formatters.items():
            if pattern.match(str(file_path)):
                return formatter.format(file_path)

        raise NoFormatterFound(f"No formatter found for {file_path}")
