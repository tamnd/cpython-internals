"""What an animation says, and how long it takes to say it, written down before it is drawn.

An animation is easy to get wrong in a way that is expensive to find out about, because the
only way to look at one is to render it, and rendering takes minutes. So every animation in
this project declares its beats as data first. The storyboard is checkable in milliseconds,
it is what the ninety second cap is enforced against, and it is what the caption track is
built from, so the captions cannot drift out of step with the picture.

It also carries the list of shapes the animation uses. That is what makes the rule in
VISUAL-SYSTEM.md mechanical rather than aspirational: a scene that starts drawing something
the visual system has no name for has to say so here first, and saying so fails the check.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .grammar import CAP_SECONDS, SHAPES

#: Animations are numbered, because they have an order in the course and a reader who has
#: seen a04 has seen a01 to a03. The slug after the number is what the file is called and
#: what the rendered GIF is called, so it has to survive being a filename and a URL.
SLUG = re.compile(r"^a\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$")

#: The same punctuation ban as everywhere else in the project. A caption is burned into the
#: video, so a stray em dash there is the one that cannot be fixed with a text edit.
FORBIDDEN = {"\u2014": "em dash", "\u2013": "en dash"}

#: A caption has to fit on one line at the bottom of a 16:9 frame on a phone. This is the
#: length past which it wraps to two lines and starts covering the picture.
CAPTION_LIMIT = 78

#: Under three beats it is a slide, not an animation, and a still picture would be cheaper
#: to make and easier to look at.
MINIMUM_BEATS = 3


@dataclass(frozen=True)
class Beat:
    """One step: what changes on screen, what the caption says while it changes.

    `seconds` is the whole step including whatever pause follows it, so the sum over the
    beats is the length of the finished video, give or take the encoder.
    """

    caption: str
    seconds: float

    def problems(self, where: str) -> list[str]:
        found = []
        if not self.caption.strip():
            found.append(f"{where}: the caption is empty")
        if "\n" in self.caption:
            found.append(f"{where}: the caption has a line break in it")
        if len(self.caption) > CAPTION_LIMIT:
            found.append(
                f"{where}: the caption is {len(self.caption)} characters, "
                f"which wraps onto the picture past {CAPTION_LIMIT}"
            )
        for character, name in FORBIDDEN.items():
            if character in self.caption:
                found.append(f"{where}: the caption has an {name} in it")
        if self.seconds <= 0:
            found.append(f"{where}: a beat has to last longer than no time at all")
        return found


@dataclass(frozen=True)
class Storyboard:
    """One animation, described well enough to check without rendering it."""

    slug: str
    title: str
    lesson: str
    beats: tuple[Beat, ...]
    shapes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def seconds(self) -> float:
        return sum(beat.seconds for beat in self.beats)

    @property
    def captions(self) -> tuple[str, ...]:
        return tuple(beat.caption for beat in self.beats)

    def problems(self) -> list[str]:
        """Everything wrong with this storyboard, as a list a checker can print."""
        found = []
        if not SLUG.match(self.slug):
            found.append(f"{self.slug}: the slug should look like a01-what-it-shows")
        if not self.title.strip():
            found.append(f"{self.slug}: the title is empty")
        for character, name in FORBIDDEN.items():
            if character in self.title:
                found.append(f"{self.slug}: the title has an {name} in it")
        if not self.lesson.strip():
            found.append(f"{self.slug}: say which lesson this belongs to")
        if len(self.beats) < MINIMUM_BEATS:
            found.append(
                f"{self.slug}: {len(self.beats)} beat(s), which is a slide rather than "
                f"an animation; under {MINIMUM_BEATS} a still picture is better"
            )
        for index, beat in enumerate(self.beats, start=1):
            found.extend(beat.problems(f"{self.slug} beat {index}"))
        if self.seconds > CAP_SECONDS:
            found.append(
                f"{self.slug}: {self.seconds:.0f} seconds, over the {CAP_SECONDS:.0f} "
                f"second cap; an animation this long is two animations"
            )
        if not self.shapes:
            found.append(f"{self.slug}: say which shapes it draws, so the grammar can be checked")
        for shape in self.shapes:
            if shape not in SHAPES:
                found.append(
                    f"{self.slug}: {shape!r} is not in the visual system; add it to "
                    f"VISUAL-SYSTEM.md and to grammar.py before drawing it"
                )
        return found
