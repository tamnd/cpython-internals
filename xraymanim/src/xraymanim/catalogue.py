"""Every animation in the project, described before any of them is drawn.

This is the one list. A scene file in `anim/` imports its storyboard from here rather than
declaring it inline, which buys two things. The plan for all of them is reviewable on one
screen, in order, with the running total of how long the course asks somebody to watch. And
the checks that matter, the ninety second cap and the shapes each one is allowed to draw,
run without manim installed, so they run in every CI job rather than in the one job that
has a renderer.

A scene is free to disagree with its storyboard by accident, so it does not get to: the
base scene counts the beats it played and fails the render if the number is wrong.
"""

from __future__ import annotations

from .storyboard import Beat, Storyboard

SEVEN_STAGES = Storyboard(
    slug="a01-seven-stages",
    title="One line of Python, seven stages",
    lesson="T01",
    shapes=("box", "arrow", "stream", "tree", "slots", "highlight", "CodeStrip"),
    beats=(
        Beat("This is one line of Python. Watch what CPython turns it into.", 4.0),
        Beat("First the text is cut into tokens. That is the whole job of the tokenizer.", 5.0),
        Beat("The parser builds a tree, which is where the shape of the code is decided.", 5.5),
        Beat("The symbol table works out which names are local and which are not.", 5.0),
        Beat("The compiler writes instructions for a machine that has a stack.", 5.0),
        Beat("One more pass drops work nobody is going to need.", 4.5),
        Beat("What survives is packed into a code object. Everything else is thrown away.", 5.5),
        Beat("The interpreter runs the instructions, and that is your answer.", 5.0),
    ),
)

A_NAME_IS_A_LABEL = Storyboard(
    slug="a02-a-name-is-a-label",
    title="A name is a label, not a box",
    lesson="T08",
    shapes=("box", "arrow", "counter", "highlight", "PyObjectBox", "RefArrow"),
    beats=(
        Beat("a = [] makes one list object, and one name pointing at it.", 5.0),
        Beat("The name is not the object. It is a label tied on to it.", 4.5),
        Beat("b = a copies nothing. It ties a second label on to the same object.", 5.5),
        Beat("The object counts its labels. Two labels, so the count reads two.", 5.0),
        Beat("del a takes one label off. The object is still sitting there.", 5.0),
        Beat("The count drops to one, which is not zero, so nothing gets freed.", 4.5),
        Beat("Take the last label off and the count hits zero. Now it is freed.", 5.0),
    ),
)

#: In course order, which is also render order and the order they are listed in anim/README.
ANIMATIONS: tuple[Storyboard, ...] = (
    SEVEN_STAGES,
    A_NAME_IS_A_LABEL,
)


def find(slug: str) -> Storyboard:
    for storyboard in ANIMATIONS:
        if storyboard.slug == slug:
            return storyboard
    known = ", ".join(item.slug for item in ANIMATIONS)
    raise KeyError(f"no animation called {slug!r}; there is {known}")


def module_name(slug: str) -> str:
    """The scene file for a slug. Hyphens read better in a filename and are not identifiers."""
    return slug.replace("-", "_")


def class_name(slug: str) -> str:
    """The scene class inside that file.

    Derived rather than declared, so the slug, the file name, the class name and the GIF
    name cannot drift apart. `a01-seven-stages` is `anim/a01_seven_stages.py` holding
    `class A01SevenStages`, and the checker reads the file to confirm it.
    """
    return "".join(part.capitalize() for part in slug.split("-"))


def seconds() -> float:
    """How long the whole set takes to watch, which is a number worth keeping an eye on."""
    return sum(storyboard.seconds for storyboard in ANIMATIONS)
