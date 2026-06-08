from pathlib import Path
from radar.config import load_settings, load_sources, Settings


def test_load_sources_parses_entries():
    sources = load_sources(Path("config/sources.yaml"))
    assert len(sources) >= 4
    gh = [s for s in sources if s.kind == "github"][0]
    assert gh.tier == "T1.5"
    assert gh.name == "GitHub Trending AI"


def test_load_settings_exposes_weights_and_thresholds():
    s: Settings = load_settings(Path("config/settings.yaml"))
    assert abs(sum(s.weights.values()) - 1.0) < 1e-6
    assert s.tier_weight["T1"] == 5
    assert s.threshold_for("model") == 3.5
    assert s.threshold_for("unknown_category") == s.thresholds["default"]
