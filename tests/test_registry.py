import re
from pathlib import Path

import pytest

from monoformat.exceptions import NoFormatterFound
from monoformat.formatters import (
    BaseFormatter,
    MonoFormatter,
    OxfmtFormatter,
    PrettierFormatter,
    PythonFormatter,
)


class FakeFormatter(BaseFormatter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.started = 0
        self.stopped = 0
        self.formatted = []

    def start(self):
        self.started += 1

    def stop(self):
        self.stopped += 1

    def format(self, file_path: Path) -> bool:
        self.formatted.append(file_path)

        return True


def default_patterns():
    return {
        f"{p.pattern}": f
        for p, f in MonoFormatter.default({"py_src_path": ["."]}).formatters.items()
    }


@pytest.mark.parametrize(
    ("file_name", "expected"),
    [
        ("foo.py", PythonFormatter),
        ("foo.js", OxfmtFormatter),
        ("foo.mjs", OxfmtFormatter),
        ("foo.cjs", OxfmtFormatter),
        ("foo.ts", OxfmtFormatter),
        ("foo.mts", OxfmtFormatter),
        ("foo.tsx", OxfmtFormatter),
        ("foo.jsx", OxfmtFormatter),
        ("foo.json", PrettierFormatter),
        ("foo.md", PrettierFormatter),
        ("foo.vue", PrettierFormatter),
        ("foo.svelte", PrettierFormatter),
        ("foo.scss", PrettierFormatter),
        ("foo.css", PrettierFormatter),
        ("foo.less", PrettierFormatter),
        ("foo.html", PrettierFormatter),
        ("foo.yml", PrettierFormatter),
        ("foo.yaml", PrettierFormatter),
        ("foo.php", PrettierFormatter),
        ("Dogefile", PrettierFormatter),
        ("foo.mjml", PrettierFormatter),
    ],
)
def test_default_dispatch(file_name, expected):
    formatter = MonoFormatter.default({"py_src_path": ["."]})

    for pattern, sub in formatter.formatters.items():
        if pattern.match(file_name):
            assert isinstance(sub, expected)
            break
    else:
        pytest.fail(f"No formatter matched {file_name}")


def test_no_formatter_found():
    formatter = MonoFormatter({})

    with pytest.raises(NoFormatterFound):
        formatter.format(Path("foo.zzz"))


def test_lazy_start_and_stop(tmp_path: Path):
    used = FakeFormatter()
    unused = FakeFormatter()

    formatter = MonoFormatter(
        {
            re.compile(r".*\.use$"): used,
            re.compile(r".*\.unused$"): unused,
        }
    )

    with formatter:
        formatter.format(tmp_path / "foo.use")
        formatter.format(tmp_path / "bar.use")

    assert used.started == 1
    assert used.stopped == 1
    assert used.formatted == [tmp_path / "foo.use", tmp_path / "bar.use"]
    assert unused.started == 0
    assert unused.stopped == 0
