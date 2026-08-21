"""Tests for the formatters that run through node-edge.

These are slower than the rest (they spin up a Node process and an npm
environment on first run), which is why they share module-scoped formatter
fixtures.
"""

from pathlib import Path

import pytest

from monoformat.formatters import OxfmtFormatter, PrettierFormatter


@pytest.fixture(scope="module")
def prettier():
    formatter = PrettierFormatter()
    formatter.start()

    yield formatter

    formatter.stop()


@pytest.fixture(scope="module")
def oxfmt():
    formatter = OxfmtFormatter()
    formatter.start()

    yield formatter

    formatter.stop()


def test_prettier_formats_json(prettier, repo: Path):
    f = repo / "data.json"
    f.write_text('{"foo":1,"bar":2}')

    assert prettier.format(f) is True
    assert f.read_text() == '{ "foo": 1, "bar": 2 }\n'


def test_prettier_formats_scss(prettier, repo: Path):
    f = repo / "style.scss"
    f.write_text(".foo{.bar{color:red}}")

    assert prettier.format(f) is True
    assert f.read_text() == ".foo {\n    .bar {\n        color: red;\n    }\n}\n"


def test_prettier_formats_svelte(prettier, repo: Path):
    f = repo / "App.svelte"
    f.write_text("<script>let   x=1</script>\n\n<div>{x}</div>\n")

    assert prettier.format(f) is True
    assert "let x = 1;" in f.read_text()


def test_prettier_formats_vue(prettier, repo: Path):
    f = repo / "App.vue"
    f.write_text("<template><div>hi</div></template>")

    assert prettier.format(f) is True


def test_prettier_keeps_formatted_markdown(prettier, repo: Path):
    f = repo / "doc.md"
    f.write_text("# Hello\n\nSome text.\n")

    assert prettier.format(f) is False


def test_prettier_rejects_unknown(prettier, repo: Path):
    f = repo / "mystery.zzz"
    f.write_text("???")

    with pytest.raises(ValueError, match="Could not infer parser"):
        prettier.format(f)


def test_oxfmt_formats_js(oxfmt, repo: Path):
    f = repo / "code.js"
    f.write_text("const x=  {foo:1,   bar:2}\nconsole.log( x )\n")

    assert oxfmt.format(f) is True
    assert f.read_text() == "const x = { foo: 1, bar: 2 };\nconsole.log(x);\n"


def test_oxfmt_indents_with_4_spaces(oxfmt, repo: Path):
    f = repo / "indent.js"
    f.write_text("function foo() {\nif (1) {\nreturn 2\n}\n}\n")

    assert oxfmt.format(f) is True
    assert f.read_text() == (
        "function foo() {\n    if (1) {\n        return 2;\n    }\n}\n"
    )


def test_oxfmt_formats_typescript(oxfmt, repo: Path):
    f = repo / "code.ts"
    f.write_text("const x:number=1\nexport default x\n")

    assert oxfmt.format(f) is True
    assert f.read_text() == "const x: number = 1;\nexport default x;\n"


def test_oxfmt_keeps_clean_code(oxfmt, repo: Path):
    f = repo / "clean.js"
    f.write_text("const x = { foo: 1 };\nconsole.log(x);\n")

    assert oxfmt.format(f) is False


def test_oxfmt_raises_on_syntax_error(oxfmt, repo: Path):
    f = repo / "broken.js"
    f.write_text("const const const\n")

    with pytest.raises(ValueError, match="could not format"):
        oxfmt.format(f)


def test_prettier_formats_mjml(prettier, repo: Path):
    f = repo / "mail.mjml"
    f.write_text("<mjml><mj-body><mj-text>hi</mj-text></mj-body></mjml>")

    assert prettier.format(f) is True
    assert "<mjml>\n" in f.read_text()
