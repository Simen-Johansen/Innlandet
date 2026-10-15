import importlib.util
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

spec = importlib.util.spec_from_file_location("probe", ROOT / "harness" / "probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_parse_skips_items_without_date():
    items = probe.parse((ROOT / "fixtures" / "nrk_sample.rss").read_bytes())
    assert len(items) == 1
    assert items[0]["title"] == "Ny gang- og sykkelvei åpner"
    assert items[0]["link"] == "https://example.org/1"
    datetime.fromisoformat(items[0]["date"])
