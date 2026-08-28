"""One blueprint that passes every rule, and the tools to break exactly one thing in it.

Tests that build a document by hand end up asserting on the fixture rather than on the
rules, so everything here starts from `clean_text` and changes one line.
"""

from __future__ import annotations

from pathlib import Path

from bpcheck.rules import SECTIONS

TITLE = "# BP-DEMO: a subsystem that exists only in the tests"

HEADER = """**Covers:** `Python/demo.c`
**Lesson:** T99, the demo
**Status:** complete
**Compatibility tier:** B"""

#: Every section gets its own body. They are all different so that a test can change one
#: line without the uniqueness check in `replace` firing on a body that appears twice, and
#: an empty section is its own rule with its own test rather than something the fixture
#: happens to have.
BODIES = {
    "Purpose and scope": "The demo covers nothing and is bounded by nothing.",
    "Data structures": "One struct, and it has no fields in it.",
    "Algorithms": "One algorithm, and it returns immediately.",
    "Invariants": "**INV-DEMO-001.** The demo holds.\n\n**INV-DEMO-002.** It keeps holding.",
    "Observable behaviour": "A Python program cannot tell the demo apart from nothing.",
    "Edge cases and error paths": "There is one edge and the demo is on both sides of it.",
    "Interactions": "Nothing depends on the demo, which is what makes it a demo.",
    "Conformance": "Held up by nothing, see the lesson T99, which section 8 is allowed to say.",
    "Port notes": "Porting the demo takes no time at all.",
}


def clean_text() -> str:
    """A blueprint with no problems in it."""
    parts = [TITLE, "", HEADER, ""]
    for number, title in enumerate(SECTIONS, start=1):
        parts.append(f"## {number}. {title}")
        parts.append("")
        parts.append(BODIES[title])
        parts.append("")
    return "\n".join(parts)


def write(path: Path, text: str) -> Path:
    """Write a blueprint and an index that lists it, which is what `lint` expects."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    index = path.parent / "README.md"
    if not index.exists():
        index.write_text(f"# Blueprints\n\n[{path.stem}]({path.name})\n", encoding="utf-8")
    return path


def replace(text: str, old: str, new: str) -> str:
    """Change one line, and fail loudly if the fixture stopped containing it."""
    assert text.count(old) == 1, f"the fixture no longer contains {old!r} exactly once"
    return text.replace(old, new)
