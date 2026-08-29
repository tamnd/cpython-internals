# The visual system

Every picture in this project is made of fifteen things. Nine shapes, six named objects built out of those shapes, six colours that each mean something, three type sizes, and one grid. That is the whole vocabulary, and the point of writing it down is that it stays the whole vocabulary.

The reason is not tidiness. A reader who works through forty lessons will see several hundred pictures, and every time a picture invents its own notation they have to stop and decode it before they can think about what it says. If a thick arrow always means the same thing, they learn it once in the first animation and read the fortieth for free.

## The rule

A new shape needs an amendment to this document before it is drawn.

That means: add it here with what it means and when to use it, add its name to `PRIMITIVES` or `MOBJECTS` in [grammar.py](src/xraymanim/grammar.py), and then write the function. Not the other way round. `xraymanim check` fails if a shape is drawable and not described here, and a storyboard cannot declare a shape that is not in the grammar, so the three cannot drift apart.

If a scene needs something the system has no name for, that is worth stopping over. Either it belongs here because it will come up again, or the picture is trying to say something the picture should not be saying.

## The nine shapes

| Shape | What it means | When it is wrong |
|---|---|---|
| `box` | Something with a memory address. If it is drawn as a box you could take a pointer to it | A count, an index or a flag. Those are text, not boxes, and the difference is the point |
| `arrow` | A reference from one thing to another. Thick is owned and counted, thin is borrowed and not. It may be curved, which is for the one case a straight line cannot draw: two objects pointing at each other | Anything that is not a pointer. Time, data flow and causation get other treatments |
| `slots` | An array or a table, indexed by number. The cells touch, because they are next to each other in memory | A list of unrelated things that happen to be near each other on the page |
| `column` | A stack, growing upward, in every lesson without exception | Anything that does not push and pop |
| `stream` | Tokens, instructions, bytes: things consumed in order, one at a time, by something with a position | A collection that is looked at all at once. That is `slots` |
| `tree` | The syntax tree, the type hierarchy, anything where a node has one parent | A graph that happens to look like a tree in this example |
| `graph` | The control flow graph, the object graph, anything with cycles. Positions are always given by hand, and which side of a box an edge leaves from follows from them | Nothing, but the layout is never automatic. An automatically placed control flow graph is unreadable |
| `counter` | A reference count, a version tag, anything that goes up and down and is worth watching | A number that never changes. That is a label |
| `highlight` | The thing happening right now. One at a time | Two at once. Two highlights tell the reader to look in two places, which tells them nothing |

## The six named objects

| Object | What it is |
|---|---|
| `PyObjectBox` | Any Python object, drawn with the header it actually has: `ob_type`, `ob_refcnt`, and whatever it holds. The count sits inside the box, because it is a field of the object and not a note beside it |
| `RefArrow` | One reference, with the owning or borrowing weight and a label saying what is doing the pointing |
| `Frame` | One `_PyInterpreterFrame`: a name, the locals as slots, and the value stack on the right growing upward |
| `CodeStrip` | A run of bytecode as a stream, with the instruction pointer as a separate mobject that moves along it |
| `DictTable` | A dict as CPython stores one: a small index array on the left, the entries in insertion order on the right. The slot numbers are written outside the array, because a slot number is a position and not something CPython stores |
| `ArenaMap` | The allocator's memory, one cell per block. Free is an outline with nothing in it, used is filled |

## Colour

Six tones, defined once in [pyxray/theme.py](../pyxray/src/pyxray/theme.py) and read by the Excalidraw diagrams, the matplotlib charts and the animations alike. They are named after the job, not the hue, which is what makes them a grammar rather than a palette.

| Tone | What it marks |
|---|---|
| `input` | What the reader wrote. Everything else in the picture came from this |
| `intermediate` | Something CPython builds and then throws away. Most of the compiler is this |
| `durable` | Something that survives: cached, marshalled, written to disk |
| `focus` | The thing under discussion right now |
| `warning` | An error, a refusal, or something that deliberately does not happen |
| `quiet` | Scaffolding. Captions, groupings, anything that is not the subject |

Colour never carries meaning on its own. A tone always arrives with a label, a position or a shape that says the same thing, so a reader who cannot tell the green from the orange loses nothing.

## Type, spacing and timing

Three type sizes and no more: title, body, caption. Two families, one sans and one monospace, and anything that is source code or an opcode name is monospace without exception.

Everything sits on a grid, in the diagrams as pixels and in the animations as manim units. A picture where nothing quite lines up looks careless even when the reader cannot say why.

A beat is one step of the thing being explained, and it is followed by a hold. The hold is the part that gets cut and should not be: the reader needs time to look at the new state before it moves again.

Ninety seconds is the hard cap on one animation, enforced by `xraymanim check` rather than by anybody's judgement. It is the length past which somebody watching an explanation starts scrubbing, and once they scrub they have stopped following the argument. An animation that needs longer is two animations.
