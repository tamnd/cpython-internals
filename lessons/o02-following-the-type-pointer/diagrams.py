#!/usr/bin/env python
"""The diagrams for O02, the type object on the other end of the second word.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `where-the-attributes-live`. A type is mostly a set of answers
to questions the interpreter asks about instances, and the two most surprising answers are
kept in front of the instance rather than inside it.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("o02-following-the-type-pointer")

gallery.add(
    figures.flow(
        "follow-the-second-word",
        [
            "the object 3",
            "its second word points at int",
            "int's second word points at type",
            "type's second word points at type",
        ],
        title="Following the type pointer until it stops going anywhere new",
        labels=[
            "every object has one, no exceptions",
            "a type is an object, so it has one too",
        ],
        tones=["input", "focus", "focus", "durable"],
    )
)


gallery.add(
    figures.table(
        "two-numbers-per-instance",
        ["type", "basicsize", "itemsize", "what that means"],
        [
            ["object", "16", "0", "just the header, nothing after it"],
            ["float", "24", "0", "the header and one double"],
            ["tuple", "32", "8", "header, count, then one pointer each"],
            ["bytes", "33", "1", "header, count, bytes, and a zero byte"],
            ["list", "40", "0", "fixed size, the items are somewhere else"],
            ["type", "944", "40", "the biggest struct in the interpreter"],
        ],
        title="Every type says how big one of its instances is",
        caption="basicsize is the fixed part and itemsize is charged per element, so tuple grows and list does not.",
        tones=["quiet", "quiet", "focus", "quiet", "warning", "focus"],
    )
)


gallery.add(
    figures.compare(
        "static-and-heap",
        (
            "static types, written in C",
            [
                "one PyTypeObject in the binary",
                "int, str, list, type itself",
                "immortal, and you cannot assign",
                "no __dict__ of its own to grow",
            ],
        ),
        (
            "heap types, made while running",
            [
                "malloc'd, one PyHeapTypeObject",
                "anything a class statement makes",
                "counted, collected, and writable",
                "carries the slot structs inline",
            ],
        ),
        title="Two ways a type comes into existence, and one flag tells them apart",
        verdict="Py_TPFLAGS_HEAPTYPE is bit 9, and almost everything else about a type follows from it.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.stack(
        "where-the-attributes-live",
        [
            "minus 32, the weakref list, if the type asked for one",
            "minus 24, the instance dict, if the type asked for one",
            "minus 16, the two words of GC pre header",
            "0, ob_refcnt and ob_flags",
            "8, ob_type, which is where id() points",
            "16 onwards, the inline values array",
        ],
        title="One instance of a plain class, and where its parts actually sit",
        note="Two of the six are at negative offsets, which is why the numbers in tp_dictoffset are negative.",
    )
)


gallery.add(
    figures.table(
        "reading-an-offset",
        ["value of tp_dictoffset", "what the interpreter does"],
        [
            ["0", "instances have no dict at all"],
            ["a positive number", "the dict pointer is that many bytes in"],
            ["a negative number", "count back from the end of a var sized object"],
            ["exactly -1", "not an offset, a flag saying the VM manages it"],
        ],
        title="One field, four meanings, and the last one is a sentinel",
        caption="A class statement gives you -1, so the pointer is at a fixed spot in front of the object instead.",
        tones=["quiet", "quiet", "quiet", "focus"],
    )
)


gallery.add(
    figures.flow(
        "what-a-class-statement-does",
        [
            "LOAD_BUILD_CLASS pushes __build_class__",
            "MAKE_FUNCTION wraps the class body",
            "CALL runs the body and collects its names",
            "type(name, bases, namespace) builds the type",
            "STORE_NAME binds it like any other value",
        ],
        title="There is no class opcode, only a call",
        labels=[
            "a builtin, and you can call it yourself",
            "the body is a function, so it has locals",
            "the metaclass, which is type unless you said otherwise",
            "and the result is an ordinary object",
        ],
        tones=["input", "intermediate", "intermediate", "focus", "durable"],
    )
)


raise SystemExit(gallery.save())
