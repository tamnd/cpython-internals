"""The checks that run without a renderer, including the one against the real repository."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from xraymanim import checks
from xraymanim.catalogue import ANIMATIONS
from xraymanim.storyboard import Beat, Storyboard

ROOT = Path(__file__).resolve().parents[2]

DEMO = Storyboard(
    slug="a99-a-demo",
    title="A demo that only exists in the tests",
    lesson="T99",
    shapes=("box",),
    beats=(Beat("One.", 4.0), Beat("Two.", 4.0), Beat("Three.", 4.0)),
)


def test_the_repository_passes_its_own_checks():
    """The one that matters. Everything else here is about the error messages."""
    assert checks.check(ROOT) == []


@pytest.fixture
def fake(tmp_path, monkeypatch):
    """A repository with one animation in it, complete enough that nothing is wrong yet."""
    monkeypatch.setattr(checks, "ANIMATIONS", (DEMO,))
    (tmp_path / "anim").mkdir()
    (tmp_path / "anim" / "a99_a_demo.py").write_text("class A99ADemo(Explainer):\n    pass\n")
    (tmp_path / "anim" / "README.md").write_text("# The animations\n\na99-a-demo is here.\n")
    (tmp_path / "anim" / "rendered").mkdir()
    (tmp_path / "anim" / "rendered" / "a99-a-demo.gif").write_bytes(b"GIF89a")
    (tmp_path / "xraymanim").mkdir()
    shapes = "\n".join(f"`{shape}`" for shape in checks.SHAPES)
    (tmp_path / "xraymanim" / "VISUAL-SYSTEM.md").write_text(f"# The visual system\n\n{shapes}\n")
    return tmp_path


def test_the_fixture_repository_is_clean(fake):
    assert checks.check(fake) == []


def test_a_missing_scene_file(fake):
    (fake / "anim" / "a99_a_demo.py").unlink()
    assert "no scene file" in " ".join(checks.check(fake))


def test_a_scene_file_with_the_wrong_class_in_it(fake):
    """The slug, the file name and the class name are one decision, so they cannot disagree."""
    (fake / "anim" / "a99_a_demo.py").write_text("class Demo(Explainer):\n    pass\n")
    assert "should define `class A99ADemo`" in " ".join(checks.check(fake))


def test_an_animation_that_has_never_been_rendered(fake):
    (fake / "anim" / "rendered" / "a99-a-demo.gif").unlink()
    assert "not rendered yet" in " ".join(checks.check(fake))


def test_an_empty_gif(fake):
    (fake / "anim" / "rendered" / "a99-a-demo.gif").write_bytes(b"")
    assert "the rendered GIF is empty" in " ".join(checks.check(fake))


def test_a_gif_nobody_on_a_slow_connection_will_see_the_end_of(fake):
    gif = fake / "anim" / "rendered" / "a99-a-demo.gif"
    gif.write_bytes(b"0" * (checks.SIZE_LIMIT + 1))
    assert "the animation is too long" in " ".join(checks.check(fake))


def test_a_shape_that_is_drawable_and_undocumented(fake):
    document = fake / "xraymanim" / "VISUAL-SYSTEM.md"
    document.write_text(document.read_text().replace("`counter`", "the count thing"))
    assert "counter is drawable but is not described" in " ".join(checks.check(fake))


def test_an_animation_missing_from_the_index(fake):
    (fake / "anim" / "README.md").write_text("# The animations\n\nNothing here.\n")
    assert "is not listed in" in " ".join(checks.check(fake))


def test_a_broken_storyboard_is_reported_along_with_everything_else(fake, monkeypatch):
    monkeypatch.setattr(checks, "ANIMATIONS", (replace(DEMO, shapes=()),))
    assert "which shapes it draws" in " ".join(checks.check(fake))


def test_two_animations_with_the_same_slug(fake, monkeypatch):
    monkeypatch.setattr(checks, "ANIMATIONS", (DEMO, DEMO))
    assert "two animations have this slug" in " ".join(checks.check(fake))


def test_the_shipped_animations_are_the_ones_the_index_lists():
    """Both directions. The check above catches a missing entry, this catches a stale one."""
    listed = (ROOT / "anim" / "README.md").read_text()
    for line in listed.splitlines():
        if line.startswith("| a"):
            slug = line.split("(rendered/")[1].split(".gif")[0]
            assert any(item.slug == slug for item in ANIMATIONS), slug
