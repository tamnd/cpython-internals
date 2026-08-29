# The animations

Short explanations of things that are hard to see in a still picture, because the point of them is that something changes. A refcount going up and down, an instruction pointer walking along a strip of bytecode, a cycle that nothing can reach and nobody can free.

Each one is under ninety seconds, has no sound, and says everything it needs to say in captions burned into the picture, so it works in a page, in a notebook and on a phone with the volume off.

Everything in them is real. The tokens are what `tokenize` returns, the instruction listings are what CPython 3.15.0rc1 actually emits, and where an animation shows a number it was printed by an interpreter rather than typed from memory.

| | Animation | Lesson | Length |
|---|---|---|---|
| a01 | [One line of Python, seven stages](rendered/a01-seven-stages.gif) | T01 | 40s |
| a02 | [A name is a label, not a box](rendered/a02-a-name-is-a-label.gif) | T08 | 34s |
| a03 | [The stack machine](rendered/a03-the-stack-machine.gif) | T07 | 38s |
| a04 | [How a dict finds a key](rendered/a04-how-a-dict-finds-a-key.gif) | T08 | 41s |
| a05 | [A cycle, and what frees it](rendered/a05-a-cycle-and-the-collector.gif) | T09 | 36s |

## a01, one line of Python, seven stages

![the eight artifacts of the compile pipeline, from source text to the number 42](https://raw.githubusercontent.com/tamnd/cpython-internals/main/anim/rendered/a01-seven-stages.gif)

`answer = 6 * 7` goes in, and 42 comes out. In between it is cut into tokens, parsed into a tree, walked once to work out what the name means, compiled into instructions, optimized, and packed into a code object. Watch the multiplication disappear between the fifth stage and the sixth: the compiler did the arithmetic, and your program never multiplies anything.

## a02, a name is a label, not a box

![a list object with two names pointing at it, and its reference count going from one to two to zero](https://raw.githubusercontent.com/tamnd/cpython-internals/main/anim/rendered/a02-a-name-is-a-label.gif)

`a = []`, then `b = a`, then `del a`. Two names, one list, and a count on the object that says how many names are pointing at it. When the count reaches zero the memory goes back. This is the single most useful thing to understand about Python values, and it is much easier to see moving than described.

## a03, the stack machine

![one call to a small function, run one instruction at a time, with the value stack drawn beside it](https://raw.githubusercontent.com/tamnd/cpython-internals/main/anim/rendered/a03-the-stack-machine.gif)

`def area(w): return w * 2 + 1`, called with 6. A disassembly listing tells you what each instruction is called and nothing about what it does to the pile of values underneath, which is the part that is actually hard. So the pile is on screen: seven instructions, the stack going up to two and back down to one twice, and the frame disappearing when the answer is handed back. The instructions and the depths are from `pyxray.stack.walk` on 3.15.0rc1, which is why `LOAD_FAST_BORROW` is there instead of the `LOAD_FAST` you might expect.

## a04, how a dict finds a key

![a dict drawn as an eight slot index array beside three entries, with a lookup that collides and probes again](https://raw.githubusercontent.com/tamnd/cpython-internals/main/anim/rendered/a04-how-a-dict-finds-a-key.gif)

A dict is not one table. Since 3.6 it has been a small array of slot numbers and a separate list of entries in the order you wrote them, and both of the questions people ask about dicts follow from that split: why the order is kept, and what a collision costs. Here `d[9]` lands on slot 1, finds the wrong key, probes again, and finds the right one on the second look. The eight slot array on screen was read out of a live interpreter, and there is a test that reads it again and fails if it ever differs.

## a05, a cycle, and what frees it

![two objects pointing at each other, their counts falling to one and staying there, and the collector taking them](https://raw.githubusercontent.com/tamnd/cpython-internals/main/anim/rendered/a05-a-cycle-and-the-collector.gif)

Reference counting is right nearly all of the time, so the interesting question is when it is not. Two objects that hold each other: take the names away, both counts drop to one, and one is not zero, so nothing is freed and nothing can reach them either. The second half is what the collector does about it, which is smaller than people expect. It copies each count, subtracts one for every reference it finds inside the group, and anything whose copy reaches zero was only ever being kept alive from inside.

## How they are made

Each `aNN_*.py` here is a manim scene built out of the shared library in [xraymanim](../xraymanim), which is what stops a hundred animations from each inventing their own way to draw a pointer. The shapes and what they mean are in [VISUAL-SYSTEM.md](../xraymanim/VISUAL-SYSTEM.md).

```
uv run xraymanim list                          # what exists, and how long it runs
uv run xraymanim check                         # the cheap checks, no renderer needed
uv sync --extra anim                           # install manim
uv run xraymanim render a01-seven-stages       # about a minute
```

The rendered GIFs in [rendered/](rendered) are committed, because a reader on GitHub or in Colab is looking at a page and cannot run a build first. They go through ffmpeg with a generated palette rather than straight out of manim, which is several times smaller for the same picture and is the difference between this repository staying clonable and not.
