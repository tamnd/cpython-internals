#!/usr/bin/env python
"""O07. Two arrays and a hash.

The seventh lesson of the object model part. Six lessons have now said "look in the instance
dict" or "look in the class dict" as if that were one simple step. This one opens the dict.

The shape is a small array of slot numbers sitting in front of a plain append only array of
entries. That split is where insertion order comes from, why deleting frees nothing, why a
dict of strings is smaller than a dict of ints, and why the table resizes at 6, 11, 22, 43 and
86 keys rather than at round numbers.

The lesson builds the whole thing in Python, in about sixty lines, and checks that it grows at
exactly the same key counts as the real one and produces exactly the same iteration order.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("o07-two-arrays-and-a-hash", "o07")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("o07-two-arrays-and-a-hash").figure


lesson.md(f"""
# O07. Two arrays and a hash

{badge}

Six lessons have said "look in the instance dict" or "walk the class dicts" and moved on. Time to open one.

A dict is not one table. It is two arrays. A small one holding slot numbers, and a plain append only one holding the actual rows.

{figure("two-arrays-not-one", "the index array with holes, and the entry array without any")}

Only the small array has holes in it. The entry array is filled front to back and never reordered, which is where insertion order comes from and why it costs nothing.

This lesson builds the whole structure in Python and checks it against the real one, key by key.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Objects/dictobject.c:1078-1101@v3.15.0rc1#do_lookup`.

Read it as three parts: the file, the lines, and the release those line numbers belong to. Sometimes there is a fourth part after a `#`, which is the name of the thing those lines are inside.

Every reference is a link, and every one is checked against the pinned source on each change, so a stale reference fails the build instead of sending you somewhere wrong. You never have to read any of it. The references are there so you can go deeper when you want to, and so you can check that this lesson is not making things up.

## Setup

Colab does not come with the small package these lessons use, so the next cell installs it. If you are running this from a checkout of the repository it is already installed and the cell does nothing.
""")


lesson.code("""
import sys

if sys.version_info < (3, 14):
    print("This lesson needs CPython 3.14 or newer.")
    print(f"This runtime is {sys.version.split()[0]}, and the cells below will not run on it.")
else:
    try:
        import pyxray
    except ImportError:
        %pip install -q "pyxray @ git+https://github.com/tamnd/cpython-internals@main#subdirectory=pyxray"
        import pyxray
""")


lesson.md("""
## Which Python is this

Everything below was checked against the version this cell prints and against 3.14. The two agree on every line of output in this lesson, though a few of the byte counts depend on whether pointers are 8 bytes or 4.
""")


lesson.code(
    """
import pyxray

pyxray.show()
""",
    differs=BANNER,
    quiet=True,
)


lesson.md(f"""
## Two arrays, not one

The struct is `PyDictKeysObject`, {cite("Include/internal/pycore_dict.h:196-235@v3.15.0rc1#_dictkeysobject")}. Strip the free threading bits and the version counter and what is left is a size, two counters, and one flexible array member called `dk_indices`. The entry array follows it in the same allocation.

`dk_indices` has one slot per table position. Each slot holds a row number into the entry array, or `-1` for a position that has never been used, or `-2` for one that used to hold something. Those two constants are `DKIX_EMPTY` and `DKIX_DUMMY`, {cite("Include/internal/pycore_dict.h:184-185@v3.15.0rc1#DKIX_DUMMY")}, and the four states a slot can be in are written out in the source, {cite("Objects/dictobject.c:66-89@v3.15.0rc1")}.

The entry array is where the real data lives, in insertion order, appended to and never shuffled. Iterating a dict reads that array top to bottom and skips the cleared rows. There is no ordering machinery anywhere, {cite("Objects/dictobject.c:91-106@v3.15.0rc1")}. The order is a side effect of the layout.

A slot number is small, so `dk_indices` uses the narrowest integer it can: one byte per slot while the table has 128 slots or fewer, then two, then four, {cite("Objects/dictobject.c:37-49@v3.15.0rc1")}. A dict with five keys spends eight bytes on its index array.
""")


lesson.md(f"""
## Where a key lands

Take the hash, keep the low bits, and that is the slot to look at first.

{figure("where-a-key-lands", "the first probe, which is usually the only one")}

For a table with eight slots the mask is 7, so the slot is `hash & 7`. Read `dk_indices[slot]`. A `-1` there means the key is not in the dict and the lookup is over, which is what makes a failed lookup as cheap as a successful one. A row number means something is there, and it might be your key or it might be a collision, so the entry gets compared.

On a collision the search moves on, and the step it takes is the interesting part, {cite("Objects/dictobject.c:360-398@v3.15.0rc1")}.

{figure("the-probe-recurrence", "the three lines that pick the next slot")}

`perturb` starts as the whole hash, and each round shifts it right by 5, {cite("Objects/dictobject.c:329@v3.15.0rc1#PERTURB_SHIFT")}. The next slot is `mask & (i * 5 + perturb + 1)`. Two things are going on. The `i * 5 + 1` part on its own visits every slot in the table exactly once, in an order that is deliberately not the order consecutive keys arrive in. Adding `perturb` pulls in the high bits of the hash that the mask threw away, so two keys that start in the same slot almost immediately diverge.

The loop is {cite("Objects/dictobject.c:1078-1101@v3.15.0rc1#do_lookup")}, and it is written out twice in a row inside the `for`, unrolled by hand.

{lesson.claim("the probe order for a size 8 table starting at slot 0 is 0, 1, 6, 7, 4, 5, 2, 3, which visits every slot exactly once before repeating")}
""")


lesson.code("""
def probe_order(hash_value, log2_size):
    \"\"\"The same three lines as do_lookup, as a generator of slot numbers.\"\"\"
    mask = (1 << log2_size) - 1
    perturb = hash_value % (1 << sys.hash_info.width)
    i = hash_value & mask
    while True:
        yield i
        perturb >>= 5
        i = mask & (i * 5 + perturb + 1)


walk = probe_order(0, 3)
first_nine = [next(walk) for _ in range(9)]
print(f"  starting from a hash of 0  {first_nine}")
print(f"  every slot exactly once    {sorted(first_nine[:8]) == list(range(8))}")
print(f"  and then it wraps          {first_nine[8] == first_nine[0]}")
""")


lesson.md(f"""
That order, `0, 1, 6, 7, 4, 5, 2, 3`, is written out in the source comment too. It matters that it is not `0, 1, 2, 3`. Consecutive integers hash to consecutive values, so linear probing would make every one of them walk over its neighbours. Jumping by five is unlikely to line up with anything real.

## Building the whole thing

Here is the structure, in Python. Two arrays, the probe loop above for lookups, a second probe loop that stops at the first free slot for inserts, and one resize rule.

The resize rule is two macros. A table is never allowed past two thirds full, {cite("Objects/dictobject.c:581@v3.15.0rc1#USABLE_FRACTION")}, and when it fills, the new size is the smallest power of two that fits three times the number of live keys, {cite("Objects/dictobject.c:618-628@v3.15.0rc1#GROWTH_RATE")} and {cite("Objects/dictobject.c:584-604@v3.15.0rc1#calculate_log2_keysize")}. Three times rather than two so that a dict which is being deleted from as much as inserted into still has room.

{lesson.claim("a dict grows when its entry array is full rather than when its length crosses a threshold, so the resize points fall at 6, 11, 22, 43 and 86 keys")}
""")


lesson.code("""
EMPTY = -1
DUMMY = -2


def usable(size):
    \"\"\"USABLE_FRACTION: how many entries a table of this size may hold.\"\"\"
    return (size * 2) // 3


def new_log2_size(live_keys):
    \"\"\"GROWTH_RATE fed into calculate_log2_keysize: room for three times the live keys.\"\"\"
    return (max(live_keys * 3, 8) - 1).bit_length()


class Compact:
    \"\"\"A dict, in the same shape CPython uses. Enough of one to compare against.\"\"\"

    def __init__(self):
        self.indices = [EMPTY] * 8
        self.entries = []
        self.used = 0

    def _lookup(self, key, key_hash):
        for slot in probe_order(key_hash, len(self.indices).bit_length() - 1):
            row = self.indices[slot]
            if row == EMPTY:
                return slot, EMPTY
            if row >= 0:
                stored_hash, stored_key, _ = self.entries[row]
                if stored_hash == key_hash and (stored_key is key or stored_key == key):
                    return slot, row
        raise AssertionError("the probe order always finds an empty slot")

    def _free_slot(self, key_hash):
        for slot in probe_order(key_hash, len(self.indices).bit_length() - 1):
            if self.indices[slot] < 0:
                return slot
        raise AssertionError("the probe order always finds an empty slot")

    def _resize(self, log2_size):
        self.entries = [row for row in self.entries if row is not None]
        self.indices = [EMPTY] * (1 << log2_size)
        for row, (stored_hash, _, _) in enumerate(self.entries):
            self.indices[self._free_slot(stored_hash)] = row

    def __setitem__(self, key, value):
        key_hash = hash(key)
        slot, row = self._lookup(key, key_hash)
        if row >= 0:
            stored_hash, stored_key, _ = self.entries[row]
            self.entries[row] = (stored_hash, stored_key, value)
            return
        if usable(len(self.indices)) - len(self.entries) <= 0:
            self._resize(new_log2_size(self.used))
            slot = self._free_slot(key_hash)
        self.indices[slot] = len(self.entries)
        self.entries.append((key_hash, key, value))
        self.used += 1

    def __delitem__(self, key):
        slot, row = self._lookup(key, hash(key))
        if row < 0:
            raise KeyError(key)
        self.indices[slot] = DUMMY
        self.entries[row] = None
        self.used -= 1

    def __iter__(self):
        return (row[1] for row in self.entries if row is not None)

    def size(self):
        return len(self.indices)
""")


lesson.md("""
Sixty lines, and it should behave like the real thing. The test is not that it looks right, it is that it grows at the same moments and iterates in the same order.
""")


lesson.code("""
mine, real = Compact(), {}
mine_grew, real_grew = [], []
mine_size, real_size = mine.size(), sys.getsizeof(real)

for n in range(1, 200):
    key = f"k{n}"
    mine[key] = n
    real[key] = n
    if mine.size() != mine_size:
        mine_grew.append(n)
        mine_size = mine.size()
    if sys.getsizeof(real) != real_size:
        real_grew.append(n)
        real_size = sys.getsizeof(real)

print(f"  my table grew at    {mine_grew}")
print(f"  the real one at     {real_grew}")
print(f"  same iteration order  {list(mine) == list(real)}")
""")


lesson.md(f"""
Same growth points and the same order over two hundred keys.

The real dict has one extra entry in its list, the very first key. An empty dict does not own a keys object at all. It points at a single shared immortal one with no room in it, {cite("Objects/dictobject.c:630-640@v3.15.0rc1#empty_keys_struct")}, so the first insert has to allocate. After that the two agree exactly.

Now delete a few keys and add one, which is the case where a design that moved entries around would fall apart.
""")


lesson.code("""
for key in ["k3", "k17", "k50"]:
    del mine[key]
    del real[key]

mine["late"] = 0
real["late"] = 0

print(f"  same order after deletes  {list(mine) == list(real)}")
print(f"  first six keys            {list(mine)[:6]}")
print(f"  last key                  {list(mine)[-1]}")
""")


lesson.md(f"""
## Deleting leaves a mark

Look at what `__delitem__` did. It wrote `-2` into the index slot and cleared the entry row. It did not shrink either array, and it did not move anything.

{figure("delete-leaves-a-mark", "what a delete changes and what it deliberately does not")}

The dummy has to be there. A `-1` means "stop looking", so turning a deleted slot back into `-1` would cut off the probe sequence for any key that had collided with it and been pushed further along. The C does exactly the same two writes, {cite("Objects/dictobject.c:2904-2941@v3.15.0rc1#delitem_common")}.

The entry row is a different matter. Its space is gone until the next resize, and the resize counter never gets it back. So a dict you delete from and insert into in a loop keeps growing even though its length never changes.

{lesson.claim("a dict that is deleted from and inserted into in equal measure still resizes, because the entry array only ever gets compacted by a resize")}
""")


lesson.code(
    """
churn = {}
for n in range(5):
    churn[f"k{n}"] = n

print(f"  five keys        {sys.getsizeof(churn):4} bytes")

for n in range(5, 10):
    del churn[f"k{n - 5}"]
    churn[f"k{n}"] = n

print(f"  after five swaps {sys.getsizeof(churn):4} bytes, still {len(churn)} keys")
print(f"  and in order     {list(churn)}")
""",
    varies="These are byte counts, so they halve on a 32 bit build, which is what a browser "
    "gives you. The dict growing while its length stays at five is the part to read.",
)


lesson.md("""
Five keys in, five out, five in. The length never went above five and the dict is a size class larger than it started. That is the reason `dict.clear()` exists as something other than a loop, and the reason a long lived dict used as a cache is worth rebuilding now and then.

`popitem()` is the one delete that does give the space back, because it always takes the last row of the entry array and can just decrement the counter.
""")


lesson.code("""
d = dict.fromkeys("abcde")
print(f"  popitem  {d.popitem()}")
print(f"  popitem  {d.popitem()}")
print(f"  left     {list(d)}")
""")


lesson.md(f"""
## Two kinds of entry

There are two entry layouts, {cite("Include/internal/pycore_dict.h:79-90@v3.15.0rc1#PyDictKeyEntry")}. The general one holds a hash, a key and a value. The unicode one holds a key and a value, and no hash.

{figure("two-kinds-of-entry", "the two entry layouts and when each one is used")}

Dropping the hash is safe when every key is an exact `str`, because a string caches its own hash inside the string object. Storing it again in the entry would be a redundant word per row. So a dict whose keys are all strings uses two words per row instead of three.

Almost every dict in a running program is that kind. Instance dicts, class dicts, module globals and keyword arguments all have string keys.

{lesson.claim("a dict with only exact str keys uses a smaller entry layout, and putting one non string key in converts the whole table to the larger one")}
""")


lesson.code(
    """
strings = {"a": 1, "b": 2}
numbers = {1: "a", 2: "b"}
print(f"  two string keys  {sys.getsizeof(strings)} bytes")
print(f"  two int keys     {sys.getsizeof(numbers)} bytes")

strings[1] = "and now a number"
print(f"  after adding one int key to the string dict  {sys.getsizeof(strings)} bytes")
""",
    varies="Byte counts again, so a 32 bit build halves them. The string keyed dict being the "
    "smaller of the two, and jumping when a non string key arrives, holds everywhere.",
)


lesson.md(f"""
The conversion happens inside the resize, {cite("Objects/dictobject.c:2141-2175@v3.15.0rc1#dictresize")}, which takes a flag saying whether the new table can stay unicode and clears it if the old one was already general.

## Asking for the space up front

One last piece. If you know how many keys are coming, there is a reverse of `USABLE_FRACTION` that works out the table size needed to hold them without any resizing, {cite("Objects/dictobject.c:606-615@v3.15.0rc1#estimate_log2_keysize")}.

`dict.fromkeys` on something with a known length uses it. Building the same dict a key at a time does not, and goes through every intermediate size on the way. The end result is the same size either way, because the growth rule lands on the same power of two. What differs is the work in between.
""")


lesson.code(
    """
presized = dict.fromkeys(range(1000))

built = {}
for n in range(1000):
    built[n] = None

print(f"  presized  {sys.getsizeof(presized)} bytes")
print(f"  built up  {sys.getsizeof(built)} bytes")
print(f"  same size {sys.getsizeof(presized) == sys.getsizeof(built)}")
print("  but the second one allocated and rehashed its way through eight smaller tables")
""",
    varies="The two byte counts are smaller on a 32 bit build. That they match each other is "
    "the point, and that holds everywhere.",
)


lesson.md("""
## Try it yourself

Three things to poke at.

Give `Compact` a `__getitem__` that counts how many slots the probe loop visited, then fill it with a thousand keys and take the average. It should be close to one. Then swap `probe_order` for plain linear probing, `i = (i + 1) & mask`, fill it with `range(1000)` as keys, and watch the average climb.

Make the dummy slots break something. Take out the `DUMMY` write in `__delitem__` and put `EMPTY` there instead. It will pass a simple test and then lose a key, and you will need a collision to see it, so start with keys that share a slot.

Count the resizes. Add a counter to `_resize` and compare building a dict with a loop against `dict.fromkeys` for a few different sizes. The number is small, which is the point of doubling, but it is not zero.

## What just happened

A dict is a small array of slot numbers in front of an append only array of entries. The slot array has the holes. The entry array does not, which is why iteration is in insertion order and why that order costs nothing to maintain.

A lookup masks the hash down to a slot number, reads one small integer, and stops right there if it is `-1`. On a collision it moves on by `i * 5 + perturb + 1`, which visits every slot exactly once and pulls in the high bits of the hash that the mask discarded. For a size 8 table the order is 0, 1, 6, 7, 4, 5, 2, 3.

The table is never more than two thirds full, and when the entry array fills, it is rebuilt at the smallest power of two that fits three times the live keys. That puts the resize points at 6, 11, 22, 43 and 86 rather than anywhere round. Sixty lines of Python reproduce all of it, including the order after deletes.

Deleting writes a dummy into the slot array so probe sequences stay intact, and clears the entry row without reclaiming it. Delete and insert in equal measure and the dict still grows. `popitem` is the exception, because it takes the last row.

A dict with only exact string keys stores no hashes, because strings cache their own, so its rows are two words instead of three. One non string key converts the whole table at the next resize.

## What is next

O08 is the layout this lesson left out. Every instance of a class tends to have the same attribute names, so the keys array can be shared between all of them and each instance keeps only a bare array of values. That is a split table, it is why `__dict__` looks like a dict but is not always stored as one, and it is most of the reason ordinary Python objects are as small as they are.
""")


raise SystemExit(lesson.save())
