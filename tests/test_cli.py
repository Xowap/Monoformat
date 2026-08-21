from pathlib import Path

from monoformat.__main__ import main, parse_args


def test_parse_args_defaults():
    args = parse_args(["."])

    assert args.path == [Path()]
    assert not args.print_exceptions
    assert Path(".gitignore") in args.ignore_files


def test_parse_args_do_not_enter():
    args = parse_args(["-d", "secret", "."])

    assert any(p.pattern == "secret" for p in args.do_not_enter)


def test_main_formats_python(repo: Path, capsys):
    f = repo / "code.py"
    f.write_text("x=1\n")

    main([f"{repo}"])

    assert f.read_text() == "x = 1\n"
    out = capsys.readouterr().out
    assert "formatted" in out
    assert "code.py" in out


def test_main_keeps_clean_python(repo: Path, capsys):
    f = repo / "code.py"
    f.write_text("x = 1\n")

    main([f"{repo}"])

    assert "kept" in capsys.readouterr().out
