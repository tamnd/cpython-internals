"""The checks that do not need a renderer, which is nearly all of them.

Rendering an animation takes minutes and needs ffmpeg, so anything that can be checked
without rendering should be, and this is that list. It runs in a few milliseconds, it runs
in every CI job rather than only in the one with manim installed, and it catches the whole
class of mistake where the plan, the scene file, the committed GIF and the page that links
to them stop agreeing with each other.

What it deliberately cannot tell you is whether the animation is any good, or whether it
shows what the caption says it shows. Nothing can. That is what watching it is for.
"""

from __future__ import annotations

from pathlib import Path

from .catalogue import ANIMATIONS, class_name, module_name
from .grammar import SHAPES
from .render import RENDERED

#: The document that names every shape and what it means. A shape that is not in here is a
#: shape the reader has to work out from context, which is how a visual grammar turns back
#: into a pile of drawings.
VISUAL_SYSTEM = Path("xraymanim") / "VISUAL-SYSTEM.md"

#: The page that lists the animations for a human.
INDEX = Path("anim") / "README.md"

#: A GIF over this is one somebody on a slow connection will never see the end of, and it
#: is also a file that makes cloning this repository slower forever, because git keeps it.
#: Hitting the limit means the animation is too long, not that the limit is wrong.
SIZE_LIMIT = 6 * 1024 * 1024


def check(root: Path) -> list[str]:
    """Everything wrong across the whole set, as lines a person can act on."""
    problems: list[str] = []
    seen: set[str] = set()
    for storyboard in ANIMATIONS:
        problems.extend(storyboard.problems())
        if storyboard.slug in seen:
            problems.append(f"{storyboard.slug}: two animations have this slug")
        seen.add(storyboard.slug)
        problems.extend(_scene(storyboard.slug, root))
        problems.extend(_rendered(storyboard.slug, root))
    problems.extend(_visual_system(root))
    problems.extend(_index(root))
    return problems


def _scene(slug: str, root: Path) -> list[str]:
    source = root / "anim" / f"{module_name(slug)}.py"
    if not source.is_file():
        return [f"{slug}: no scene file at {source}"]
    wanted = f"class {class_name(slug)}("
    if wanted not in source.read_text(encoding="utf-8"):
        return [f"{slug}: {source} should define `{wanted.rstrip('(')}`"]
    return []


def _rendered(slug: str, root: Path) -> list[str]:
    gif = root / RENDERED / f"{slug}.gif"
    if not gif.is_file():
        return [f"{slug}: not rendered yet, run `just build-animations`"]
    size = gif.stat().st_size
    if size == 0:
        return [f"{slug}: the rendered GIF is empty"]
    if size > SIZE_LIMIT:
        return [
            f"{slug}: the GIF is {size / 1024 / 1024:.1f} MB, over the "
            f"{SIZE_LIMIT / 1024 / 1024:.0f} MB limit, so the animation is too long"
        ]
    return []


def _visual_system(root: Path) -> list[str]:
    document = root / VISUAL_SYSTEM
    if not document.is_file():
        return [f"there is no visual system document at {document}"]
    text = document.read_text(encoding="utf-8")
    return [
        f"{shape} is drawable but is not described in {VISUAL_SYSTEM}"
        for shape in SHAPES
        if f"`{shape}`" not in text
    ]


def _index(root: Path) -> list[str]:
    page = root / INDEX
    if not page.is_file():
        return [f"there is no index at {page}"]
    text = page.read_text(encoding="utf-8")
    return [
        f"{storyboard.slug} is not listed in {INDEX}"
        for storyboard in ANIMATIONS
        if storyboard.slug not in text
    ]
