#!/usr/bin/env python
"""The diagrams for T10, the napkin.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

`the-napkin` is the one that matters and it is the reference diagram for the whole project.
Every later lesson is an expansion of one box in it, so it is drawn once, here, and pointed
at from everywhere else rather than redrawn slightly differently each time.
"""

from nbdiagram import Gallery, figures, stages
from nbdiagram.scene import Scene
from pyxray import theme

gallery = Gallery("t10-the-napkin")

gallery.add(
    stages.map(
        "where-we-are",
        highlight=list(range(len(stages.STAGES))),
        title="All of it, which is the point of this lesson",
        caption="Nine lessons, one box each. This one is about the arrows between them and about which box you would put a new question in.",
    )
)


def _row(scene, panel_label, tone, top, cells, *, width, pitch, extra=0):
    """One band of the napkin: a titled panel with a row of boxes and a caption under each.

    The panel has to be drawn before the boxes, since SVG has no z-index and a container
    drawn last paints over its own contents. That means its height is worked out from the
    box height rather than measured afterwards, which is why every label here is short
    enough to sit on one line and the explaining is done by the caption underneath.
    """
    box_height = 64
    caption_height = theme.CAPTION_SIZE * theme.LINE_HEIGHT
    row = top + 2 * theme.GRID + 6
    height = 2 * theme.GRID + 6 + box_height + 6 + caption_height + theme.GRID + extra
    scene.panel(
        panel_label, 0, top, theme.PADDING * 2 + (len(cells) - 1) * pitch + width, height, tone=tone
    )

    boxes = []
    for index, (label, note, box_tone) in enumerate(cells):
        x = theme.PADDING + index * pitch
        boxes.append(
            scene.box(
                label,
                x,
                row,
                width=width,
                height=box_height,
                tone=box_tone,
                size=theme.CAPTION_SIZE,
            )
        )
        scene.text(
            note,
            x + 4,
            row + box_height + 6,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
        )
    return boxes, row, box_height, height


def _the_napkin() -> Scene:
    """The whole machine on one page. This is the reference the reader checks against."""
    scene = Scene("the-napkin")
    width = 150
    pitch = width + 26

    scene.text("The whole machine on one page", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    boxes, _, _, compile_height = _row(
        scene,
        "compile time, once per source file",
        "intermediate",
        top,
        [
            ("your file", "the text", "quiet"),
            ("tokens", "lexer.c", "quiet"),
            ("syntax tree", "parser.c", "quiet"),
            ("symbol table", "symtable.c", "quiet"),
            ("instructions", "codegen.c", "quiet"),
            ("optimized", "flowgraph.c", "quiet"),
            ("code object", "codeobject.c", "focus"),
        ],
        width=width,
        pitch=pitch,
    )
    for index in range(len(boxes) - 1):
        scene.arrow(boxes[index], boxes[index + 1])

    run_top = top + compile_height + 3 * theme.GRID
    ring, ring_row, box_height, run_height = _row(
        scene,
        "run time, every instruction of every call",
        "focus",
        run_top,
        [
            ("read", "two bytes", "quiet"),
            ("dispatch", "opcode to handler", "quiet"),
            ("execute", "bytecodes.c", "quiet"),
            ("advance", "check signals", "quiet"),
        ],
        width=width,
        pitch=pitch,
        extra=44,
    )
    for index in range(len(ring) - 1):
        scene.arrow(ring[index], ring[index + 1])

    # The return leg goes round the outside rather than straight back under the boxes,
    # because the direct route crosses the caption under every one of them.
    lane = ring_row + box_height + theme.CAPTION_SIZE * theme.LINE_HEIGHT + 26
    middle = ring_row + box_height / 2
    right = theme.PADDING + (len(ring) - 1) * pitch + width + 8
    left = 6.0
    first = theme.PADDING + width / 2
    # theme.LINE is the default and it is far too quiet for a route this long, so both of
    # the hand routed legs below are drawn in ink to read as connections rather than rules.
    scene.line([(right, middle), (right, lane), (left, lane), (left, middle)], colour=theme.INK)
    scene.arrow((left, middle), ring[0], sides=("left", "left"))
    scene.text(
        "and again, until the function returns",
        first,
        lane + 6,
        size=theme.CAPTION_SIZE,
        colour=theme.MUTED,
    )

    cross = run_top - theme.GRID - 8
    code_middle = theme.PADDING + 6 * pitch + width / 2
    scene.line(
        [(code_middle, top + compile_height), (code_middle, cross), (first, cross)],
        colour=theme.INK,
    )
    scene.arrow((first, cross), (first, run_top))
    scene.text(
        "the code object is the only thing that crosses",
        first + 40,
        cross - theme.CAPTION_SIZE * theme.LINE_HEIGHT - 2,
        size=theme.CAPTION_SIZE,
        colour=theme.MUTED,
    )

    under_top = run_top + run_height + 3 * theme.GRID
    _row(
        scene,
        "underneath all of it, at every arrow above",
        "durable",
        under_top,
        [
            ("PyObject", "no exceptions", "durable"),
            ("ob_refcnt", "who holds it", "durable"),
            ("ob_type", "what it can do", "durable"),
            ("zero", "freed on the spot", "warning"),
            ("a cycle", "collector frees it", "warning"),
        ],
        width=width,
        pitch=pitch,
    )

    bottom = max(element.box[3] for element in scene.elements)
    for line, words in enumerate(
        [
            "Everything in the first nine lessons is somewhere on this page. The top row happens once and",
            "produces a code object. The middle row happens millions of times and produces nothing except",
            "effects. The bottom row is the same two fields in front of every value the other two rows touch.",
        ]
    ):
        scene.text(
            words,
            0,
            bottom + theme.GRID + line * theme.CAPTION_SIZE * theme.LINE_HEIGHT,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
        )
    return scene


gallery.add(_the_napkin())


gallery.add(
    figures.compare(
        "the-boundary",
        (
            "compile time",
            [
                "runs once, when the file is imported",
                "sees the whole function at once",
                "knows every name and where it lives",
                "produces a code object and stops",
            ],
        ),
        (
            "run time",
            [
                "runs every call, every loop turn",
                "sees one instruction at a time",
                "looks names up in dicts it is handed",
                "produces effects and a return value",
            ],
        ),
        title="Two halves, and the one thing that crosses between them",
        verdict="A code object is the whole output of the left column and the whole input of the right one. Everything the compiler learned that did not fit in it is gone.",
        verdict_tone="durable",
    )
)


gallery.add(
    figures.table(
        "what-you-can-print",
        ["stage", "the call that shows it", "what you get back"],
        [
            ["tokens", "tokenize.generate_tokens", "type, text, and where it started"],
            ["syntax tree", "ast.parse", "nested nodes with line numbers"],
            ["symbol table", "symtable.symtable", "one decision per name per block"],
            ["instructions", "compiler.stages().codegen", "the codegen output, before cleanup"],
            ["optimized", "compiler.stages().optimized", "the same list after flowgraph.c"],
            ["code object", "compile", "consts, names, varnames and the bytes"],
            ["the run", "pyxray.stepper.run", "every instruction, in execution order"],
        ],
        title="Seven stages you can print, with nothing but the standard library",
        caption="This is the argument the whole project rests on. None of this needs a debug build, a C compiler, or a patched interpreter.",
        tones=["quiet"] * 7,
    )
)


gallery.add(
    figures.table(
        "wrong-models",
        ["what people say", "what is actually true"],
        [
            ["Python is interpreted, not compiled", "it is compiled, to bytecode, every time"],
            [
                "the .pyc file is the compiler's output",
                "it is a cache of it, and skipping it changes nothing",
            ],
            ["257 is 257 is False", "it is True, and not for the reason you were told"],
            ["names are looked up in a dict", "locals are array slots, decided at compile time"],
            ["the GC frees your objects", "counting frees almost all of them, immediately"],
            ["del frees the object", "it removes one name, and nothing else"],
            [
                "freeing memory shrinks the process",
                "the arena stays until every pool in it is empty",
            ],
        ],
        title="Seven things that are nearly right",
        caption="Each of these is a sentence you will have read somewhere. Each one is wrong in a way that changes what you predict.",
        tones=["warning"] * 7,
    )
)


gallery.add(
    figures.nest(
        "what-comes-next",
        (
            "the napkin",
            [
                ("the front end", ["the real PEG parser", "error messages", "f-strings"]),
                ("the compiler", ["the flow graph", "what the optimizer will and will not do"]),
                ("the interpreter", ["specialization", "tier 2", "the JIT"]),
                ("objects", ["types and slots", "dicts and their layouts", "attribute lookup"]),
                ("the runtime", ["import", "startup", "the C API"]),
                ("concurrency", ["the GIL", "free threading", "subinterpreters"]),
            ],
        ),
        title="Where the rest of this goes",
        caption="Every later part opens one box on the napkin. Nothing after this introduces a stage the map does not already have.",
    )
)


gallery.add(
    figures.pipeline(
        "one-line-all-the-way",
        [
            ("answer = 6 * 7", "1 line of text"),
            ("NAME OP NUMBER", "8 tokens"),
            ("Assign(BinOp)", "8 nodes"),
            ("answer: global", "1 name"),
            ("BINARY_OP 5", "8 instructions"),
            ("LOAD_SMALL_INT 42", "5 instructions"),
            ("co_consts (6,)", "the leftover"),
            ("answer == 42", "the effect"),
        ],
        title="One line, end to end, with the real artefact at every box",
        caption="The multiplication is gone by the sixth box, so nothing at run time ever does the sum. The 6 is still sitting in co_consts because codegen put it there before the optimizer folded it away, and nobody goes back to tidy up.",
    )
)


gallery.add(
    figures.table(
        "the-checklist",
        ["if your napkin is missing this", "go back to"],
        [
            ["the order of the seven stages", "T01"],
            ["that indentation becomes tokens", "T02"],
            ["that the tree has line numbers on it", "T03"],
            ["that scope is decided before any code runs", "T04"],
            ["that the compiler folds constants", "T05"],
            ["what the argument byte of an instruction means", "T06"],
            ["that the loop reads, dispatches, runs, repeats", "T07"],
            ["the two fields in front of every value", "T08"],
            ["that a cycle needs the collector", "T09"],
        ],
        title="What your drawing should have on it",
        caption="Nine rows, one per lesson. A gap here is not a failure, it is the lesson to reread.",
        tones=["quiet"] * 9,
    )
)


raise SystemExit(gallery.save())
