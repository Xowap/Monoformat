from pathlib import Path

from monoformat.formatters import PythonFormatter

PY_SRC_PATH = [".", "src", "tests"]


def make_formatter() -> PythonFormatter:
    return PythonFormatter(py_src_path=PY_SRC_PATH)


def test_formats_ugly_code(repo: Path):
    f = repo / "ugly.py"
    f.write_text("x=1\ny = [1,\n  2 ,3]\n")

    assert make_formatter().format(f) is True
    assert f.read_text() == "x = 1\ny = [1, 2, 3]\n"


def test_keeps_clean_code(repo: Path):
    f = repo / "clean.py"
    f.write_text("x = 1\ny = [1, 2, 3]\n")

    assert make_formatter().format(f) is False


def test_sorts_imports(repo: Path):
    f = repo / "imports.py"
    f.write_text("import sys\nimport os\n\nprint(os, sys)\n")

    assert make_formatter().format(f) is True
    assert f.read_text() == "import os\nimport sys\n\nprint(os, sys)\n"


def test_first_party_imports_grouped_last(repo: Path):
    (repo / "src" / "my_pkg").mkdir(parents=True)
    (repo / "src" / "my_pkg" / "__init__.py").write_text("")

    f = repo / "src" / "my_pkg" / "main.py"
    f.write_text("from my_pkg import thing\nimport os\n\nprint(os, thing)\n")

    make_formatter().format(f)

    assert f.read_text() == (
        "import os\n\nfrom my_pkg import thing\n\nprint(os, thing)\n"
    )


def test_detect_repo_root(repo: Path):
    (repo / "sub" / "dir").mkdir(parents=True)
    formatter = make_formatter()

    assert formatter.detect_repo_root(repo / "sub" / "dir" / "x.py") == repo


def test_detect_repo_root_none(tmp_path: Path):
    formatter = make_formatter()

    assert formatter.detect_repo_root(Path("/x/y/z.py")) is None
