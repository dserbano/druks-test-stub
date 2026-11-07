"""Incremental build manifest tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.sitegen.build import build
from app.sitegen.incremental import MANIFEST_NAME, Manifest, hash_bytes, hash_tree, plan_rebuild


@pytest.fixture
def seeded(tmp_path: Path):
    (tmp_path / "content").mkdir()
    (tmp_path / "content" / "a.md").write_text("# A\n", encoding="utf-8")
    (tmp_path / "content" / "b.md").write_text("# B\n", encoding="utf-8")
    (tmp_path / "site.toml").write_text('[site]\ntitle = "x"\n', encoding="utf-8")
    out = tmp_path / "public"
    build(tmp_path, out)
    return tmp_path, out


def test_second_build_skips_unchanged(seeded):
    src, out = seeded
    r = build(src, out)
    assert set(r.skipped) == {"a.md", "b.md"}
    assert r.rendered == []


def test_touching_one_source_rebuilds_only_it(seeded):
    src, out = seeded
    (src / "content" / "a.md").write_text("# A changed\n", encoding="utf-8")
    r = build(src, out)
    assert {p.rel for p in r.rendered} == {"a.md"}
    assert "b.md" in r.skipped


def test_config_change_invalidates_everything(seeded):
    src, out = seeded
    (src / "site.toml").write_text('[site]\ntitle = "new"\n', encoding="utf-8")
    r = build(src, out)
    assert {p.rel for p in r.rendered} == {"a.md", "b.md"}


def test_manifest_written_to_output(seeded):
    src, out = seeded
    m = out / MANIFEST_NAME
    assert m.exists()
    data = json.loads(m.read_text(encoding="utf-8"))
    assert "sources" in data and "global_hash" in data


def test_manifest_stores_source_hashes(seeded):
    src, out = seeded
    data = json.loads((out / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert "a.md" in data["sources"]
    assert "b.md" in data["sources"]


def test_manifest_load_from_missing_returns_empty(tmp_path):
    m = Manifest.load(tmp_path / "nope.json")
    assert m.sources == {}
    assert m.global_hash == ""


def test_manifest_save_and_load_roundtrip(tmp_path):
    m = Manifest(sources={"a": "1", "b": "2"}, global_hash="gh")
    path = tmp_path / "m.json"
    m.save(path)
    back = Manifest.load(path)
    assert back.sources == {"a": "1", "b": "2"}
    assert back.global_hash == "gh"


def test_plan_rebuild_full_when_global_hash_changes():
    m = Manifest(sources={"a.md": "h1"}, global_hash="old")
    files = {"a.md": b"x", "b.md": b"y"}
    assert plan_rebuild(files, m, "new") == {"a.md", "b.md"}


def test_plan_rebuild_subset_for_changed_source():
    files = {"a.md": b"x", "b.md": b"y"}
    gh = "G"
    m = Manifest(sources={"a.md": hash_bytes(b"x"), "b.md": hash_bytes(b"y")}, global_hash=gh)
    # No files changed.
    assert plan_rebuild(files, m, gh) == set()
    # a.md changes.
    files2 = {"a.md": b"x!", "b.md": b"y"}
    assert plan_rebuild(files2, m, gh) == {"a.md"}


def test_hash_tree_is_order_insensitive(tmp_path):
    (tmp_path / "x").write_text("x")
    (tmp_path / "y").write_text("y")
    a = hash_tree([tmp_path / "x", tmp_path / "y"])
    b = hash_tree([tmp_path / "y", tmp_path / "x"])
    assert a == b


def test_hash_tree_reacts_to_contents(tmp_path):
    f = tmp_path / "x"
    f.write_text("a")
    h1 = hash_tree([f])
    f.write_text("b")
    h2 = hash_tree([f])
    assert h1 != h2
