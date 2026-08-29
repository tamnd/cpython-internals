"""Every animation in the project, described before any of them is drawn.

This is the one list. A scene file in `anim/` imports its storyboard from here rather than
declaring it inline, which buys two things. The plan for all of them is reviewable on one
screen, in order, with the running total of how long the course asks somebody to watch. And
the checks that matter, the ninety second cap and the shapes each one is allowed to draw,
run without manim installed, so they run in every CI job rather than in the one job that
has a renderer.

A scene is free to disagree with its storyboard by accident, so it does not get to: the
base scene counts the beats it played and fails the render if the number is wrong.

The alt text is here too rather than in the page that shows the GIF. It is the one piece
of writing about an animation that nobody proofreads, because everybody who reviews the
page can see the picture, so it is the piece most worth keeping next to the plan it
describes and checking on every run.
"""

from __future__ import annotations

from .storyboard import Beat, Storyboard

SEVEN_STAGES = Storyboard(
    slug="a01-seven-stages",
    title="One line of Python, seven stages",
    lesson="T01",
    alt="the eight artifacts of the compile pipeline, from source text to the number 42",
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
    alt=(
        "a list object with two names pointing at it, and its reference count going from one to "
        "two to zero"
    ),
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

THE_STACK_MACHINE = Storyboard(
    slug="a03-the-stack-machine",
    title="The stack machine",
    lesson="T07",
    alt=(
        "one call to a small function, run one instruction at a time, with the value stack drawn "
        "beside it"
    ),
    shapes=("box", "column", "slots", "highlight", "Frame", "CodeStrip"),
    beats=(
        Beat("Calling area(6) makes a frame. The argument goes in a slot.", 5.0),
        Beat("RESUME is where the interpreter checks whether anything wants a turn.", 4.5),
        Beat("Now w goes on the stack. Nothing is copied, only pointed at.", 5.0),
        Beat("A 2 goes on top of it. That 2 was written down when the code compiled.", 5.0),
        Beat("BINARY_OP takes two off, multiplies them, and puts one back.", 5.0),
        Beat("Another small integer, and the stack is two deep again.", 4.5),
        Beat("The second BINARY_OP adds them, and one value is left.", 4.5),
        Beat("RETURN_VALUE hands it back, and the frame is gone.", 4.5),
    ),
)

HOW_A_DICT_FINDS_A_KEY = Storyboard(
    slug="a04-how-a-dict-finds-a-key",
    title="How a dict finds a key",
    lesson="T08",
    alt=(
        "a dict drawn as an eight slot index array beside three entries, with a lookup that "
        "collides and probes again"
    ),
    shapes=("box", "arrow", "slots", "highlight", "DictTable"),
    beats=(
        Beat("Three keys. CPython keeps this as two pieces rather than one table.", 5.0),
        Beat("On the right, the entries, in the order you wrote them.", 4.5),
        Beat("On the left, eight slots. Each one names an entry, or nothing.", 5.0),
        Beat("To find key 9, take its hash and keep the last three bits. Slot 1.", 5.5),
        Beat("Slot 1 points at entry 0, whose key is 1. Not the key we asked for.", 5.5),
        Beat("So it tries again, by a rule that reaches every slot eventually.", 5.0),
        Beat("Slot 6 points at entry 2, and that key is 9. Found, in two looks.", 5.5),
        Beat("Two keys wanted slot 1 and both still fit. That is all a collision is.", 5.0),
    ),
)

A_CYCLE_AND_THE_COLLECTOR = Storyboard(
    slug="a05-a-cycle-and-the-collector",
    title="A cycle, and what frees it",
    lesson="T09",
    alt=(
        "two objects pointing at each other, their counts falling to one and staying there, and "
        "the collector taking them"
    ),
    shapes=(
        "box",
        "arrow",
        "graph",
        "counter",
        "highlight",
        "PyObjectBox",
        "RefArrow",
        "ArenaMap",
    ),
    beats=(
        Beat("Two objects, and each one is pointing at the other.", 4.5),
        Beat("Each count is two: one from the name, one from the other object.", 5.0),
        Beat("del a and del b take the names away. The objects still point at each other.", 5.5),
        Beat("Both counts drop to one. One is not zero, so neither gets freed.", 5.0),
        Beat("The collector copies the counts, then looks at every arrow inside.", 5.0),
        Beat("It subtracts one per arrow. Both copies reach zero.", 5.0),
        Beat("Zero means nothing outside is pointing in, so the whole group goes.", 5.5),
    ),
)

#: In course order, which is also render order and the order they are listed in anim/README.
ANIMATIONS: tuple[Storyboard, ...] = (
    SEVEN_STAGES,
    A_NAME_IS_A_LABEL,
    THE_STACK_MACHINE,
    HOW_A_DICT_FINDS_A_KEY,
    A_CYCLE_AND_THE_COLLECTOR,
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
