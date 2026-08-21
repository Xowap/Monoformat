"""Formatter implementations and the registry tying them to file types."""

import re
import subprocess
from abc import ABC, abstractmethod
from collections.abc import Iterator, Mapping, MutableMapping, Sequence
from pathlib import Path
from typing import Any, ClassVar

from node_edge import NodeEngine

from .exceptions import NoFormatterFound, StopError

__all__ = [
    "BaseFormatter",
    "MonoFormatter",
    "OxfmtFormatter",
    "PrettierFormatter",
    "PythonFormatter",
]


# Monoformat's signature style: 4-space indentation across the board.
# printWidth is pinned because Prettier and oxfmt have different defaults
# (80 vs 100) and switching formatters shouldn't reflow the code.
STYLE_OPTIONS = {
    "trailingComma": "es5",
    "tabWidth": 4,
    "printWidth": 80,
}

PRETTIER_OPTIONS = {
    **STYLE_OPTIONS,
    "proseWrap": "always",
}

# oxfmt shares Prettier's option names for the style basics.
OXFMT_OPTIONS = {
    **STYLE_OPTIONS,
}


def _find_ruff_bin() -> str:
    """Locate the ruff binary shipped by the ``ruff`` PyPI package."""
    from ruff.__main__ import find_ruff_bin

    return find_ruff_bin()


class BaseFormatter(ABC):
    """
    Basic interface for a formatter.
    """

    def __init__(self, **_):  # noqa: B027 -- optional hook, not abstract
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

    def start(self) -> None:  # noqa: B027 -- optional hook, not abstract
        """
        Start anything you need to start (if anything) to start this formatter
        """

    def stop(self) -> None:  # noqa: B027 -- optional hook, not abstract
        """
        Cleanup what you did in start().
        """


class PythonFormatter(BaseFormatter):
    """
    In charge of formatting Python code, using Ruff (both its import sorter
    and its Black-compatible formatter).
    """

    def __init__(self, py_src_path: Sequence[str], **_):
        """
        Parameters
        ----------
        py_src_path
            Glob patterns (relative to the repo root) locating Python source
            roots, used for first-party import classification.
        """
        super().__init__()
        self.py_src_path = py_src_path
        self.source_dirs_cache: MutableMapping[Path | None, set[Path]] = {}
        self.ruff_bin = _find_ruff_bin()

    def detect_repo_root(self, file_path: Path) -> Path | None:
        """
        Detect the root of the repo by looking for a .git directory
        """
        path = file_path.absolute()

        while not (path / ".git").is_dir():
            path = path.parent
            if path == path.parent:
                return None

        return path

    def _find_source_dirs(self, root: Path | None) -> Iterator[Path]:
        """
        Underlying implementation of find_source_dirs that can then be cached
        """
        if not root:
            return

        for pattern in self.py_src_path:
            if pattern in (".", "./"):
                yield root
            else:
                for match in root.glob(pattern):
                    if match.is_file():
                        yield match.parent
                    elif match.is_dir():
                        yield match

    def find_source_dirs(self, file_path: Path) -> set[Path]:
        """
        Find the source directories of the project by looking for a .git
        directory and then looking for a src directory.
        """
        root = self.detect_repo_root(file_path)

        if root not in self.source_dirs_cache:
            found = set(self._find_source_dirs(root))
            without_root = found - {root}
            self.source_dirs_cache[root] = without_root or found

        return self.source_dirs_cache[root]

    def _src_config(self, file_path: Path) -> str:
        """
        Renders the computed source directories into an inline Ruff ``src``
        configuration, for first-party import detection.
        """
        dirs = sorted(f"{d}" for d in self.find_source_dirs(file_path))
        inner = ", ".join(f'"{d}"' for d in dirs)

        return f"src = [{inner}]"

    def format(self, file_path: Path) -> bool:
        """
        We use Ruff to both sort imports and format the code, replicating the
        historical isort + black behavior.
        """
        before = file_path.read_bytes()

        subprocess.run(
            [
                self.ruff_bin,
                "check",
                "--select",
                "I",
                "--fix",
                "--exit-zero",
                "--quiet",
                "--config",
                self._src_config(file_path),
                f"{file_path}",
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [self.ruff_bin, "format", "--quiet", f"{file_path}"],
            check=True,
            capture_output=True,
        )

        return file_path.read_bytes() != before


class PrettierFormatter(BaseFormatter):
    """
    Formats all the languages that Prettier (and its plugins) understand.
    """

    PLUGINS = (
        "@prettier/plugin-php",
        "prettier-plugin-svelte",
    )

    # Extensions that Prettier does not know about but that are close enough
    # to a supported language to be formatted by one of its parsers.
    PARSER_OVERRIDES: ClassVar[Mapping[str, str]] = {
        ".mjml": "html",
    }

    # Extra Prettier options for specific extensions.
    OPTIONS_OVERRIDES: ClassVar[Mapping[str, Mapping[str, Any]]] = {
        # MJML tags are unknown to the HTML parser, which by default makes
        # them whitespace-sensitive and produces mangled-looking output.
        ".mjml": {"htmlWhitespaceSensitivity": "ignore"},
    }

    def __init__(self, **_):
        """
        Configures (without starting) the Node engine that runs Prettier.
        """
        super().__init__()
        self.ne = NodeEngine(
            {
                "dependencies": {
                    "prettier": "^3.9.0",
                    "@prettier/plugin-php": "^0.25.0",
                    "prettier-plugin-svelte": "^4.1.0",
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
        if not (parser := self.PARSER_OVERRIDES.get(file_path.suffix.lower())):
            info = self.ne.resolve(
                self.prettier.getFileInfo(
                    f"{file_path}", {"plugins": list(self.PLUGINS)}
                )
            )
            parser = info.get("inferredParser")

        if not parser:
            msg = f"Could not infer parser for {file_path}"
            raise ValueError(msg)

        content = file_path.read_text(encoding="utf-8")

        formatted = self.ne.resolve(
            self.prettier.format(
                content,
                {
                    **PRETTIER_OPTIONS,
                    **self.OPTIONS_OVERRIDES.get(file_path.suffix.lower(), {}),
                    "parser": parser,
                    "plugins": list(self.PLUGINS),
                },
            )
        )

        if formatted == content:
            return False

        file_path.write_text(formatted, encoding="utf-8")

        return True


class OxfmtFormatter(BaseFormatter):
    """
    Formats JS/TS files using oxfmt, the (much faster) Rust-based formatter
    from the Oxc project.
    """

    def __init__(self, **_):
        """
        Configures (without starting) the Node engine that runs oxfmt.
        """
        super().__init__()
        self.ne = NodeEngine({"dependencies": {"oxfmt": "^0.64.0"}})
        self.oxfmt_format = None

    def start(self) -> None:
        """
        Starting the NodeEngine and getting oxfmt's format function
        """
        self.ne.start()
        self.oxfmt_format = self.ne.import_from("oxfmt", "format")

    def stop(self) -> None:
        """
        Stopping the NodeEngine
        """
        self.ne.stop()

    def format(self, file_path: Path) -> bool:
        """
        We use oxfmt to format the code
        """
        content = file_path.read_text(encoding="utf-8")

        result = self.ne.resolve(
            self.oxfmt_format(f"{file_path.name}", content, OXFMT_OPTIONS)
        )
        errors = result.get("errors")

        if len(errors):
            msg = f"oxfmt could not format {file_path}: {errors[0].get('message')}"
            raise ValueError(msg)

        formatted = result.get("code")

        if formatted == content:
            return False

        file_path.write_text(formatted, encoding="utf-8")

        return True


class MonoFormatter:
    """
    A global formatter that for each file will decide which formatter to use
    and will use it to format the file. If you want to use it with the default
    formatters, you can use the `Monoformat.default()` function to get a
    pre-configured instance.
    """

    def __init__(self, formatters: Mapping[re.Pattern, BaseFormatter]):
        """
        Parameters
        ----------
        formatters
            Maps file-name patterns to the formatter in charge.
        """
        self.formatters = formatters
        self._started: set[int] = set()

    @classmethod
    def default(cls, context: Mapping[str, Any]) -> "MonoFormatter":
        """
        Generates a pre-configured instance
        """
        return cls(
            {
                re.compile(r".*\.py$", re.IGNORECASE): PythonFormatter(**context),
                re.compile(
                    r".*\.([cm]?[jt]sx?)$",
                    re.IGNORECASE,
                ): OxfmtFormatter(**context),
                re.compile(
                    r".*(\.(json|md|vue|php|html?|mjml|svelte|ya?ml|(s?c|le)ss)"
                    r"|(Doge|Flux)file)$",
                    re.IGNORECASE,
                ): PrettierFormatter(**context),
            }
        )

    def __enter__(self):
        """
        Formatters are started lazily on first use (some of them spin up a
        whole Node.js process, which is expensive if no matching file ever
        shows up), so there is nothing to do here.
        """
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
            if id(formatter) not in self._started:
                continue

            try:
                formatter.stop()
            except Exception as e:
                exceptions.append(e)

        self._started.clear()

        if exceptions:
            msg = "One or more formatters failed to stop"
            raise StopError(msg, exceptions)

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
                if id(formatter) not in self._started:
                    formatter.start()
                    self._started.add(id(formatter))

                return formatter.format(file_path)

        msg = f"No formatter found for {file_path}"
        raise NoFormatterFound(msg)
