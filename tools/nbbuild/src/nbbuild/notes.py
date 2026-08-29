"""The version notes that more than one lesson needs to say.

Four differences between 3.14 and 3.15 turn up over and over, in cells that have nothing
else in common. Writing the sentence once means a reader who meets it in T05 and again in
T10 gets the same words both times, and means that when 3.16 changes one of them there is
one place to fix rather than thirty.

A note that only one lesson needs is written in that lesson's `build.py`, not here. This is
for the ones that repeat.
"""

from __future__ import annotations

#: Every lesson opens by printing which interpreter is about to run it. That output is
#: different for everybody, and the banner says so itself, so these are declared quietly.
BANNER = "This prints the interpreter you are on, so it is different for everybody."

#: The one that started the whole check. 3.15 added LOAD_COMMON_CONSTANT, which carries
#: None in the instruction rather than in the code object's constant table.
TRAILING_NONE = "On 3.14 the implicit return None at the end is a LOAD_CONST and None sits in co_consts, so you get one more constant and two fewer bytes of bytecode than the text says."

#: RESUME and GET_ITER gained an inline cache entry in 3.15, which moves everything after
#: the first instruction. Any cell that prints an offset or a byte count says this.
OFFSETS = "On 3.14 RESUME and GET_ITER have no inline cache, so every offset below is two to four lower than the numbers in the text. The shape of the listing is the same."

#: 3.15 widened the range of integers the interpreter keeps one shared copy of, which
#: changes the answer to `257 is 257` and is the central observation of two lessons.
SMALL_INTS = "On 3.14 the shared range of small integers stops at 256 rather than 1024, so anything above 256 is a fresh object there and this prints False where the text says True."

#: Counts taken from the installation the reader happens to have. These differ between two
#: machines running the same version, so this one goes on a cell with `varies=` rather than
#: `differs=`. A reader comparing their screen against the page still needs to be told.
YOUR_INSTALL = "These numbers describe the Python you are running rather than the language, so they will not match the text exactly. A framework install, a source build and a Colab image all count different files."
