from pathlib import Path

import pytest


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A fake git repo root to format files into."""
    (tmp_path / ".git").mkdir()

    return tmp_path
