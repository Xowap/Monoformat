import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Mapping

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

    def format(self, file_path: Path) -> None:
        """
        We use both isort and black to format Python code
        """

        att = sort_imports(
            file_name=f"{file_path}",
            config=Config(
                profile="black",
                quiet=True,
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
    def __init__(self):
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

    def format(self, file_path: Path) -> None:
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

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(formatted)

        return content != formatted


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
    def default(cls) -> "MonoFormatter":
        """
        Generates a pre-configured instance
        """

        return cls(
            {
                re.compile(r".*\.py$"): PythonFormatter(),
                re.compile(
                    r".*\.([jt]sx?|json|md|vue|php|html?|svelte|ya?ml|s?css)$"
                ): PrettierFormatter(),
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
