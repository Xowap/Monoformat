import re
from pathlib import Path

from monoformat.__main__ import parse_args
from monoformat.explorer import FormatAction, MonoExplorer
from monoformat.formatters import MonoFormatter

from .test_registry import FakeFormatter

DO_NOT_ENTER = parse_args(["."]).do_not_enter
IGNORE_FILES = [Path(".gitignore"), Path(".formatignore")]


def make_explorer(formatter=None):
    return MonoExplorer(
        formatter=MonoFormatter({re.compile(r".*\.py$"): formatter or FakeFormatter()}),
        do_not_enter=DO_NOT_ENTER,
        ignore_files=IGNORE_FILES,
    )


def test_finds_files(repo: Path):
    (repo / "a.py").write_text("")
    (repo / "sub").mkdir()
    (repo / "sub" / "b.py").write_text("")

    found = set(make_explorer().find_files(repo))

    assert found == {repo / "a.py", repo / "sub" / "b.py"}


def test_does_not_enter_excluded_dirs(repo: Path):
    (repo / "node_modules").mkdir()
    (repo / "node_modules" / "dep.py").write_text("")
    (repo / ".venv").mkdir()
    (repo / ".venv" / "lib.py").write_text("")
    (repo / "ok.py").write_text("")

    found = set(make_explorer().find_files(repo))

    assert found == {repo / "ok.py"}


def test_respects_gitignore(repo: Path):
    (repo / ".gitignore").write_text("generated.py\n")
    (repo / "generated.py").write_text("")
    (repo / "source.py").write_text("")

    found = set(make_explorer().find_files(repo))

    assert repo / "generated.py" not in found
    assert repo / "source.py" in found


def test_respects_formatignore(repo: Path):
    (repo / ".formatignore").write_text("vendored/\n")
    (repo / "vendored").mkdir()
    (repo / "vendored" / "lib.py").write_text("")
    (repo / "mine.py").write_text("")

    found = set(make_explorer().find_files(repo))

    assert found == {repo / "mine.py", repo / ".formatignore"}


def test_format_reports_actions(repo: Path):
    (repo / "good.py").write_text("")
    (repo / "other.txt").write_text("")

    results = {
        info.file_path.name: info.action for info in make_explorer().format([repo])
    }

    assert results["good.py"] == FormatAction.formatted
    assert results["other.txt"] == FormatAction.skipped


def test_format_reports_failures(repo: Path):
    class Broken(FakeFormatter):
        def format(self, file_path: Path) -> bool:
            msg = "boom"
            raise RuntimeError(msg)

    (repo / "bad.py").write_text("")

    results = list(make_explorer(Broken()).format([repo]))
    by_name = {info.file_path.name: info for info in results}

    assert by_name["bad.py"].action == FormatAction.failed
    assert isinstance(by_name["bad.py"].error, RuntimeError)


def test_enters_github_directory(repo: Path):
    """
    The do-not-enter pattern for `.git` must not swallow `.github`, where
    workflow files live and deserve formatting.
    """
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".github" / "workflows" / "ci.py").write_text("")

    found = set(make_explorer().find_files(repo))

    assert repo / ".github" / "workflows" / "ci.py" in found
