#!/usr/bin/env python
"""O09. Arrays of thirty bit digits.

The ninth lesson of the object model part, and the first of four about the built in types.

Python integers do not overflow, and this is the lesson about what that costs and how it is
paid for. An int is a sign, a digit count and an array of digits in base 2**30, so it grows
four bytes at a time. Small ones get a fast path, tiny ones are shared and immortal, and big
ones switch multiplication algorithms at exactly 70 digits.

Everything measured here comes from `sys.getsizeof`, identity, and two algorithms written out
in Python and counted rather than timed, so the numbers are the same on every run.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("o09-arrays-of-thirty-bit-digits", "o09")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("o09-arrays-of-thirty-bit-digits").figure


lesson.md(f"""
# O09. Arrays of thirty bit digits

{badge}

Python integers do not overflow. You can raise 2 to the power of a million and get an exact answer, which is not true in C, Go, Rust or Java without reaching for a library.

That has to cost something, and the cost is that an int is not a machine word. It is an array.

{figure("thirty-bit-digits", "how an int grows one digit at a time")}

The digits are in base 2**30, four bytes each, least significant first. A number under 2**30 needs one of them and fits in the space the object already has, which is why 0 and a billion cost the same 28 bytes.

This lesson takes an int apart, puts it back together, finds the exact point where multiplication changes algorithm, and explains the only error message in Python that tells you to raise a limit.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Objects/longobject.c:4070-4090@v3.15.0rc1#k_mul`.

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

Everything below was checked against the version this cell prints and against 3.14. There is one real difference between them, and it is the range of shared integers, which grew in 3.15. The lesson says so where it comes up.
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
## The shape of an int

Four fields, and you have seen two of them already.

{figure("an-int-top-to-bottom", "an int object from top to bottom")}

After the header from O01 comes one machine word called `lv_tag`, and then the digits, {cite("Include/cpython/longintrepr.h:93-101@v3.15.0rc1#_PyLongValue")}. A digit is a `uint32_t` holding 30 bits, {cite("Include/cpython/longintrepr.h:43-47@v3.15.0rc1#PyLong_SHIFT")}, so two bits of every four bytes go unused. That is deliberate: multiplying two 30 bit digits fits in a 64 bit result with room for carries, and the code can add several products before it has to do anything about overflow.

You can see the array from Python without any tools. `sys.getsizeof` grows by four bytes per digit.

{lesson.claim("an int object grows by one fixed size digit at a time, and the size steps exactly at the powers of two that need another digit")}
""")


lesson.code(
    """
DIGIT_BITS = sys.int_info.bits_per_digit
DIGIT_BYTES = sys.int_info.sizeof_digit

print(f"  a digit holds {DIGIT_BITS} bits in {DIGIT_BYTES} bytes")
print()

for value in [0, 1, 2**DIGIT_BITS - 1, 2**DIGIT_BITS, 2 ** (2 * DIGIT_BITS), 2 ** (3 * DIGIT_BITS)]:
    shown = f"2**{value.bit_length() - 1}" if value > 1000 else str(value)
    print(f"  {shown:10} {sys.getsizeof(value):3} bytes")
""",
    varies="In a browser, where Python is a 32 bit WebAssembly build, the object header is "
    "smaller, so every row is 12 bytes lower. A digit is 30 bits in 4 bytes either way, so "
    "the steps land in exactly the same places.",
)


lesson.md(f"""
The number of digits is the only thing that changes. Everything else about the object is the same whether it holds 0 or a googol.

Since the digits are base 2**30, you can pull them out with a mask and a shift, and put them back with a sum. This is the whole storage format, written out.

{lesson.claim("the digits of an int can be extracted with a mask and a shift and summed back into the original number, because that is exactly what the storage format is")}
""")


lesson.code("""
MASK = (1 << DIGIT_BITS) - 1


def digits_of(n):
    \"\"\"The ob_digit array of n, least significant first, the way CPython stores it.\"\"\"
    n = abs(n)
    out = []
    while n:
        out.append(n & MASK)
        n >>= DIGIT_BITS
    return out


def value_of(digits):
    \"\"\"The formula from the comment in longintrepr.h, in one line.\"\"\"
    return sum(digit << (DIGIT_BITS * i) for i, digit in enumerate(digits))


number = 2**100 + 12345
parts = digits_of(number)

print(f"  digits, least significant first  {parts}")
print(f"  how many                         {len(parts)}")
print(f"  every one under the base         {all(d <= MASK for d in parts)}")
print(f"  the top one is never zero        {parts[-1] != 0}")
print(f"  and it adds back up              {value_of(parts) == number}")
""")


packed = lesson.claim(
    "the digit count, the sign and the shared int flag are packed into one machine word "
    "so that a single comparison can decide whether the fast path applies",
    unobservable="lv_tag is not reachable from Python, and pyxray does not read raw struct "
    "fields. What the lesson can show is the consequence: everything below one digit "
    "behaves differently from everything above it.",
)


lesson.md(f"""
Two of those lines are rules the source relies on rather than facts about arithmetic. Every digit stays below the base, and the most significant digit is never zero, {cite("Include/cpython/longintrepr.h:64-91@v3.15.0rc1")}. The second one is why almost every operation ends by calling `long_normalize`, {cite("Objects/longobject.c:126-142@v3.15.0rc1#long_normalize")}, which walks back from the top dropping zeros. Addition allocates room for a carry it usually does not need, and normalizing is how the extra digit goes away again.

## One word holds three things

{term("digit array", "the ob_digit array, base 2**30, least significant first")}

The tag is where the sign lives, and the digit count, and one flag.

{figure("whats-in-the-tag", "the bits of lv_tag for the number 5")}

The low two bits are the sign, encoded as 0 for positive, 1 for zero and 2 for negative. Zero gets its own value rather than being a positive number with no digits, which makes checking for zero one comparison. The third bit marks one of the shared integers. Everything above that is the digit count.

Packing it this way buys one thing, and the source uses it constantly, {cite("Include/cpython/longintrepr.h:121-125@v3.15.0rc1#_PyLong_IsCompact")}:

```c
return op->long_value.lv_tag < (2 << _PyLong_NON_SIZE_BITS);
```

A tag below 16 means the digit count is 0 or 1 and the sign is not negative. So "is this a small non negative integer I can handle without touching the array" is a single unsigned comparison against a constant. When it passes, the value comes out with a multiply and no branches, {cite("Include/cpython/longintrepr.h:129-142@v3.15.0rc1#_PyLong_CompactValue")}.

{packed}

## The ones that were made for you

Some integers you never allocate, because they already exist.

{figure("the-ones-made-for-you", "shared integers against everything else")}

The runtime builds a fixed array of them at startup, {cite("Include/internal/pycore_runtime_structs.h:97-98@v3.15.0rc1#_PY_NSMALLPOSINTS")}, and every operation that produces a result in range hands back the one from the array instead of making a new object, {cite("Objects/longobject.c:251-270@v3.15.0rc1#_PyLong_FromMedium")}. You can find the edges of that range with `is`.

{lesson.claim("integers in a fixed low range are shared objects rather than fresh allocations, so two separate computations that land on the same small value produce the same object")}
""")


lesson.code(
    """
def computed(n):
    \"\"\"Force a real computation, so the result cannot be a constant folded by the compiler.\"\"\"
    return int(str(n))


low = 0
while computed(low - 1) is computed(low - 1):
    low -= 1

high = 0
while computed(high + 1) is computed(high + 1):
    high += 1

print(f"  shared from   {low}")
print(f"  shared up to  {high}")
print(f"  pyxray agrees {pyxray.obj.small_int_range() == (low, high)}")
""",
    differs="On 3.14 the shared range stops at 256, and it goes up to 1024 from 3.15 onward. "
    "This cell finds whichever one you are on, so the second line differs. Nothing else in "
    "the lesson depends on the number.",
)


lesson.md(f"""
The range is not part of the language and it has moved before, so code that relies on `is` for integers is code that will break on somebody else's Python.

Being shared has a second consequence. An object handed out to everybody forever cannot usefully be reference counted, so these are immortal, the same way `None` and `True` were in O01.

{lesson.claim("shared integers are immortal, so their reference count never changes, while an integer outside the range is refcounted normally")}
""")


lesson.code(
    """
for value in [0, 5, 256, 1024, 4096, 10**9]:
    print(f"  {value:12}  immortal {pyxray.obj.is_immortal(value)!s:5}")
""",
    differs="Which values come out immortal follows the shared range, so on 3.14 the 1024 row "
    "says False where it says True here. The 0, 5 and 256 rows are True everywhere, and the "
    "last two are False everywhere.",
)


lesson.md(f"""
## Adding is what you did at school

With the format in hand, addition is not mysterious. Line the digits up, add them column by column, carry when a column goes past the base, {cite("Objects/longobject.c:3746-3775@v3.15.0rc1#x_add")}.

The C is about twenty lines and it is a direct transcription of the method you learned at seven, with base 2**30 instead of base 10. Here it is in Python, checked against the real thing.
""")


lesson.code("""
def add_digits(left, right):
    \"\"\"x_add, line for line: pad to the longer, add with a carry, then normalize.\"\"\"
    if len(left) < len(right):
        left, right = right, left
    out = []
    carry = 0
    for i in range(len(left)):
        carry += left[i] + (right[i] if i < len(right) else 0)
        out.append(carry & MASK)
        carry >>= DIGIT_BITS
    out.append(carry)
    while len(out) > 1 and out[-1] == 0:
        out.pop()
    return out


checks = [(2**100, 2**100), (2**90 - 1, 1), (0, 12345), (7, 2**200)]
for a, b in checks:
    left, right = digits_of(a), digits_of(b)
    mine = value_of(add_digits(left, right))
    shape = f"a {len(left)} digit and a {len(right)} digit number"
    print(f"  matches {mine == a + b}   for {shape}")
""")


lesson.md(f"""
The `while` at the end is `long_normalize`. The append before it is the carry slot that gets dropped again when there was no carry out of the top.

## Multiplying stops being what you did at school

Multiplication is where it gets interesting, because school long multiplication is quadratic. Two numbers of n digits each take n squared digit multiplies, {cite("Objects/longobject.c:3931-3942@v3.15.0rc1#x_mul")}, and for big enough numbers that is too slow.

So above a threshold CPython switches to Karatsuba, {cite("Objects/longobject.c:4070-4090@v3.15.0rc1#k_mul")}. Split each number in half, and where the obvious approach needs four products of half sized numbers, this needs three, because one of them can be recovered by subtraction. Do that recursively and the exponent drops from 2 to about 1.585.

The threshold is a constant and it is 70 digits, {cite("Objects/longobject.c:80-85@v3.15.0rc1#KARATSUBA_CUTOFF")}. Below it the bookkeeping costs more than the multiply it saves.

{figure("two-ways-to-multiply", "digit multiplies for each method at three sizes")}

Rather than time anything, which would give a different answer every run, count the digit multiplies each method performs.

{lesson.claim("the two multiplication algorithms cost the same at the cutoff and diverge above it, which is why the cutoff sits where it does")}
""")


lesson.code("""
CUTOFF = 70


def schoolbook(n, m):
    \"\"\"x_mul: one digit multiply for every pair of digits.\"\"\"
    return n * m


def karatsuba(n, m):
    \"\"\"k_mul: three products on halves, and gradeschool once either side is small.\"\"\"
    if n < m:
        n, m = m, n
    if m <= CUTOFF:
        return schoolbook(n, m)
    half = m >> 1
    return (
        karatsuba(half, half)
        + karatsuba(n - half, m - half)
        + karatsuba(n - half + 1, m - half + 1)
    )


print("  digits   schoolbook   karatsuba   saving")
for size in [70, 140, 280, 560, 1120]:
    slow, fast = schoolbook(size, size), karatsuba(size, size)
    print(f"  {size:6}   {slow:10}   {fast:9}   {slow / fast:.2f}x")
""")


lesson.md(f"""
At exactly 70 digits the two are the same number, because Karatsuba has not kicked in yet. Every size above that, the gap widens.

Note that the fast path for small numbers comes before any of this. If both operands are compact, the whole multiply is one machine multiply and the array code is never reached, {cite("Objects/longobject.c:4340-4354@v3.15.0rc1#long_mul")}.

## The one limit Python puts on integers

Everything above is base 2 in disguise. Digits are 30 bits, shifts are free, and `bin`, `hex` and `oct` are just regrouping bits.

Decimal is not, and it is the odd one out.

{figure("why-str-has-a-limit", "which integer operations are linear and which is not")}

Turning a big int into a decimal string means repeatedly dividing by a power of ten, which is quadratic in the number of digits. A few million digits is enough to hang a process, and since untrusted input reaching `int()` is a very ordinary thing for a web application to do, that was a denial of service waiting to happen. So there is a cap.

It is 4300 digits by default, and it is the only error message in Python that tells you how to raise a limit, {cite("Objects/longobject.c:2128-2134@v3.15.0rc1")}.

{lesson.claim("converting a very long decimal string to an int, or the reverse, raises rather than running, and the limit can be raised at runtime")}
""")


lesson.code("""
print(f"  the default limit  {sys.get_int_max_str_digits()}")

big = 10**5000

try:
    str(big)
except ValueError as error:
    print(f"  going to a string  {str(error)[:60]}")

try:
    int("9" * 5000)
except ValueError as error:
    print(f"  coming from one    {str(error)[:60]}")

print(f"  but hex is fine    {len(hex(big))} characters, no complaint")
print(f"  and so is the size {big.bit_length()} bits")

sys.set_int_max_str_digits(6000)
print(f"  after raising it   {len(str(big))} digits")
sys.set_int_max_str_digits(4300)
""")


lesson.md(f"""
The floor on the limit is 640 rather than zero, {cite("Include/internal/pycore_long.h:40-45@v3.15.0rc1#_PY_LONG_MAX_STR_DIGITS_THRESHOLD")}, so that error messages and reprs of ordinary numbers can never themselves be the thing that raises.

## The hash is a remainder

One more thing that falls out of the representation. Hashing an int has to agree with hashing a float and a Fraction of the same value, because `1 == 1.0` and equal objects must hash equal. The trick is to do all of it modulo a prime, and the prime chosen is one less than a power of two. It is 2**61 - 1 on an ordinary build and 2**31 - 1 on a 32 bit one.

For a compact int the hash is just the value, {cite("Objects/longobject.c:3670-3684@v3.15.0rc1#long_hash")}. For a bigger one it walks the digits, and because the modulus is one less than a power of two, the multiply by 2**30 at each step is a bit rotation rather than a real division.

{lesson.claim("the hash of an integer is its remainder modulo a prime one less than a power of two, which is why a number equal to that modulus hashes to zero")}
""")


lesson.code("""
modulus = sys.hash_info.modulus

print(f"  the modulus        {modulus}")
print(f"  which is 2**{modulus.bit_length()} - 1  {modulus == 2 ** modulus.bit_length() - 1}")
print(f"  hash of it         {hash(modulus)}")
print()

for value in [7, 10**30, 2**200 + 1]:
    shown = str(value) if value < 10**6 else f"a {len(str(value))} digit number"
    print(f"  {shown:22}  hash equals value % modulus  {hash(value) == value % modulus}")
""")


lesson.md("""
That is also why the modulus, twice the modulus and zero all hash the same, which is a real collision you can construct on purpose but will never hit by accident.

## Try it yourself

Three things to try.

Find the sizeof steps yourself. Loop over `n` from 1 to 400, compute `sys.getsizeof(2**n)`, and print every `n` where the answer changed. You should get exactly the multiples of the digit width, and the digit width should be whatever `sys.int_info.bits_per_digit` says.

Break the digit rules on purpose. Take `digits_of` and hand `value_of` a list with a digit above the mask, or a trailing zero. The sum still comes out right, which is the point: those rules are for CPython's benefit, not arithmetic's, and every operation in `longobject.c` is allowed to assume them.

Work out where Karatsuba would pay off if the cutoff were wrong. Change `CUTOFF` to 10 and to 500 and print the crossover table again. At 10 the counts get worse for the small sizes, which is the bookkeeping the real cutoff is there to avoid.

## What just happened

An int is a sign, a digit count and an array of digits in base 2**30, stored least significant first. Four bytes per digit, and the first digit's worth of space comes with the object, so everything from 0 to 2**30 - 1 costs the same 28 bytes.

The sign, the count and one flag are packed into a single word. That packing exists so a single unsigned comparison can answer "does the fast path apply", and the fast path is taken everywhere in the source.

Integers from -5 up to a fixed ceiling are built once at startup and handed out rather than allocated, and they are immortal. The ceiling was 256 through 3.14 and is 1024 from 3.15, which is exactly why `is` on integers is a bug waiting for a version bump.

Addition is the column method you learned at school in base 2**30, with a carry slot allocated up front and normalized away afterwards. Multiplication is the same until 70 digits, at which point CPython splits both numbers in half and does three products instead of four.

Decimal conversion is the one operation that is quadratic and the one with a limit, because base 10 is not a power of two and untrusted input reaching `int()` is common.

Integer hashing is a remainder modulo a prime one less than a power of two, 2**61 - 1 on an ordinary build, chosen so that equal ints and floats hash equal and so that the per digit step is a rotation rather than a division.

## What is next

O10 is strings, which are the other type every program uses constantly and the one with the most machinery behind it. There are four different storage layouts depending on the largest character present, a cached hash, an interning table, and a compact form where the characters live inside the object. Some of that will look familiar after this lesson.
""")


raise SystemExit(lesson.save())
