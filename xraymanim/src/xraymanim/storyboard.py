"""What an animation says, and how long it takes to say it, written down before it is drawn.

An animation is easy to get wrong in a way that is expensive to find out about, because the
only way to look at one is to render it, and rendering takes minutes. So every animation in
this project declares its beats as data first. The storyboard is checkable in milliseconds,
it is what the ninety second cap is enforced against, and it is what the caption track is
built from, so the captions cannot drift out of step with the picture.

It also carries the list of shapes the animation uses. That is what makes the rule in
VISUAL-SYSTEM.md mechanical rather than aspirational: a scene that starts drawing something
the visual system has no name for has to say so here first, and saying so fails the check.

And it carries the alt text, for the same reason the captions live here. Alt text written
into a page by hand is alt text that goes stale the first time the animation changes, and
nothing notices, because the one reader who would notice cannot see the picture either.
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

#: Alt text shorter than this is a label rather than a description. "the compiler" tells a
#: reader who cannot see the animation nothing at all about what is in it.
ALT_MINIMUM = 40

#: And past this it is a paragraph. A screen reader reads alt text as one unbroken run with
#: no way to skim or pause, so a long one is worse than a short one.
ALT_LIMIT = 220

#: Openings that spend the reader's first few words saying what they already know from the
#: fact that alt text is being read to them at all.
REDUNDANT = (
    "a gif of",
    "an animation of",
    "an animation showing",
    "an image of",
    "a picture of",
    "a diagram of",
    "this animation",
    "image of",
    "animation of",
)


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

    #: What is on screen, for somebody who is not going to see it. Written as a description
    #: of the picture rather than a summary of the lesson, because the paragraph next to the
    #: animation already does the second one and repeating it helps nobody.
    alt: str = ""

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
        found.extend(self._alt())
        if not self.shapes:
            found.append(f"{self.slug}: say which shapes it draws, so the grammar can be checked")
        for shape in self.shapes:
            if shape not in SHAPES:
                found.append(
                    f"{self.slug}: {shape!r} is not in the visual system; add it to "
                    f"VISUAL-SYSTEM.md and to grammar.py before drawing it"
                )
        return found

    def _alt(self) -> list[str]:
        """Whether the alt text is a description somebody could picture the animation from.

        None of this can tell you the alt text is accurate. It can tell you it is not the
        title again, not two words, and not a paragraph, which is what the three ways of
        writing bad alt text look like.
        """
        found = []
        text = self.alt.strip()
        if not text:
            return [f"{self.slug}: write alt text saying what is on screen"]
        if "\n" in self.alt:
            found.append(f"{self.slug}: the alt text has a line break in it")
        for character, name in FORBIDDEN.items():
            if character in self.alt:
                found.append(f"{self.slug}: the alt text has an {name} in it")
        if text.lower() == self.title.lower():
            found.append(
                f"{self.slug}: the alt text is the title again, and the title is already "
                f"next to the picture; say what is on screen instead"
            )
        if len(text) < ALT_MINIMUM:
            found.append(
                f"{self.slug}: the alt text is {len(text)} characters, which is a label "
                f"rather than a description of what is on screen"
            )
        if len(text) > ALT_LIMIT:
            found.append(
                f"{self.slug}: the alt text is {len(text)} characters, over {ALT_LIMIT}; "
                f"a screen reader reads it as one run with nowhere to pause"
            )
        for opening in REDUNDANT:
            if text.lower().startswith(opening):
                found.append(
                    f"{self.slug}: the alt text starts with {opening!r}, which the reader "
                    f"already knows; start with what is in the picture"
                )
                break
        return found
