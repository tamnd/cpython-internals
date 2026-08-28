#!/usr/bin/env python
"""The diagrams for Z02, being lost productively.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

Every number in here was counted rather than remembered. The commands that produced them
are in the comment above each scene, so anyone can rerun them against a different tag and
see what moved. They are hard coded rather than measured at build time on purpose: a
diagram that quietly redraws itself when somebody adds a citation to an unrelated lesson
would fail `just diagrams` on a pull request that never touched this file.
"""

from nbdiagram import Gallery, figures, stages

gallery = Gallery("z02-being-lost")

gallery.add(
    stages.map(
        "where-we-are",
        highlight=None,
        title="Still before any of this",
        caption="Nothing is highlighted because finding a file is not a stage. It is the other half of the ramp: Z01 was reading nine lines of C, and this one is working out which nine.",
    )
)


# Counted at v3.15.0rc1 with:
#   find <dir> -type f \( -name '*.c' -o -name '*.h' \) -exec cat {} + | wc -l
# and the generated share from the same list, keeping the files whose first three lines
# say "generated" or "do not edit".
gallery.add(
    figures.table(
        "the-tree",
        ["directory", "what is in it", "lines", "written by a script"],
        [
            ["Python", "the compiler and the interpreter loop", "203,839 C", "37%"],
            ["Objects", "one file per built in type", "155,429 C", "13%"],
            ["Include", "the headers, where the structs live", "65,616 C", "33%"],
            ["Parser", "the tokenizer and the parser", "48,130 C", "83%"],
            ["Modules", "the C half of the standard library", "550,440 C", "37%"],
            ["Lib", "the Python half, plus every test", "1,060,700 Python", "a little"],
        ],
        title="Where two million lines actually are",
        caption="Three of these are where the lessons live. Modules is bigger than all of them put together and almost none of it is about how Python works, it is zlib and sqlite and ssl. Lib is bigger again and most of that is tests.",
        tones=["focus", "focus", "focus", "intermediate", "quiet", "quiet"],
    )
)


# Same counts as above, as a share rather than a total.
gallery.add(
    figures.bars(
        "generated-share",
        [
            ("Parser", 83),
            ("Modules", 37),
            ("Python", 37),
            ("Include", 33),
            ("Objects", 13),
            ("the whole tree", 35),
        ],
        unit="percent",
        title="How much of the C nobody typed",
        caption="Of 1,050,298 lines of C and headers, 371,643 are written by a script at build time. Reading one of those is reading the output of a program instead of the program, which is why nothing ever quite makes sense.",
        tones=["warning", "intermediate", "intermediate", "intermediate", "quiet", "durable"],
    )
)


gallery.add(
    figures.compare(
        "two-versions",
        (
            "Python/bytecodes.c, typed by a person",
            [
                "14 lines for BINARY_OP_MULTIPLY_INT",
                "the two operands, the multiply, done",
                "a small language, not quite C",
                "one copy, and it is the real one",
            ],
        ),
        (
            "generated_cases.c.h, typed by a script",
            [
                "about 60 lines for the same thing",
                "plus guards, counters and deopt jumps",
                "real C, and hard to read on purpose",
                "one of three copies, all generated",
            ],
        ),
        title="The same instruction, written twice",
        verdict="Both of these describe what happens when you multiply two ints. Grep finds the long one first, because it is longer and because there are three of them. Reading it teaches you what the code generator does, which is not what you asked.",
        verdict_tone="warning",
    )
)


gallery.add(
    figures.table(
        "where-not-to-look",
        ["if you opened this", "a script wrote it", "read this instead"],
        [
            ["Python/generated_cases.c.h", "Tools/cases_generator", "Python/bytecodes.c"],
            ["Python/executor_cases.c.h", "Tools/cases_generator", "Python/bytecodes.c"],
            ["pycore_opcode_metadata.h", "Tools/cases_generator", "Python/bytecodes.c"],
            ["Lib/_opcode_metadata.py", "Tools/cases_generator", "Python/bytecodes.c"],
            ["Parser/parser.c", "Tools/peg_generator", "Grammar/python.gram"],
            ["Python/Python-ast.c", "Parser/asdl_c.py", "Parser/Python.asdl"],
            ["Objects/clinic/listobject.c.h", "Tools/clinic", "the comment in listobject.c"],
        ],
        title="Seven files to close again",
        caption="These seven are most of the generated lines you will trip over. You do not have to remember them, because every one of them says so in its first three lines, and that is the rule worth keeping.",
        tones=["warning"] * 7,
    )
)


gallery.add(
    figures.table(
        "the-map",
        ["what you want to know", "where it is"],
        [
            [
                "what a built in type is made of",
                "Objects/<type>object.c, and its struct in Include/",
            ],
            ["what one instruction does", "Python/bytecodes.c, and nowhere else"],
            ["how a name gets its scope", "Python/symtable.c"],
            ["what the compiler emits", "Python/codegen.c, then Python/flowgraph.c"],
            ["what runs the bytecode", "Python/ceval.c, which is mostly a wrapper"],
            [
                "what a stdlib module is written in",
                "Lib/<name>.py, plus Modules/_<name>.c if it has one",
            ],
            ["why a line looks like that", "git log -S on the line, then the issue it names"],
        ],
        title="Seven questions and where they are answered",
        caption="This is the whole map for now. InternalDocs/structure.md has the naming rules in more detail, and the lesson checks the stdlib half of it against your own installation rather than asking you to believe it.",
        tones=["quiet"] * 7,
    )
)


gallery.add(
    figures.flow(
        "the-trail",
        [
            "a line of C that makes no sense",
            "git log -S on that line",
            "the commit, and its gh-NNNNN",
            "the pull request, and its review",
            "the issue, and the argument about it",
        ],
        title="How to find out why a line is there",
        tones=["input", "intermediate", "intermediate", "intermediate", "durable"],
        labels=[
            "search the history for the text",
            "the subject line carries the number",
            "the number opens either one",
            "and the issue is where the reasons are",
        ],
    )
)


gallery.add(
    figures.table(
        "internaldocs",
        ["if you want", "InternalDocs has"],
        [
            ["the parser", "parser.md, and changing_grammar.md"],
            ["the compiler", "compiler.md"],
            ["the interpreter loop", "interpreter.md, and stackrefs.md"],
            ["frames and code objects", "frames.md, and code_objects.md"],
            ["the cycle collector", "garbage_collector.md"],
            ["the JIT", "jit.md"],
            ["the tokenizer", "nothing, so read Parser/lexer/ instead"],
            ["the symbol table", "nothing, so read Python/symtable.c instead"],
            ["dicts, lists and ints", "nothing, so read Objects/ instead"],
            ["the memory allocator", "nothing, so read Objects/obmalloc.c instead"],
        ],
        title="Eighteen files of documentation, and where they stop",
        caption="InternalDocs is written by the people who maintain the code and it is the best thing in the tree. It also covers about half of what this course covers, and knowing which half saves you an hour of looking for a page that was never written.",
        tones=["durable"] * 6 + ["warning"] * 4,
    )
)


# Counted from citations.lock.json on 2026-08-29, at 11 lessons and 99 citations:
#   jq -r '.citations | keys[] | split(":")[0]' citations.lock.json | sort -u
gallery.add(
    figures.bars(
        "forty-four-files",
        [
            ("Include", 13),
            ("Python", 12),
            ("Parser", 7),
            ("Objects", 6),
            ("InternalDocs", 4),
            ("Grammar", 1),
            ("Lib", 1),
        ],
        title="Every file the first eleven lessons opened",
        caption="Forty four files, out of the 1,154 C and header files in the tree. Ninety nine separate citations, and they land on forty four files, because the same few files answer nearly every question worth asking.",
        tones=["durable", "durable", "intermediate", "intermediate", "quiet", "quiet", "quiet"],
    )
)


raise SystemExit(gallery.save())
