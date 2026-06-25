import pytest

from pattern_generator.config import PGConfig
from pattern_generator.idioms import find_idiom, format_idiom

SCRIPT_ROOT = PGConfig().script_root
_skip = pytest.mark.skipif(not (SCRIPT_ROOT / "api").is_dir(),
                           reason="GitNexusMCP/Script not present")


def test_format_idiom_none():
    assert "no idiom" in format_idiom(None)


def test_find_idiom_empty_query():
    assert find_idiom("", SCRIPT_ROOT) is None


@_skip
def test_find_idiom_returns_worked_snippet():
    idiom = find_idiom("random_write WRITE(10) compare", SCRIPT_ROOT)
    assert idiom is not None
    assert idiom["path"].endswith(".py")
    assert "def " in idiom["code"] or "class " in idiom["code"]
    # rendered form carries the provenance + a python block
    out = format_idiom(idiom)
    assert idiom["path"] in out
    assert "```python" in out
