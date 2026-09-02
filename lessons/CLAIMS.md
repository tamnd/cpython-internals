# The claim ledger

Every behavioural claim the lessons make about CPython, and the cell that proves it.

This file is generated. A lesson marks a claim where it makes it, the build works out which
cell answers it, and `just claims` fails when one has no answer. The rule is that the
evidence is the next code cell and it has to come before the next section heading, because a
claim proved three sections later is a claim nobody checked.

A handful of true things cannot be observed from Python at all: the layout of an object
header, what the allocator does with a freed block, the shape of the eval loop. Those are
marked with the reason, and a lesson is allowed at most 3 of them. The cap is the point.
Without it the exception becomes the rule and this goes back to being a book.

437 claims across 55 lessons, 29 of them not observable from Python.

## B01. Building CPython, and whether you need to

| Claim | Proved by |
| --- | --- |
| a CPython built with configure keeps the argument list it was given, and sysconfig hands it back at run time | [`b01-07`](b01-building-cpython/b01.ipynb) |
| the python binary is a small program, and almost all of the interpreter lives in the library it links against | not observable from Python: the split between the binary and libpython is a link time arrangement, and Python is only ever handed the result |
| sysconfig cannot see any macro in pyconfig.h whose name starts with an underscore, so _Py_TAIL_CALL_INTERP is missing from get_config_vars even on a build that defines it | [`b01-10`](b01-building-cpython/b01.ipynb) |

## B02. Watching the interpreter stop

| Claim | Proved by |
| --- | --- |
| pdb reads its commands from whatever you hand it as standard input, so a debugging session can be written down in advance, run, and read back later | [`b02-07`](b02-the-debugger/b02.ipynb) |
| pdb is ordinary Python that asks the interpreter to call it back on every function call, line and return, which is a hook any program can install | [`b02-10`](b02-the-debugger/b02.ipynb) |
| four nested Python calls run inside a single _PyEval_EvalFrameDefault frame, so the C stack does not grow one frame per Python call | not observable from Python: counting C frames means attaching a debugger to the process, and there is no second process in a browser tab |
| small integers report a reference count of 3221225472, which is a marker meaning never free this rather than a count of references | [`b02-22`](b02-the-debugger/b02.ipynb) |

## B03. Asking CPython whether it still works

| Claim | Proved by |
| --- | --- |
| CPython's test suite is ordinary unittest, the same module you would use for your own project | [`b03-07`](b03-the-test-suite/b03.ipynb) |
| A file in Lib/test is a test file if its name starts with test_, and that is the entire rule | [`b03-10`](b03-the-test-suite/b03.ipynb) |
| A -m pattern matches if it matches the full test id or any single dotted part of it, so a bare method name finds that method in every class | [`b03-12`](b03-the-test-suite/b03.ipynb) |
| sys.gettotalrefcount only exists on a debug build, which is why hunting leaks needs one | not observable from Python: the function is compiled in only when CPython is configured with --with-pydebug, so an ordinary interpreter has nothing to call |
| A run is only reported as a leak when every counted repetition gained at least one reference, so a single noisy run is not enough | [`b03-16`](b03-the-test-suite/b03.ipynb) |

## B04. Reading the tree

| Claim | Proved by |
| --- | --- |
| the running interpreter can hand you the file and the line range for anything in the standard library written in Python, in the same shape as the source references in this book | [`b04-07`](b04-reading-the-tree/b04.ipynb) |
| the ast module can list every function and class in a file with the exact line range of each, which is enough to build an index of any Python file in the standard library | [`b04-12`](b04-reading-the-tree/b04.ipynb) |
| a generated file says so in its own first few lines, and usually names the script that wrote it, so you can find every one of them in your own standard library with a search for a handful of phrases | [`b04-14`](b04-reading-the-tree/b04.ipynb) |
| running those scripts against the unchanged input reproduces the committed files byte for byte, which is what makes generated a fact about a file rather than a comment in it | not observable from Python: the scripts live in Tools/ and read Python/bytecodes.c, and neither of those ships with an installed Python, so this is the recorded run below rather than a cell |
| every commit in CPython names an issue number in the first line of its message, so any line of code leads to a discussion | [`b04-22`](b04-reading-the-tree/b04.ipynb) |

## E01. The interpreter nobody wrote by hand

| Claim | Proved by |
| --- | --- |
| Lib/_opcode_metadata.py ships with every CPython install, and its first four lines say which script generated it and from which file | [`e01-07`](e01-the-interpreter-nobody-wrote/e01.ipynb) |
| the six line definition of UNARY_NOT becomes a seventeen line case in the generated eval loop plus four more in the tier two interpreter, and only three lines were written by a person | not observable from Python: the generated C is not shipped in an install, so it is quoted from the pinned tree rather than measured here |
| the stack effect of an instruction is the count of names after the arrow minus the count before it, and _opcode.stack_effect agrees | [`e01-10`](e01-the-interpreter-nobody-wrote/e01.ipynb) |
| opcode._specializations is the family declarations from Python/bytecodes.c, with one entry per family and one name per member | [`e01-13`](e01-the-interpreter-nobody-wrote/e01.ipynb) |
| the number of families and the number of specialized opcodes are both properties of this build, and both changed between 3.14 and 3.15 | [`e01-15`](e01-the-interpreter-nobody-wrote/e01.ipynb) |
| the cache slots after an instruction are the numbered slots in its definition added up, and dis reports the same totals the C table holds | [`e01-18`](e01-the-interpreter-nobody-wrote/e01.ipynb) |
| every instruction is two bytes plus two per cache slot, so the declared sizes add up to the exact length of a code object | [`e01-21`](e01-the-interpreter-nobody-wrote/e01.ipynb) |
| dis.opname is built entirely from opmap and _specialized_opmap in the generated module, and rebuilding it the same way gives an identical list | [`e01-24`](e01-the-interpreter-nobody-wrote/e01.ipynb) |
| the list of common constants is written by hand in Lib/opcode.py and grew from five entries to twelve between 3.14 and 3.15 | [`e01-27`](e01-the-interpreter-nobody-wrote/e01.ipynb) |

## E02. Two bytes at a time

| Claim | Proved by |
| --- | --- |
| the same sixteen bits in a code object are read as an opcode and argument pair, as a cache slot, or as a countdown counter, with nothing in the word saying which | not observable from Python: the union is a C type, so the three readings are quoted from the pinned tree rather than measured from Python |
| a code object holds more sixteen bit words than dis reports instructions, because the extra words are cache slots belonging to the instruction in front of them | [`e02-07`](e02-two-bytes-at-a-time/e02.ipynb) |
| walking co_code two bytes at a time, folding EXTENDED_ARG and skipping cache slots by their declared count, reproduces dis.get_instructions exactly | [`e02-10`](e02-two-bytes-at-a-time/e02.ipynb) |
| the interpreter never stops on a cache slot, so the offsets it visits jump by more than two after an instruction that carries a cache | [`e02-13`](e02-two-bytes-at-a-time/e02.ipynb) |
| an argument bigger than 255 is carried by an EXTENDED_ARG instruction in front of the real one, and dis folds the pair into a single number | [`e02-16`](e02-two-bytes-at-a-time/e02.ipynb) |
| pseudo instructions are numbered above 255 so that they cannot fit in the one byte opcode field of a code unit | [`e02-19`](e02-two-bytes-at-a-time/e02.ipynb) |
| which of the three dispatch strategies a CPython was built with is recorded in its build configuration and can differ between two installs of the same version | [`e02-22`](e02-two-bytes-at-a-time/e02.ipynb) |
| co_code is reconstructed from the running bytecode by undoing specialization and zeroing caches, so it differs from _co_code_adaptive once an instruction has specialized | [`e02-25`](e02-two-bytes-at-a-time/e02.ipynb) |

## E03. Where a running function lives

| Claim | Proved by |
| --- | --- |
| sys._getframe returns the same object each time it is called in one frame, and the frame it returns keeps working after the function has returned | [`e03-07`](e03-where-a-running-function-lives/e03.ipynb) |
| a local variable is a numbered slot in the frame rather than an entry in a dictionary, and the argument to LOAD_FAST is that number | [`e03-10`](e03-where-a-running-function-lives/e03.ipynb) |
| frame.f_locals inside a function is a write through proxy over the frame slots, so assigning through it changes the local variable | [`e03-12`](e03-where-a-running-function-lives/e03.ipynb) |
| a generator object contains its frame, so its size grows by exactly eight bytes for every extra local variable or value stack slot | [`e03-14`](e03-where-a-running-function-lives/e03.ipynb) |
| a Python function calling a Python function uses no C stack, while the same recursion routed through a C function costs hundreds or thousands of bytes per level | [`e03-17`](e03-where-a-running-function-lives/e03.ipynb) |
| sys.setrecursionlimit changes only the counter, so raising it lets pure Python recursion go further and leaves recursion through C stopping at the same depth for the same reason | [`e03-20`](e03-where-a-running-function-lives/e03.ipynb) |

## E04. Owned, borrowed, or not a pointer

| Claim | Proved by |
| --- | --- |
| sys.getrefcount answers 1 for a local variable, without the extra one for the asking, because handing a local to a function does not create a reference | [`e04-07`](e04-owned-borrowed-or-not-a-pointer/e04.ipynb) |
| every object address is a multiple of four, so the bottom two bits of an object pointer are always zero and free to be used for something else | [`e04-09`](e04-owned-borrowed-or-not-a-pointer/e04.ipynb) |
| the compiler picks LOAD_FAST or LOAD_FAST_BORROW for each use of a local, so the same variable can be loaded both ways in one function | [`e04-12`](e04-owned-borrowed-or-not-a-pointer/e04.ipynb) |
| a value loaded borrowed and then stored in a container gains a counted reference at the moment it is stored, and loses it again when the container drops it | [`e04-14`](e04-owned-borrowed-or-not-a-pointer/e04.ipynb) |
| the reference count of an immortal object is a fixed marker that does not move no matter how many references you take | [`e04-16`](e04-owned-borrowed-or-not-a-pointer/e04.ipynb) |
| a for loop needs one more value stack slot in 3.15 than in 3.14, and the extra slot holds the loop position as a number rather than an object | [`e04-19`](e04-owned-borrowed-or-not-a-pointer/e04.ipynb) |
| in the free threaded build a counted reference is an atomic operation, which is why avoiding one on every local load matters more there than it does under the GIL | not observable from Python: You would need a free threaded build and a machine with several cores to see the difference, and this notebook is running on neither. |

## E05. The try that costs nothing

| Claim | Proved by |
| --- | --- |
| the instructions for the guarded line are the same as the instructions for the unguarded line, so entering a try block executes nothing | [`e05-07`](e05-the-try-that-costs-nothing/e05.ipynb) |
| a try block adds bytes to the code object, but all of them are the handler and none of them are on the path a successful call takes | [`e05-09`](e05-the-try-that-costs-nothing/e05.ipynb) |
| every entry in the exception table carries a target, a stack depth and a lasti flag as well as the range it covers | [`e05-12`](e05-the-try-that-costs-nothing/e05.ipynb) |
| the exception table can be decoded by hand from the raw bytes, and a hand written decoder gives the same answer as the one in dis | [`e05-15`](e05-the-try-that-costs-nothing/e05.ipynb) |
| a loop with a try around its body runs at about the same speed as the same loop without one, and faster than the same loop checking a returned value instead | [`e05-18`](e05-the-try-that-costs-nothing/e05.ipynb) |
| raising and catching in the same frame costs a few hundred nanoseconds, and each extra frame the exception has to travel through adds roughly the same amount again | [`e05-21`](e05-the-try-that-costs-nothing/e05.ipynb) |
| the traceback points at the instruction that raised, not at the finally block that re-raised, because the raising offset was saved on the stack and put back | [`e05-24`](e05-the-try-that-costs-nothing/e05.ipynb) |
| the body of a finally block appears in the bytecode more than once, one copy per way out of the try it guards | [`e05-27`](e05-the-try-that-costs-nothing/e05.ipynb) |
| a for loop has no exception table at all, and the same loop written with next and a try does, and is slower | [`e05-29`](e05-the-try-that-costs-nothing/e05.ipynb) |

## E06. The instruction that rewrites itself

| Claim | Proved by |
| --- | --- |
| disassembling the same unmodified function before and after calling it twice gives two different instruction names | [`e06-07`](e06-the-instruction-that-rewrites-itself/e06.ipynb) |
| BINARY_OP is not one instruction but a family, and the whole set of families is listed in a module you can import | [`e06-09`](e06-the-instruction-that-rewrites-itself/e06.ipynb) |
| five copies of the same source compile to the same bytecode and then specialize into different instructions based only on the values passed in | [`e06-12`](e06-the-instruction-that-rewrites-itself/e06.ipynb) |
| the number of cache slots after each instruction is a fixed property of that instruction and can be read out of dis | [`e06-15`](e06-the-instruction-that-rewrites-itself/e06.ipynb) |
| the countdown that controls specialization can be read directly out of the running bytecode and watched change | [`e06-18`](e06-the-instruction-that-rewrites-itself/e06.ipynb) |
| an instruction specializes on exactly the second execution, and a specialized instruction survives exactly fifty two failures and gives up on the fifty third | [`e06-21`](e06-the-instruction-that-rewrites-itself/e06.ipynb) |
| an instruction that keeps missing does not return to the general form permanently, it re-specializes for whatever it is now seeing | [`e06-23`](e06-the-instruction-that-rewrites-itself/e06.ipynb) |
| the same attribute lookup specializes into different instructions depending only on the shape of the object it is reading from | [`e06-26`](e06-the-instruction-that-rewrites-itself/e06.ipynb) |
| calls specialize into different instructions depending on what is being called, not just on the arguments | [`e06-28`](e06-the-instruction-that-rewrites-itself/e06.ipynb) |
| a loop over mixed types is slower than the same loop over either type alone, purely because the instruction cannot stay specialized | [`e06-31`](e06-the-instruction-that-rewrites-itself/e06.ipynb) |
| in a real module only a small fraction of specializable instructions ever specialize, because most code does not run often enough | [`e06-34`](e06-the-instruction-that-rewrites-itself/e06.ipynb) |

## E07. The loop that gets its own program

| Claim | Proved by |
| --- | --- |
| the JIT is a build option and a startup flag rather than something a running program can turn on | [`e07-07`](e07-the-loop-that-gets-its-own-program/e07.ipynb) |
| the backward jump in a loop specializes into one of two named forms depending on whether the JIT is switched on | [`e07-10`](e07-the-loop-that-gets-its-own-program/e07.ipynb) |
| a loop needs a few thousand iterations before it grows a trace, and the exact number is findable by searching for it | [`e07-13`](e07-the-loop-that-gets-its-own-program/e07.ipynb) |
| the trace attached to a hot loop is a readable object, and every micro operation in it can be printed from Python | [`e07-16`](e07-the-loop-that-gets-its-own-program/e07.ipynb) |
| the optimizer deletes guards it can prove cannot fail, so a trace runs far fewer checks than the instructions it came from | [`e07-19`](e07-the-loop-that-gets-its-own-program/e07.ipynb) |
| a trace recorded from a loop containing a function call includes the body of that function, so the call boundary is gone from the hot path | [`e07-22`](e07-the-loop-that-gets-its-own-program/e07.ipynb) |
| turning the JIT on changes how long the same loop takes, by enough to measure from Python | [`e07-25`](e07-the-loop-that-gets-its-own-program/e07.ipynb) |

## E08. Watching without slowing it down

| Claim | Proved by |
| --- | --- |
| the interpreter offers a fixed set of numbered monitoring events and a fixed number of tool slots, and both are readable from Python | [`e08-07`](e08-watching-without-slowing-it-down/e08.ipynb) |
| switching a monitoring event on for one function replaces instructions in its bytecode, and switching the event off puts the original instructions back | [`e08-09`](e08-watching-without-slowing-it-down/e08.ipynb) |
| a monitoring callback that returns DISABLE leaves the watched loop running at close to full speed, while the same callback returning None makes it several times slower | [`e08-11`](e08-watching-without-slowing-it-down/e08.ipynb) |
| a callback returning DISABLE is called once per instruction rather than once per execution, so a loop of a thousand turns produces a handful of calls | [`e08-14`](e08-watching-without-slowing-it-down/e08.ipynb) |
| two monitoring tools can watch the same function at the same time, each receiving only the events it registered for | [`e08-16`](e08-watching-without-slowing-it-down/e08.ipynb) |
| instrumenting a warm function un-specializes its instructions, and they specialize again once the instrumentation is removed and the function runs | [`e08-19`](e08-watching-without-slowing-it-down/e08.ipynb) |
| sys.settrace is implemented on top of monitoring, so installing a trace function puts instrumented instructions into the functions it runs | [`e08-21`](e08-watching-without-slowing-it-down/e08.ipynb) |

## E09. The optimizer that runs your loop without running it

| Claim | Proved by |
| --- | --- |
| an executor can be fetched from Python and read as a list of micro operation names | [`e09-07`](e09-the-optimizer-that-runs-your-loop-without-running-it/e09.ipynb) |
| a trace with three reads of the same attribute contains one type check, not three | [`e09-10`](e09-the-optimizer-that-runs-your-loop-without-running-it/e09.ipynb) |
| the number of guards in the trace does not grow as more additions are added to the loop body | [`e09-13`](e09-the-optimizer-that-runs-your-loop-without-running-it/e09.ipynb) |
| a guard whose type question is already answered comes out as a narrower check on the remaining question | [`e09-16`](e09-the-optimizer-that-runs-your-loop-without-running-it/e09.ipynb) |
| one loop body produces three different pop instructions depending on what is known about each value | [`e09-19`](e09-the-optimizer-that-runs-your-loop-without-running-it/e09.ipynb) |
| a loop that reads a global and calls a global function contains no name lookups in its trace | [`e09-22`](e09-the-optimizer-that-runs-your-loop-without-running-it/e09.ipynb) |
| rebinding a global that a trace depends on marks the executor invalid and detaches it | [`e09-25`](e09-the-optimizer-that-runs-your-loop-without-running-it/e09.ipynb) |
| the amount of bookkeeping left in a trace tracks how many operations in it could run other code | [`e09-28`](e09-the-optimizer-that-runs-your-loop-without-running-it/e09.ipynb) |

## E10. The compiler that finished before you started

| Claim | Proved by |
| --- | --- |
| an executor hands back its compiled machine code as bytes, rounded up to a whole page | [`e10-07`](e10-the-compiler-that-finished-before-you-started/e10.ipynb) |
| machine code size grows by a fixed amount for each micro operation added to the trace | [`e10-10`](e10-the-compiler-that-finished-before-you-started/e10.ipynb) |
| different loop bodies produce a similar number of machine code bytes per micro operation | [`e10-13`](e10-the-compiler-that-finished-before-you-started/e10.ipynb) |
| the address of a baked in constant appears literally inside the compiled machine code | [`e10-16`](e10-the-compiler-that-finished-before-you-started/e10.ipynb) |
| two loops differing only in which constant they use compile to almost identical machine code | [`e10-19`](e10-the-compiler-that-finished-before-you-started/e10.ipynb) |
| two different loops that share a prefix of micro operations share most of their opening bytes | [`e10-22`](e10-the-compiler-that-finished-before-you-started/e10.ipynb) |
| the memory an executor is given is a whole number of pages, most of it unused for a short trace | [`e10-25`](e10-the-compiler-that-finished-before-you-started/e10.ipynb) |

## E11. One function per opcode

| Claim | Proved by |
| --- | --- |
| the dispatch style chosen at configure time is recorded as a macro in the shipped pyconfig.h | [`e11-07`](e11-one-function-per-opcode/e11.ipynb) |
| the same generated C file becomes a switch, a jump table or a set of separate functions depending only on which macros are defined around it | not observable from Python: the three versions are produced by the C preprocessor at build time, and only one of them exists in the binary you are running |
| the opcode numbering fills most of the 256 available slots, and the leftovers shrink as opcodes are added | [`e11-10`](e11-one-function-per-opcode/e11.ipynb) |
| each opcode function ends by calling the next one and the compiler is required to turn that call into a jump | not observable from Python: whether a call reused the stack frame is a property of the machine code, and Python has no way to look at the C stack |
| a single function containing eighty thousand bytecode instructions runs in one frame without trouble | [`e11-13`](e11-one-function-per-opcode/e11.ipynb) |
| adding one more bytecode instruction to a hot loop costs a roughly fixed amount of time | [`e11-15`](e11-one-function-per-opcode/e11.ipynb) |
| the time three different loops take tracks the number of instructions they run, at close to the same rate | [`e11-18`](e11-one-function-per-opcode/e11.ipynb) |
| the speed comes from the compiler handling small functions better, not from calls being cheap | not observable from Python: register allocation happens inside the C compiler, and nothing about it survives into anything Python can inspect |

## E12. One plus sign, all the way down

| Claim | Proved by |
| --- | --- |
| BINARY_OP occupies twelve bytes in a code object, two for the instruction and ten for five cache slots | [`e12-07`](e12-one-plus-sign-all-the-way-down/e12.ipynb) |
| the instructions in a loop are replaced by narrower ones after the loop has run enough times | [`e12-10`](e12-one-plus-sign-all-the-way-down/e12.ipynb) |
| the same expression specializes to different instructions depending on the types that turn up at run time | [`e12-12`](e12-one-plus-sign-all-the-way-down/e12.ipynb) |
| adding strings specializes differently depending on whether the result is stored back into the left operand | [`e12-15`](e12-one-plus-sign-all-the-way-down/e12.ipynb) |
| the micro operations a specialized instruction expands to are visible in the trace an executor holds | [`e12-17`](e12-one-plus-sign-all-the-way-down/e12.ipynb) |
| adding floats produces a different guard, a different addition and a different pop than adding ints | [`e12-20`](e12-one-plus-sign-all-the-way-down/e12.ipynb) |
| one plus sign in a loop can be followed from its instruction through its cache slots and micro operations to its machine code | [`e12-23`](e12-one-plus-sign-all-the-way-down/e12.ipynb) |

## F01. The tokenizer, in C

| Claim | Proved by |
| --- | --- |
| the token numbers in Lib/token.py are the line order of Grammar/Tokens, and the file says at the top that it was generated | [`f01-07`](f01-the-tokenizer-in-c/f01.ipynb) |
| every operator arrives as the single type OP and the exact spelling is recovered afterwards from a table, rather than the tokenizer having a separate type for each one | [`f01-09`](f01-the-tokenizer-in-c/f01.ipynb) |
| compiling the same source as bytes and as a str goes through two different tokenizer constructors, and the difference shows up as whether a coding cookie is obeyed or ignored | [`f01-11`](f01-the-tokenizer-in-c/f01.ipynb) |
| the tokenizer holds one line of your file at a time, and a file that fails to parse gets read more than once | not observable from Python: the fprintf that prints this is inside an #ifdef Py_DEBUG, so a stock interpreter has no way to show it and the run below is a recording |
| the deepest you can indent and the deepest you can nest brackets are both fixed at compile time, and you can find both numbers from Python without reading the header | [`f01-14`](f01-the-tokenizer-in-c/f01.ipynb) |
| every DEDENT from the same line ending reports the same position and an empty string, because they are drained from a counter rather than matched against text | [`f01-17`](f01-the-tokenizer-in-c/f01.ipynb) |
| some tokenizer errors carry their message from the lexer and others carry only a number that the parser turns into words, and which is which explains why a TabError and an unterminated string feel like they come from different places | [`f01-19`](f01-the-tokenizer-in-c/f01.ipynb) |

## F02. f-strings in the lexer

| Claim | Proved by |
| --- | --- |
| a plain string is a single STRING token, and an f-string with the same characters is a start token, some middle tokens, the ordinary tokens of the expression, and an end token | [`f02-07`](f02-f-strings-in-the-lexer/f02.ipynb) |
| f-strings have two separate nesting limits, one for f-strings inside f-strings and a far smaller one for fields inside a format spec, and you can find both from Python | [`f02-09`](f02-f-strings-in-the-lexer/f02.ipynb) |
| the text of a format spec comes out as FSTRING_MIDDLE tokens, the same token type as literal text in the body of the f-string | [`f02-11`](f02-f-strings-in-the-lexer/f02.ipynb) |
| the lexer does no escape decoding inside an f-string, so the token for a backslash n is two characters long and the parser is what turns it into one | [`f02-13`](f02-f-strings-in-the-lexer/f02.ipynb) |
| a doubled brace produces two separate FSTRING_MIDDLE tokens with a one character gap between them, and that gap is the character the lexer threw away | [`f02-15`](f02-f-strings-in-the-lexer/f02.ipynb) |
| the spacing you wrote inside an equals field survives exactly, including spaces a reconstruction would have normalised away | [`f02-17`](f02-f-strings-in-the-lexer/f02.ipynb) |
| a t-string produces the same shape of token stream as an f-string with different token names, because the lexer runs the same code and only changes which name it stamps on the result | [`f02-19`](f02-f-strings-in-the-lexer/f02.ipynb) |

## F03. The parser nobody wrote

| Claim | Proved by |
| --- | --- |
| the keyword module in the standard library is generated from the grammar file, and it says so in its own docstring | [`f03-07`](f03-the-parser-nobody-wrote/f03.ipynb) |
| the generator is a real program you can point at any grammar, and on a four rule grammar it writes a working parser in about a hundred lines | not observable from Python: Tools/peg_generator ships only in the CPython source tree, so no installed Python can import it and the run below is a recording |
| associativity is not configured anywhere, it falls out of which side of the rule the rule names itself on | [`f03-10`](f03-the-parser-nobody-wrote/f03.ipynb) |
| a soft keyword can be a keyword and an ordinary variable name in the same file, and a reserved word cannot | [`f03-12`](f03-the-parser-nobody-wrote/f03.ipynb) |
| the wording of a syntax error is written in the grammar file, and code that no invalid_ rule matches falls back to a generic message | [`f03-15`](f03-the-parser-nobody-wrote/f03.ipynb) |
| the node types you see from the ast module are named directly in the grammar's actions | [`f03-17`](f03-the-parser-nobody-wrote/f03.ipynb) |

## F04. The tree is generated too

| Claim | Proved by |
| --- | --- |
| the _fields tuple on a node class is the field list from the schema, in the order the schema wrote it | [`f04-07`](f04-the-tree-is-generated-too/f04.ipynb) |
| position information is declared once per family in the schema, so a node either has all four position attributes or none of them | [`f04-09`](f04-the-tree-is-generated-too/f04.ipynb) |
| the abstract base classes in the ast module are exactly the sum types in the schema, and the classes with no subclasses are the products | [`f04-11`](f04-the-tree-is-generated-too/f04.ipynb) |
| an optional field arrives as None and a sequence field arrives as an empty list, whether or not you wrote anything for it | [`f04-13`](f04-the-tree-is-generated-too/f04.ipynb) |
| the tree keeps meaning and drops spelling, so parsing and unparsing is not a round trip | [`f04-15`](f04-the-tree-is-generated-too/f04.ipynb) |
| a hand built tree is checked in C before the compiler sees it, and the two kinds of complaint come from two different places | [`f04-17`](f04-the-tree-is-generated-too/f04.ipynb) |

## F05. Every name gets a number

| Claim | Proved by |
| --- | --- |
| there are mistakes the parser accepts and the compiler refuses, and every one of them is about names | [`f05-07`](f05-every-name-gets-a-number/f05.ipynb) |
| the symbol table sorts every name in every block into one of five scopes, and you can read the answers straight out of the symtable module | [`f05-10`](f05-every-name-gets-a-number/f05.ipynb) |
| a name is local because of an assignment anywhere in the block, including one that comes after the use | [`f05-12`](f05-every-name-gets-a-number/f05.ipynb) |
| co_cellvars and co_freevars on the code objects are the symbol table's answers, written down again | [`f05-14`](f05-every-name-gets-a-number/f05.ipynb) |
| a method gets a __class__ free variable because the symbol table saw the name super, and a method that reaches super some other way does not get one | [`f05-16`](f05-every-name-gets-a-number/f05.ipynb) |

## F06. One node at a time

| Claim | Proved by |
| --- | --- |
| `and` and `or` produce no instruction of their own, only a jump | [`f06-07`](f06-one-node-at-a-time/f06.ipynb) |
| the shape a node compiles to does not depend on where the node is, only on what kind of node it is | [`f06-09`](f06-one-node-at-a-time/f06.ipynb) |
| in `box[key] = value` the value runs before the target and before the key | [`f06-11`](f06-one-node-at-a-time/f06.ipynb) |
| the code generator emits the dead branch of `if False` in full, and something later removes it | [`f06-16`](f06-one-node-at-a-time/f06.ipynb) |
| some instructions in your function belong to no line of your source, and dis says so | [`f06-19`](f06-one-node-at-a-time/f06.ipynb) |

## F07. The list becomes a graph

| Claim | Proved by |
| --- | --- |
| the three leader rules are enough to split real bytecode into blocks | [`f07-07`](f07-the-list-becomes-a-graph/f07.ipynb) |
| in a function with a try, the compiled instructions are not in source order | [`f07-10`](f07-the-list-becomes-a-graph/f07.ipynb) |
| the code generator emits code that can never run, and the graph pass deletes it | [`f07-13`](f07-the-list-becomes-a-graph/f07.ipynb) |
| adding stack effects up along the flat list gets the right answer until there is a handler | [`f07-15`](f07-the-list-becomes-a-graph/f07.ipynb) |
| moving a cold block to the end leaves a jump behind where control used to fall through | [`f07-17`](f07-the-list-becomes-a-graph/f07.ipynb) |
| nothing in the finished code object is a graph | [`f07-20`](f07-the-list-becomes-a-graph/f07.ipynb) |

## F08. The optimizer

| Claim | Proved by |
| --- | --- |
| whether an expression is folded depends on how big the answer would be, and the boundary is exact | [`f08-07`](f08-the-optimizer/f08.ipynb) |
| a leftover constant survives if it happened to land in the first slot, and is removed otherwise | [`f08-09`](f08-the-optimizer/f08.ipynb) |
| a small ending can be copied in place of a jump, so the same two instructions appear twice | [`f08-12`](f08-the-optimizer/f08.ipynb) |
| a line break in the middle of an expression, or a sixteenth local variable, costs you a superinstruction | [`f08-15`](f08-the-optimizer/f08.ipynb) |
| the same local, read twice in one function, can compile to a checked load and an unchecked one | [`f08-17`](f08-the-optimizer/f08.ipynb) |

## F09. Two bytes at a time

| Claim | Proved by |
| --- | --- |
| the bytes of a small function are short enough to read one by one and match against the disassembly | [`f09-07`](f09-two-bytes-at-a-time/f09.ipynb) |
| the gap between one instruction's offset and the next tells you how many cache slots it carries | [`f09-10`](f09-two-bytes-at-a-time/f09.ipynb) |
| you can rebuild every jump target by hand from the argument and the size of the jump itself | [`f09-13`](f09-two-bytes-at-a-time/f09.ipynb) |
| the step that first needs an EXTENDED_ARG is one pair bigger than every other step | [`f09-16`](f09-two-bytes-at-a-time/f09.ipynb) |
| the same jump is a label before the assembler and a signed distance after it | [`f09-19`](f09-two-bytes-at-a-time/f09.ipynb) |

## F10. Inside a code object

| Claim | Proved by |
| --- | --- |
| the code objects of a file form a tree, reachable through co_consts alone | [`f10-07`](f10-inside-a-code-object/f10.ipynb) |
| a parameter that a nested function reads is tagged twice, so it appears in two tuples | [`f10-09`](f10-inside-a-code-object/f10.ipynb) |
| a function whose parameter is captured starts with instructions that belong to no line of source | [`f10-11`](f10-inside-a-code-object/f10.ipynb) |
| a module body and a class body have no flags set at all, and a function has several | [`f10-13`](f10-inside-a-code-object/f10.ipynb) |
| the same source compiled from two different filenames gives two equal code objects | [`f10-15`](f10-inside-a-code-object/f10.ipynb) |
| replace gives you a new code object and leaves the original alone | [`f10-17`](f10-inside-a-code-object/f10.ipynb) |

## F11. Two tables on the side

| Claim | Proved by |
| --- | --- |
| the instructions inside a try block are identical to the same code with no try around it | [`f11-07`](f11-two-tables-on-the-side/f11.ipynb) |
| an exception table entry decodes to start, size, target and a doubled depth | [`f11-13`](f11-two-tables-on-the-side/f11.ipynb) |
| a dozen lines of Python decode co_exceptiontable exactly as dis does | [`f11-16`](f11-two-tables-on-the-side/f11.ipynb) |
| the caret in a traceback is drawn from the column numbers in co_linetable | [`f11-20`](f11-two-tables-on-the-side/f11.ipynb) |
| some instructions in a normal function have no source location at all | [`f11-23`](f11-two-tables-on-the-side/f11.ipynb) |
| a hand written decoder reproduces co_positions() for every code object in a standard library module | [`f11-26`](f11-two-tables-on-the-side/f11.ipynb) |
| the two tables encode integers with their chunks in opposite orders | [`f11-31`](f11-two-tables-on-the-side/f11.ipynb) |

## F12. What ends up on disk

| Claim | Proved by |
| --- | --- |
| a .pyc is a sixteen byte header followed by one marshalled object and nothing else | [`f12-07`](f12-what-ends-up-on-disk/f12.ipynb) |
| half of the magic number is a carriage return and a newline put there to catch text mode copying | [`f12-13`](f12-what-ends-up-on-disk/f12.ipynb) |
| the first byte of any marshalled object is an ascii letter naming its type | [`f12-16`](f12-what-ends-up-on-disk/f12.ipynb) |
| a value that shows up twice is written once and pointed at the second time | [`f12-18`](f12-what-ends-up-on-disk/f12.ipynb) |
| a reader written here decodes a marshalled code object into the fields the interpreter reads | [`f12-21`](f12-what-ends-up-on-disk/f12.ipynb) |
| a .pyc assembled by hand imports and runs with no source file on disk | [`f12-26`](f12-what-ends-up-on-disk/f12.ipynb) |
| a wrong magic number raises and a wrong timestamp is fixed silently | [`f12-29`](f12-what-ends-up-on-disk/f12.ipynb) |

## M01. Three doors into the same heap

| Claim | Proved by |
| --- | --- |
| Making a hundred thousand objects moves sys.getallocatedblocks by a hundred thousand and one, and dropping them moves it back | [`m01-07`](m01-three-doors-into-the-same-heap/m01.ipynb) |
| A block allocated through PyMem_RawMalloc, PyMem_Malloc or PyObject_Malloc carries the byte r, m or o in front of it | [`m01-13`](m01-three-doors-into-the-same-heap/m01.ipynb) |
| A Python object's memory comes through the obj door, and the size stored in front of it is the size of that one block rather than everything sys.getsizeof counts | [`m01-16`](m01-three-doors-into-the-same-heap/m01.ipynb) |
| A list is two blocks, and the second one came through the mem door rather than the obj door | [`m01-19`](m01-three-doors-into-the-same-heap/m01.ipynb) |
| Freeing a block through a different door than it was allocated from is a fatal error naming both doors | [`m01-22`](m01-three-doors-into-the-same-heap/m01.ipynb) |
| Writing one byte past the end of a block is caught, and the report says which byte and how far past | [`m01-24`](m01-three-doors-into-the-same-heap/m01.ipynb) |
| Twenty thousand blocks of 496 bytes costs several new arenas and twenty thousand of 528 bytes costs none | [`m01-27`](m01-three-doors-into-the-same-heap/m01.ipynb) |
| Starting Python with PYTHONMALLOC=malloc removes CPython's small object allocator entirely, and sys.getallocatedblocks then reports zero | [`m01-30`](m01-three-doors-into-the-same-heap/m01.ipynb) |

## O01. The header, byte by byte

| Claim | Proved by |
| --- | --- |
| id() is the address an object lives at, and the two machine words there are its reference count and a pointer to its type | [`o01-07`](o01-the-header-byte-by-byte/o01.ipynb) |
| the reference count is thirty two bits wide, and the other half of that word holds two more fields | [`o01-10`](o01-the-header-byte-by-byte/o01.ipynb) |
| an immortal object's count starts halfway between the immortality line and the top of the field, leaving about a billion of slack in each direction | [`o01-13`](o01-the-header-byte-by-byte/o01.ipynb) |
| a string literal that happens to be one of CPython's own identifiers is immortal, and the same characters CPython does not use are not | [`o01-16`](o01-the-header-byte-by-byte/o01.ipynb) |
| for a tuple, a list, a bytes and a str, the machine word after the header is the length | [`o01-19`](o01-the-header-byte-by-byte/o01.ipynb) |
| sys.getsizeof reports two machine words more than an object's own __sizeof__ for the types the cycle collector tracks, and nothing extra for the types it does not | [`o01-21`](o01-the-header-byte-by-byte/o01.ipynb) |
| the free threaded build gives every object a thirty two byte header, split so the owning thread can increment without an atomic instruction | not observable from Python: the fields only exist in a build configured with --disable-gil, and this notebook is not running one |

## O02. Following the type pointer

| Claim | Proved by |
| --- | --- |
| the second word of an object is the address of its type object, and following it from any object reaches type in at most two steps, where it loops | [`o02-07`](o02-following-the-type-pointer/o02.ipynb) |
| basicsize is the fixed part of an instance and itemsize is charged per element, and list has an itemsize of zero because its items live in a separate allocation | [`o02-09`](o02-following-the-type-pointer/o02.ipynb) |
| basicsize plus itemsize times ob_size matches __sizeof__ for the variable sized types, and misses for list, whose reported size includes an array the type object knows nothing about | [`o02-12`](o02-following-the-type-pointer/o02.ipynb) |
| the flags word distinguishes static types from heap types, and the same word is what makes int reject attribute assignment while a class you wrote accepts it | [`o02-15`](o02-following-the-type-pointer/o02.ipynb) |
| a class statement sets tp_dictoffset to -1 and tp_weaklistoffset to minus four pointers, and the space those refer to sits in front of the object, which is why getsizeof reports more than __sizeof__ | [`o02-17`](o02-following-the-type-pointer/o02.ipynb) |
| an instance of a class with a managed dict is allocated with room for its attribute values after the object, and that room is in neither of the numbers getsizeof adds together | not observable from Python: the inline values array is sized from a table on the type and no Python level call reports it |
| a class statement compiles to a call to __build_class__, and calling type with a name, bases and a namespace produces a type with the same flags, size and mro | [`o02-20`](o02-following-the-type-pointer/o02.ipynb) |

## O03. Dunders and the slots behind them

| Claim | Proved by |
| --- | --- |
| the dunder methods on a builtin type are slot wrappers generated from its C slots, and they are a different kind of object from both the plain methods on the same type and the functions you write in a class body | [`o03-07`](o03-dunders-and-slots/o03.ipynb) |
| a dunder assigned to an instance is a real attribute you can call by name, and the built in function that would use it never sees it, because the slot looks the name up on the type | [`o03-11`](o03-dunders-and-slots/o03.ipynb) |
| assigning a dunder to a class updates the slot at once, on that class and on every subclass of it, and deleting it puts the inherited behaviour back | [`o03-13`](o03-dunders-and-slots/o03.ipynb) |
| a class defining only __getitem__ can be iterated over and used with in, because that one name fills the sq_item slot and the old sequence protocol is still what iteration falls back on | [`o03-15`](o03-dunders-and-slots/o03.ipynb) |
| a subclass that defines __radd__ itself is called before the base class __add__, and an unrelated class defining __radd__ is not, because both names share one slot and the dispatcher checks the subclass relationship first | [`o03-17`](o03-dunders-and-slots/o03.ipynb) |
| a class that defines __eq__ and not __hash__ ends up with a real None stored under __hash__ in its class dict, and putting a hash back is a one line assignment | [`o03-19`](o03-dunders-and-slots/o03.ipynb) |

## O04. The order things are found in

| Claim | Proved by |
| --- | --- |
| a class with two bases carries a flat __mro__ tuple that flattens both paths into one order, and method lookup follows that order rather than searching the base classes | [`o04-07`](o04-the-order-things-are-found-in/o04.ipynb) |
| swapping the order of the declared bases changes the resulting MRO, so the bases tuple is an input to the computation and not just a record of what you typed | [`o04-09`](o04-the-order-things-are-found-in/o04.ipynb) |
| every class's MRO starts with the class itself, ends with object, and lists each declared base in the order it was declared | [`o04-11`](o04-the-order-things-are-found-in/o04.ipynb) |
| a twenty line C3 merge written in Python reproduces CPython's __mro__ exactly, for hand written diamonds and for classes taken from the standard library | [`o04-13`](o04-the-order-things-are-found-in/o04.ipynb) |
| a chain of single inheritance produces an MRO that is just each class prepended to its base's MRO, which is the fast path CPython takes without running the merge | [`o04-15`](o04-the-order-things-are-found-in/o04.ipynb) |
| a pair of bases that order two classes in opposite ways makes the class statement itself raise TypeError, and a repeated base is rejected earlier by a separate check with a different message | [`o04-17`](o04-the-order-things-are-found-in/o04.ipynb) |
| super in a method resolves against the MRO of the instance's type, so an unchanged method in Left can dispatch to Right when the instance is a Both, even though Left never refers to Right | [`o04-19`](o04-the-order-things-are-found-in/o04.ipynb) |
| assigning to a class's __bases__ recomputes the MRO of that class and of every subclass, and instances that already exist pick up the new method at once | [`o04-22`](o04-the-order-things-are-found-in/o04.ipynb) |
| a metaclass that overrides mro can return an order the C3 rules would never produce, and attribute lookup uses that order without complaint | [`o04-24`](o04-the-order-things-are-found-in/o04.ipynb) |

## O05. What a dot does

| Claim | Proved by |
| --- | --- |
| with the same name present on the type and in the instance dict, a data descriptor on the type wins and a non data descriptor loses, and the instance dict entry is untouched either way | [`o05-07`](o05-what-a-dot-does/o05.ipynb) |
| __getattr__ runs only for names the normal lookup failed to find, while an overridden __getattribute__ runs for every name including __dict__ | [`o05-09`](o05-what-a-dot-does/o05.ipynb) |
| assigning __getattr__ to an instance leaves it in the instance dict and has no effect on attribute lookup | [`o05-11`](o05-what-a-dot-does/o05.ipynb) |
| a name defined on the metaclass is reachable through the class and not through an instance of it, and a descriptor found on a class is called with None where the instance would be | [`o05-13`](o05-what-a-dot-does/o05.ipynb) |
| the AttributeError for an instance and for a class have different wording, and the exception carries the name and the object as attributes | [`o05-15`](o05-what-a-dot-does/o05.ipynb) |
| the did you mean suggestion is not part of the exception message and only appears when a traceback is formatted, because it is computed from the obj attribute at that point | [`o05-17`](o05-what-a-dot-does/o05.ipynb) |
| the cache and the version tag are not visible from Python at all, since nothing exposes tp_version_tag, the hit rate, or the cache contents | not observable from Python: the effect is only measurable as a timing difference, and the specialised bytecode in the next section is the closest observable proxy |
| the same LOAD_ATTR instruction takes a different specialised form depending on whether the attribute lives in the instance values, in a slot, on a module, or is a method | [`o05-20`](o05-what-a-dot-does/o05.ipynb) |
| assigning a property over an attribute the specialised instruction was relying on makes the guard fail, and the instruction goes back to the general form and then settles on a different specialised one | [`o05-22`](o05-what-a-dot-does/o05.ipynb) |

## O06. What property actually is

| Claim | Proved by |
| --- | --- |
| an object with __get__ and __set__ in a class dict intercepts both reads and writes of that attribute on every instance of the class | [`o06-07`](o06-what-property-actually-is/o06.ipynb) |
| reading a method off an instance calls the function's __get__ and produces a new bound method object each time, while reading it off the class returns the plain function | [`o06-10`](o06-what-property-actually-is/o06.ipynb) |
| classmethod produces a bound method whose __self__ is the class, and the class it binds to is the one the lookup started from rather than the one that defined the method | [`o06-14`](o06-what-property-actually-is/o06.ipynb) |
| attributes defined from C appear as one of five descriptor types, and whether each is a data descriptor is decided by whether its type fills in tp_descr_set | [`o06-20`](o06-what-property-actually-is/o06.ipynb) |
| a descriptor placed in an instance dict is returned as itself, because the lookup that would call __get__ only runs for objects found on the type | [`o06-24`](o06-what-property-actually-is/o06.ipynb) |
| __set_name__ runs once for every entry in the class dict during class creation, and never runs again for later assignments to the class | [`o06-26`](o06-what-property-actually-is/o06.ipynb) |

## O07. Two arrays and a hash

| Claim | Proved by |
| --- | --- |
| the probe order for a size 8 table starting at slot 0 is 0, 1, 6, 7, 4, 5, 2, 3, which visits every slot exactly once before repeating | [`o07-08`](o07-two-arrays-and-a-hash/o07.ipynb) |
| a dict grows when its entry array is full rather than when its length crosses a threshold, so the resize points fall at 6, 11, 22, 43 and 86 keys | [`o07-10`](o07-two-arrays-and-a-hash/o07.ipynb) |
| a dict that is deleted from and inserted into in equal measure still resizes, because the entry array only ever gets compacted by a resize | [`o07-16`](o07-two-arrays-and-a-hash/o07.ipynb) |
| a dict with only exact str keys uses a smaller entry layout, and putting one non string key in converts the whole table to the larger one | [`o07-21`](o07-two-arrays-and-a-hash/o07.ipynb) |

## O08. Where attributes really live

| Claim | Proved by |
| --- | --- |
| the compiler records every attribute assigned to self inside a class body and stores the names on the class as __static_attributes__ | [`o08-07`](o08-where-attributes-really-live/o08.ipynb) |
| two instances of the same class keep their own attribute order even though the names themselves are stored once, on the type | [`o08-10`](o08-where-attributes-really-live/o08.ipynb) |
| an instance sharing its keys with its class costs roughly a third of what the same instance costs once it has a dict of its own | [`o08-12`](o08-where-attributes-really-live/o08.ipynb) |
| a class shares up to 30 attribute names when they are known when the class is created, and only 29 when they are discovered later, because creating the first instance reserves one slot | [`o08-15`](o08-where-attributes-really-live/o08.ipynb) |
| reading an attribute on an instance with inline values specialises to a different instruction than reading one on an instance whose dict has been materialised | [`o08-18`](o08-where-attributes-really-live/o08.ipynb) |

## O09. Arrays of thirty bit digits

| Claim | Proved by |
| --- | --- |
| an int object grows by one fixed size digit at a time, and the size steps exactly at the powers of two that need another digit | [`o09-07`](o09-arrays-of-thirty-bit-digits/o09.ipynb) |
| the digits of an int can be extracted with a mask and a shift and summed back into the original number, because that is exactly what the storage format is | [`o09-10`](o09-arrays-of-thirty-bit-digits/o09.ipynb) |
| the digit count, the sign and the shared int flag are packed into one machine word so that a single comparison can decide whether the fast path applies | not observable from Python: lv_tag is not reachable from Python, and pyxray does not read raw struct fields. What the lesson can show is the consequence: everything below one digit behaves differently from everything above it. |
| integers in a fixed low range are shared objects rather than fresh allocations, so two separate computations that land on the same small value produce the same object | [`o09-12`](o09-arrays-of-thirty-bit-digits/o09.ipynb) |
| shared integers are immortal, so their reference count never changes, while an integer outside the range is refcounted normally | [`o09-15`](o09-arrays-of-thirty-bit-digits/o09.ipynb) |
| the two multiplication algorithms cost the same at the cutoff and diverge above it, which is why the cutoff sits where it does | [`o09-20`](o09-arrays-of-thirty-bit-digits/o09.ipynb) |
| converting a very long decimal string to an int, or the reverse, raises rather than running, and the limit can be raised at runtime | [`o09-22`](o09-arrays-of-thirty-bit-digits/o09.ipynb) |
| the hash of an integer is its remainder modulo a prime one less than a power of two, which is why a number equal to that modulus hashes to zero | [`o09-24`](o09-arrays-of-thirty-bit-digits/o09.ipynb) |

## O10. One string, four layouts

| Claim | Proved by |
| --- | --- |
| a string stores its characters in 1, 2 or 4 bytes each, chosen by the largest code point in the string, so adding one wide character widens every character in it | [`o10-07`](o10-one-string-four-layouts/o10.ipynb) |
| the characters of an ordinary string are stored inside the object, in the same allocation as the header, with a fixed overhead of 40 bytes for ASCII and 56 for everything else | [`o10-16`](o10-one-string-four-layouts/o10.ipynb) |
| a string's hash is the hash of its raw storage buffer, so it equals the hash of the same text encoded in whichever fixed width encoding matches the string's kind | [`o10-22`](o10-one-string-four-layouts/o10.ipynb) |
| a non-ASCII string can grow after it is created, because the first time C code asks for it as UTF-8 the encoded copy is stored on the object and counted by sys.getsizeof | [`o10-25`](o10-one-string-four-layouts/o10.ipynb) |
| string constants are interned only if they are ASCII and look like identifiers, while every name in co_names is interned and immortal | [`o10-28`](o10-one-string-four-layouts/o10.ipynb) |

## O11. Two sizes and a growth curve

| Claim | Proved by |
| --- | --- |
| a list is a fixed size object holding a pointer to a separately allocated array of item pointers, while a tuple holds its items inside the object itself | [`o11-07`](o11-two-sizes-and-a-growth-curve/o11.ipynb) |
| appending to a list allocates room for about an eighth more than it needs plus six, rounded down to a multiple of four, so the array is reallocated a logarithmic number of times rather than once per append | [`o11-11`](o11-two-sizes-and-a-growth-curve/o11.ipynb) |
| shrinking a list reallocates its array only when the new length falls below half of what is allocated, so deleting exactly half the items of a full list frees nothing | [`o11-20`](o11-two-sizes-and-a-growth-curve/o11.ipynb) |
| a tuple's hash is xxHash over the hashes of its items, computed once and cached in the object, which is what makes a tuple usable as a dict key | [`o11-24`](o11-two-sizes-and-a-growth-curve/o11.ipynb) |

## O12. The objects that come back

| Claim | Proved by |
| --- | --- |
| dropping an object and immediately building another of the same type usually hands you the same memory, because the type keeps a stash of dead objects rather than returning them to the allocator | [`o12-07`](o12-the-objects-that-come-back/o12.ipynb) |
| the reuse is per type rather than per size, so a dropped list can be reused as another list but never as a tuple of the same number of bytes | [`o12-09`](o12-the-objects-that-come-back/o12.ipynb) |
| each free list has a fixed cap, and a float free list fills to exactly a hundred no matter how many floats you drop | [`o12-15`](o12-the-objects-that-come-back/o12.ipynb) |
| the cap on a free list can be measured from Python, as the number of dropped objects a different type of the same size can reach | [`o12-19`](o12-the-objects-that-come-back/o12.ipynb) |
| tuples of one to twenty items each have their own free list, so two neighbouring sizes in that range never share memory even when the allocator would let them, while two neighbouring sizes above twenty do | [`o12-24`](o12-the-objects-that-come-back/o12.ipynb) |
| only exact instances of a type go on its free list, so a subclass of list or float is freed normally and the stash stays empty | [`o12-27`](o12-the-objects-that-come-back/o12.ipynb) |
| free lists are emptied by the cycle collector only when it collects the oldest generation, so gc.collect(0) leaves them full and a bare gc.collect() empties them | [`o12-30`](o12-the-objects-that-come-back/o12.ipynb) |

## O13. Pointing at something without holding it

| Claim | Proved by |
| --- | --- |
| creating a weak reference to an object leaves its reference count exactly where it was, while binding an ordinary name adds one | [`o13-07`](o13-pointing-without-holding/o13.ipynb) |
| a type supports weak references exactly when its __weakrefoffset__ is not zero, which is why list, dict, tuple, int and str all refuse | [`o13-09`](o13-pointing-without-holding/o13.ipynb) |
| adding __weakref__ to a class with __slots__ costs sixteen bytes rather than eight, because the pointer lives in a pre header that is allocated two words at a time | [`o13-12`](o13-pointing-without-holding/o13.ipynb) |
| asking twice for a weak reference with no callback gives you the same object back, while two with callbacks are always two separate objects | [`o13-15`](o13-pointing-without-holding/o13.ipynb) |
| by the time a weakref callback runs, every weak reference to the object has already been broken, so calling the reference it is handed always gives None | [`o13-17`](o13-pointing-without-holding/o13.ipynb) |
| a dropped bound method leaves its memory on a free list, so the next one lands on the same address, while a weak reference to the old one correctly reports it gone | [`o13-19`](o13-pointing-without-holding/o13.ipynb) |
| a weakref callback runs when the weak reference outlives the object, and is skipped when the weak reference is part of the same garbage being collected | [`o13-21`](o13-pointing-without-holding/o13.ipynb) |
| an exception raised inside a weakref callback is reported through sys.unraisablehook and does not propagate to whatever was running at the time | [`o13-23`](o13-pointing-without-holding/o13.ipynb) |

## O14. The last thing an object does

| Claim | Proved by |
| --- | --- |
| a __del__ method runs with every attribute of the object still set, because clearing happens after finalizers rather than before | [`o14-07`](o14-the-last-thing-an-object-does/o14.ipynb) |
| a weakref callback runs after __del__ when the reference count reached zero, and before __del__ when the cycle collector did the freeing | [`o14-09`](o14-the-last-thing-an-object-does/o14.ipynb) |
| a weak reference with no callback still finds the object during __del__ on the reference count path, and on 3.15 it does on the collector path too, which is a change from 3.14 | [`o14-11`](o14-the-last-thing-an-object-does/o14.ipynb) |
| a __del__ method that stores self cancels the deallocation, and the object is never finalized again because the finalized bit is set before the call rather than after | [`o14-14`](o14-the-last-thing-an-object-does/o14.ipynb) |
| a reference cycle whose objects have __del__ methods is collected normally, every finalizer runs, and gc.garbage stays empty | [`o14-16`](o14-the-last-thing-an-object-does/o14.ipynb) |
| if the finalizers in a cycle store self, that collection frees nothing, and a later one frees the objects without calling any finalizer again | [`o14-18`](o14-the-last-thing-an-object-does/o14.ipynb) |
| dropping a half consumed generator runs its finally block, and weakref.finalize gives the same effect for an ordinary object without defining __del__ | [`o14-20`](o14-the-last-thing-an-object-does/o14.ipynb) |

## T01. One line, seven stages

| Claim | Proved by |
| --- | --- |
| every token comes back with the line and the column range it was cut from, which is how a syntax error knows which characters to point at | [`t01-10`](t01-one-line-seven-stages/t01.ipynb) |
| INDENT and DEDENT are tokens the tokenizer works out from column numbers rather than characters it found | [`t01-12`](t01-one-line-seven-stages/t01.ipynb) |
| the multiplication is still a multiplication, with 6 and 7 sitting underneath it as two separate constants | [`t01-15`](t01-one-line-seven-stages/t01.ipynb) |
| the tree is an ordinary Python object, so you can change a node and compile the result | [`t01-17`](t01-one-line-seven-stages/t01.ipynb) |
| the symbol table is not private to the compiler, you can ask a stock interpreter for it and print the whole thing | [`t01-19`](t01-one-line-seven-stages/t01.ipynb) |
| a parameter is a local and nothing else, and a name that comes from the module is a global the function only ever reads | [`t01-21`](t01-one-line-seven-stages/t01.ipynb) |
| before the optimizer runs, `6 * 7` is still three instructions: load one constant, load the other, multiply them | [`t01-24`](t01-one-line-seven-stages/t01.ipynb) |
| the optimizer replaces those three instructions with a single one that loads 42 | [`t01-27`](t01-one-line-seven-stages/t01.ipynb) |
| CPython folds constants twice, in two places, on two different data structures | not observable from Python: the first pass runs on the tree inside a real compile() call, and the stage hook this lesson uses is handed a tree that has already skipped it, so nothing here can catch that one in the act |
| the code object holds everything the compiler worked out: the instructions, the table of constants, and how deep the value stack has to be for them | [`t01-32`](t01-one-line-seven-stages/t01.ipynb) |
| the constant table still contains the 6, and no instruction in the finished code ever loads it | [`t01-34`](t01-one-line-seven-stages/t01.ipynb) |
| the 42 never reaches the constant table, it rides inside the instruction as its argument | [`t01-34`](t01-one-line-seven-stages/t01.ipynb) |
| from 3.15 the implicit return None needs no entry in the constant table, because LOAD_COMMON_CONSTANT reads it from a table every code object shares | [`t01-36`](t01-one-line-seven-stages/t01.ipynb) |
| 42 lands in the namespace without your program multiplying anything | [`t01-38`](t01-one-line-seven-stages/t01.ipynb) |

## T02. Text becomes tokens

| Claim | Proved by |
| --- | --- |
| the tokenize module now calls into the C tokenizer through a small module called _tokenize, rather than reimplementing it in Python | [`t02-08`](t02-text-becomes-tokens/t02.ipynb) |
| ENCODING, INDENT, DEDENT and ENDMARKER are all added by the tokenizer and appear nowhere in the text you wrote | [`t02-15`](t02-text-becomes-tokens/t02.ipynb) |
| `if` comes back as a NAME rather than as a keyword, the same kind of token as `answer` or `print` or `banana` | [`t02-17`](t02-text-becomes-tokens/t02.ipynb) |
| `match` is an ordinary NAME to the tokenizer, which is what lets it be a keyword in one place in the grammar and a variable name everywhere else | [`t02-19`](t02-text-becomes-tokens/t02.ipynb) |
| every operator and every piece of punctuation comes back as the same token type, OP, with which operator it was recorded separately | [`t02-21`](t02-text-becomes-tokens/t02.ipynb) |
| the two are not symmetric: INDENT carries the spaces it covers and DEDENT is zero characters wide | [`t02-23`](t02-text-becomes-tokens/t02.ipynb) |
| going right produces exactly one INDENT however far right you went, and going left produces one DEDENT for every level you closed | [`t02-25`](t02-text-becomes-tokens/t02.ipynb) |
| the whole of Python's indentation is a stack of column numbers and three comparisons, and the stack column is enough to follow every one of them | [`t02-28`](t02-text-becomes-tokens/t02.ipynb) |
| a line that closes three blocks is remembered across three calls, in a counter the tokenizer decrements one dedent at a time | not observable from Python: pendin is a field on the C tokenizer state, and all the token stream shows is three dedents arriving in a row with nothing to say how they were held |
| blank lines and comment only lines are thrown out before any indentation comparison happens, so a comment indented to a ridiculous column breaks nothing | [`t02-32`](t02-text-becomes-tokens/t02.ipynb) |
| a tab moves to the next multiple of eight, so what a tab is worth depends on what came before it | [`t02-34`](t02-text-becomes-tokens/t02.ipynb) |
| every line is measured twice, once with a tab stop of 8 and once with a tab stop of 1, and only a line with a tab in it gets two different answers | [`t02-37`](t02-text-becomes-tokens/t02.ipynb) |
| two lines that agree on the real count and disagree on the alternate count are refused, because their agreement was luck rather than intent | [`t02-39`](t02-text-becomes-tokens/t02.ipynb) |
| closing a block to a column nothing ever opened at is an error, because the stack runs out before it finds a match | [`t02-41`](t02-text-becomes-tokens/t02.ipynb) |
| an unclosed bracket raises TokenError rather than SyntaxError, and carries its position in its arguments rather than as attributes | [`t02-43`](t02-text-becomes-tokens/t02.ipynb) |
| a line ending inside brackets comes back as NL rather than NEWLINE, and the five spaces in front of the next line produce no INDENT at all | [`t02-47`](t02-text-becomes-tokens/t02.ipynb) |
| the token stream tokenize hands you is bigger than the one the compiler works from, because comments and the newlines inside brackets are dropped before the parser | [`t02-49`](t02-text-becomes-tokens/t02.ipynb) |
| a backslash continuation produces no token at all, not even a marker, and the only trace left is the tokens jumping from line 1 to line 2 in the middle of an expression | [`t02-51`](t02-text-becomes-tokens/t02.ipynb) |
| an f-string comes out as several tokens, with the expression between the braces tokenized as ordinary Python | [`t02-53`](t02-text-becomes-tokens/t02.ipynb) |
| template strings get their own token kinds rather than borrowing the f-string ones | [`t02-57`](t02-text-becomes-tokens/t02.ipynb) |

## T03. Tokens become a tree

| Claim | Proved by |
| --- | --- |
| the tree is the first thing in the pipeline that knows `6 * 7` is one thing rather than three, with both numbers hanging underneath a single BinOp | [`t03-08`](t03-tokens-become-a-tree/t03.ipynb) |
| the ASDL declaration of a node type is carried around as the docstring of the class, which means printing it gives you the definition itself rather than somebody's description of it | [`t03-12`](t03-tokens-become-a-tree/t03.ipynb) |
| the operators are a closed list of cases rather than nodes with fields, so Mult has no fields at all | [`t03-14`](t03-tokens-become-a-tree/t03.ipynb) |
| brackets, spacing and a trailing comment make no difference to the tree: three differently written files give one identical tree, field for field | [`t03-17`](t03-tokens-become-a-tree/t03.ipynb) |
| the tokenizer hands the parser both brackets as ordinary tokens, and the parser is where they stop existing | [`t03-19`](t03-tokens-become-a-tree/t03.ipynb) |
| the same five tokens in the same order give two different trees, because what the brackets did is kept as shape | [`t03-21`](t03-tokens-become-a-tree/t03.ipynb) |
| every node that was written somewhere carries the line and column range it covers | [`t03-24`](t03-tokens-become-a-tree/t03.ipynb) |
| a node with no fields has no position either, so there is nothing in the tree that says where the `*` was | [`t03-24`](t03-tokens-become-a-tree/t03.ipynb) |
| unparse gives back source that means the same thing rather than the source you wrote: 0x2a comes back as 42 and the underscores in 1_000_000 are gone | [`t03-27`](t03-tokens-become-a-tree/t03.ipynb) |
| adjacent string literals are glued together by the grammar, so 'a' 'b' is already one string before anything runs | [`t03-27`](t03-tokens-become-a-tree/t03.ipynb) |
| parse a file, unparse it, parse the result, and you get an identical tree, for every module in your own standard library | [`t03-30`](t03-tokens-become-a-tree/t03.ipynb) |

## T04. Names get scopes

| Claim | Proved by |
| --- | --- |
| a function that only reads a name finds the module's copy of it, so calling it prints the module's value | [`t04-08`](t04-names-get-scopes/t04.ipynb) |
| the same line of source compiled to two different instructions in two functions in one file, and both were settled before either function ran | [`t04-13`](t04-names-get-scopes/t04.ipynb) |
| the symtable module reports the same name as local in one function and not local in another, from the one file | [`t04-16`](t04-names-get-scopes/t04.ipynb) |
| every name in a block gets exactly one decision, and that decision is what picks the instruction | [`t04-19`](t04-names-get-scopes/t04.ipynb) |
| the finished code object has no field saying what scope a name had, so the choice of instruction is the only record of it | not observable from Python: what would show it is the absence of a field on the code object, and no cell can print a thing that is not there |
| a global statement beats an assignment in the same block, so a name assigned inside a function that declares it global is compiled as a global anyway | [`t04-22`](t04-names-get-scopes/t04.ipynb) |
| a global statement inside a function changes the instruction used for an assignment at module level, on a line above the function | [`t04-25`](t04-names-get-scopes/t04.ipynb) |
| a name shared by two functions is a cell in the one that owns it and a free variable in the one that uses it, and both read it with LOAD_DEREF | [`t04-28`](t04-names-get-scopes/t04.ipynb) |
| the cell outlives the frame that made it, so the count kept by a returned closure survives from one call to the next | [`t04-30`](t04-names-get-scopes/t04.ipynb) |
| the same two lines compile to different instructions in a class body and in a function, because a class body looks names up in a dictionary and a function uses numbered slots | [`t04-33`](t04-names-get-scopes/t04.ipynb) |
| the compiler only pays for the checked load where a read could come first, and a name assigned before it is read gets the plain fast load | [`t04-36`](t04-names-get-scopes/t04.ipynb) |
| a comprehension in a class body can read the first iterable from the class and nothing else, so rows resolves and factor raises NameError three lines later | [`t04-41`](t04-names-get-scopes/t04.ipynb) |

## T05. The tree becomes bytecode

| Claim | Proved by |
| --- | --- |
| a stock CPython exports the first two compiler stages as callable functions, in a module called _testinternalcapi that ships with the interpreter | [`t05-08`](t05-the-tree-becomes-bytecode/t05.ipynb) |
| The multiplication in 6 * 7 happens while the file is being compiled, and no multiply instruction survives into the finished program | [`t05-12`](t05-the-tree-becomes-bytecode/t05.ipynb) |
| the compiler is not simulating the multiplication, it is doing it with the same C function your program would have called | not observable from Python: the call happens in C while the file is being compiled, and nothing in the finished code object records that it took place |
| the 42 is not in the constants table | [`t05-15`](t05-the-tree-becomes-bytecode/t05.ipynb) |
| 6 is still in the constants table with nothing loading it | [`t05-17`](t05-the-tree-becomes-bytecode/t05.ipynb) |
| there is no such instruction as ANNOTATIONS_PLACEHOLDER outside the compiler | [`t05-19`](t05-the-tree-becomes-bytecode/t05.ipynb) |
| SETUP_FINALLY and SETUP_CLEANUP are pseudo instructions, and both of them survive the optimizer | [`t05-21`](t05-the-tree-becomes-bytecode/t05.ipynb) |
| the optimizer's first move is to cut the instruction list into basic blocks and join them with edges wherever a jump goes | not observable from Python: the graph is built, used and thrown away inside the compiler, and is never handed back to Python in any form |
| The entire body of an if False block is removed before the file is written | [`t05-23`](t05-the-tree-becomes-bytecode/t05.ipynb) |
| the string inside the if False block is not in the code object's constants table | [`t05-25`](t05-the-tree-becomes-bytecode/t05.ipynb) |
| A list literal that is only iterated over is built once at compile time and stored as a constant tuple | [`t05-27`](t05-the-tree-becomes-bytecode/t05.ipynb) |
| 2 ** 65 is not folded, even though the answer is only a 66 bit number | [`t05-30`](t05-the-tree-becomes-bytecode/t05.ipynb) |
| 1 / 0 is left for runtime because evaluating it raised, and a % on a string is left alone on purpose | [`t05-32`](t05-the-tree-becomes-bytecode/t05.ipynb) |
| Folding stops the moment either side of the operator is a name | [`t05-34`](t05-the-tree-becomes-bytecode/t05.ipynb) |
| a code object's bytes come in pairs, one byte of opcode and one byte of argument | [`t05-36`](t05-the-tree-becomes-bytecode/t05.ipynb) |
| a traceback finds its line number by looking a byte offset up in a table that is stored separately from the instructions | [`t05-38`](t05-the-tree-becomes-bytecode/t05.ipynb) |
| a try block leaves no instruction behind in the bytecode, only an entry in a table | [`t05-40`](t05-the-tree-becomes-bytecode/t05.ipynb) |

## T06. Reading bytecode fluently

| Claim | Proved by |
| --- | --- |
| a line like total = total + 1 pushes two values, replaces them with one, and leaves the stack as empty as it found it | [`t06-07`](t06-reading-bytecode-fluently/t06.ipynb) |
| every offset in a listing is even: the bytes of a code object come in pairs and there is nothing else in there | [`t06-10`](t06-reading-bytecode-fluently/t06.ipynb) |
| the same argument byte means a different thing for every instruction, and which thing is published by the opcode module rather than worked out from the number | [`t06-12`](t06-reading-bytecode-fluently/t06.ipynb) |
| a packed load carries two slot numbers in one byte, four bits each, so the argument 18 means slots 1 and 2 | [`t06-16`](t06-reading-bytecode-fluently/t06.ipynb) |
| an argument bigger than 255 is carried by an EXTENDED_ARG in front of the instruction, which shifts what it holds left by eight and adds the next argument on | [`t06-18`](t06-reading-bytecode-fluently/t06.ipynb) |
| inline caches are real bytes in co_code that the offsets step over, and dis leaves them out of a listing unless you ask for them | [`t06-21`](t06-reading-bytecode-fluently/t06.ipynb) |
| a jump argument counts instructions rather than bytes, and it counts from after the jump including the jump's own cache slot | [`t06-23`](t06-reading-bytecode-fluently/t06.ipynb) |
| the interpreter never multiplies a jump by two, because next_instr points at a two byte unit and C's pointer arithmetic does the doubling | not observable from Python: the doubling is in the type of a C pointer, and the only thing that reaches Python is the finished offset |
| there are no absolute jumps left at all, and every jump instruction is relative | [`t06-25`](t06-reading-bytecode-fluently/t06.ipynb) |
| how many values an instruction pops and pushes is written down for every one of them, and dis.stack_effect hands back the net of the two | [`t06-27`](t06-reading-bytecode-fluently/t06.ipynb) |
| a handler starts at a stack height the instruction above it did not leave behind, because nothing falls into a handler from the line above | [`t06-30`](t06-reading-bytecode-fluently/t06.ipynb) |
| the Python version of the stack depth rule in this lesson agrees with CPython's own co_stacksize on every code object it is run over | [`t06-32`](t06-reading-bytecode-fluently/t06.ipynb) |
| a function that never pushes anything still reports a stack size of one, because a computed zero is bumped up to one | [`t06-35`](t06-reading-bytecode-fluently/t06.ipynb) |
| a listing on its own is enough to work out what a function does, and the source it was compiled from agrees | [`t06-39`](t06-reading-bytecode-fluently/t06.ipynb) |

## T07. The machine runs

| Claim | Proved by |
| --- | --- |
| a build records which dispatch strategy it was compiled with, so you can ask your own interpreter rather than guess | [`t07-08`](t07-the-machine-runs/t07.ipynb) |
| Python calling Python only grows the interpreter's own frame stack, so ninety thousand deep is fine, while going out through a C function and back in runs out of the real C stack after a few thousand | [`t07-14`](t07-the-machine-runs/t07.ipynb) |
| the events a tool can ask for are a fixed published list on sys.monitoring.events, and four of the six tool ids are already spoken for | [`t07-18`](t07-the-machine-runs/t07.ipynb) |
| a frame that leaves because of an exception is reported by a different event than one that returns, so an unwinding stack can be watched one frame at a time | [`t07-20`](t07-the-machine-runs/t07.ipynb) |
| not every monitoring event can be turned on for a single code object, and which ones can changed between 3.14 and 3.15 | [`t07-22`](t07-the-machine-runs/t07.ipynb) |
| nothing in the standard library can read the values sitting on the value stack | not observable from Python: what would show it is the absence of a door, and the cells below demonstrate the way around it rather than the missing thing |
| the deepest the stack gets on a real run is exactly the co_stacksize the compiler wrote down | [`t07-25`](t07-the-machine-runs/t07.ipynb) |
| END_FOR is compiled into the loop and never reported to instrumentation, so an instruction that certainly ran is missing from the recording | [`t07-29`](t07-the-machine-runs/t07.ipynb) |
| the branch events report only the places control could have gone two ways, and say which way it went, so a two item loop is five reports rather than twenty seven | [`t07-31`](t07-the-machine-runs/t07.ipynb) |
| returning DISABLE turns an event off at one code location rather than everywhere, so a five pass loop reports each instruction once instead of five times | [`t07-34`](t07-the-machine-runs/t07.ipynb) |
| sys.settrace has no way to be switched off at one place, so every line of every pass through a loop costs a callback | [`t07-36`](t07-the-machine-runs/t07.ipynb) |
| asking for the frame twice gives back the same object, and that object is still usable after the call it belonged to has returned | [`t07-38`](t07-the-machine-runs/t07.ipynb) |
| writing through f_locals changes the actual local variable and writing to the dictionary locals() hands back changes nothing | [`t07-40`](t07-the-machine-runs/t07.ipynb) |
| every frame keeps a pointer to the one that called it, and walking that chain from the inside out is all a traceback is | [`t07-42`](t07-the-machine-runs/t07.ipynb) |

## T08. Everything is an object

| Claim | Proved by |
| --- | --- |
| every object in a running Python starts with the same two fields, a reference count and a pointer to its type | not observable from Python: the two fields are members of a C struct, and Python only ever gets handed the object on the far side of them |
| an integer, a string, a dictionary and a plain function all answer the same four questions, because all four are objects | [`t08-11`](t08-everything-is-an-object/t08.ipynb) |
| two lists built from the same three numbers are equal and are not the same object | [`t08-14`](t08-everything-is-an-object/t08.ipynb) |
| the top of the small integer cache moved in 3.15, so the 256 that every tutorial quotes is the old number | [`t08-17`](t08-everything-is-an-object/t08.ipynb) |
| where the sharing stops can be measured from Python, by walking outward from zero until two equal integers stop being the same object | [`t08-17`](t08-everything-is-an-object/t08.ipynb) |
| two identical integer literals in one piece of source become one object however big the number is, which is the compiler keeping each distinct constant once and has nothing to do with the small integer cache | [`t08-20`](t08-everything-is-an-object/t08.ipynb) |
| building the same integer twice through int() rather than writing it as a literal does show the cache, and the sharing stops once the value is past the top of it | [`t08-23`](t08-everything-is-an-object/t08.ipynb) |
| a string is interned only when it is ASCII and shaped like an identifier, which puts append and _private in the table and leaves hello world out of it | [`t08-26`](t08-everything-is-an-object/t08.ipynb) |
| a string built at runtime is not interned even when it is shaped like an identifier, and sys.intern puts it in the table and hands back the object that is in there | [`t08-28`](t08-everything-is-an-object/t08.ipynb) |
| sys.getrefcount gives a different answer for a local and a global that each hold one list, because loading a local borrows the reference and loading a global takes one | [`t08-31`](t08-everything-is-an-object/t08.ipynb) |
| every container holding an object holds a reference of its own, so putting one list inside another list twice raises its count by two and clearing that list drops it back | [`t08-33`](t08-everything-is-an-object/t08.ipynb) |
| Python can be asked which objects are holding a value, and at the top level of a notebook one of the answers is always the module's own namespace | [`t08-35`](t08-everything-is-an-object/t08.ipynb) |
| None, True, the small integers and the type objects have their reference count parked, so sys.getrefcount reports an enormous number for them that is not counting anything | [`t08-37`](t08-everything-is-an-object/t08.ipynb) |
| a list costs one pointer per slot, so what an extra item adds is the size of an address on your machine and not the size of the thing you put in | [`t08-41`](t08-everything-is-an-object/t08.ipynb) |
| sys.getsizeof reports an object's own bytes and nothing it points at, so a list of three tiny integers and a list of three enormous ones come out the same size | [`t08-44`](t08-everything-is-an-object/t08.ipynb) |

## T09. Memory appears and disappears

| Claim | Proved by |
| --- | --- |
| binding an object to a name adds one to its count and putting it in a container adds another, and dropping either takes one away again | [`t09-10`](t09-memory-appears-and-disappears/t09.ipynb) |
| a weak reference lets you watch an object go without keeping it alive, because it is the one kind of reference that does not add to the count | [`t09-12`](t09-memory-appears-and-disappears/t09.ipynb) |
| a finalizer runs at the del itself, so its output lands in the middle of the surrounding prints rather than at the end of the function or the end of the program | [`t09-14`](t09-memory-appears-and-disappears/t09.ipynb) |
| two objects that hold each other keep each other's count above zero after every name to them has gone, and counting alone never frees either one | [`t09-17`](t09-memory-appears-and-disappears/t09.ipynb) |
| running gc.collect() by hand frees a pair that dropping their names did not | [`t09-17`](t09-memory-appears-and-disappears/t09.ipynb) |
| gc.get_referents plus a search for strongly connected components finds the same groups of objects that can all reach each other, which is what heap.cycles does | [`t09-21`](t09-memory-appears-and-disappears/t09.ipynb) |
| a cycle whose members define __del__ is collected like any other, with every finalizer run and gc.garbage left empty | [`t09-23`](t09-memory-appears-and-disappears/t09.ipynb) |
| the collector sorts objects into three groups by how long they have survived, and Python can be asked which group any object is in | [`t09-26`](t09-memory-appears-and-disappears/t09.ipynb) |
| an object starts in the youngest group and moves up one place each time it survives a sweep | [`t09-26`](t09-memory-appears-and-disappears/t09.ipynb) |
| the collector does not track an object that cannot hold a reference to another object, so an integer or a string is in no generation at all | [`t09-28`](t09-memory-appears-and-disappears/t09.ipynb) |
| requests over 512 bytes go to the system allocator, and everything under that is rounded up to one of a fixed set of sizes | [`t09-31`](t09-memory-appears-and-disappears/t09.ipynb) |
| one surviving object anywhere in an arena keeps the whole arena, which is why a process that peaked at two gigabytes usually still looks like it is using two gigabytes afterwards | not observable from Python: an arena is not an object and Python has no way to name one, and how much memory the operating system thinks the process holds is not a number the standard library reports |
| building ten thousand objects and then dropping them brings the count of blocks in use back to roughly where it started | [`t09-34`](t09-memory-appears-and-disappears/t09.ipynb) |
| freeing an object and immediately building another of the same size usually puts the new one at the address the old one had | [`t09-37`](t09-memory-appears-and-disappears/t09.ipynb) |

## T10. The napkin

| Claim | Proved by |
| --- | --- |
| the entire middle band is one enormous C function, which is why there is a single place to point at for it | not observable from Python: it is a C function, and the only thing that reaches Python from it is the result of running the instruction |
| a function still runs after its source text has been destroyed, because the code object is the only thing that crosses from compile time to run time | [`t10-10`](t10-the-napkin/t10.ipynb) |
| the compiler works out the deepest the value stack can ever get and writes the number into the code object, and nothing recomputes it later | [`t10-10`](t10-the-napkin/t10.ipynb) |
| every stage from the token stream to the finished code object can be printed with the standard library, with no debug build and no C compiler anywhere | [`t10-13`](t10-the-napkin/t10.ipynb) |
| compile() with no file on disk anywhere still produces bytecode, so a pyc file is a cache of that work rather than the compilation itself | [`t10-16`](t10-the-napkin/t10.ipynb) |
| a local name is stored and loaded by slot number rather than looked up in a dictionary, and the name survives only so a traceback has something to print | [`t10-16`](t10-the-napkin/t10.ipynb) |
| an object is still freed with the cycle collector switched off, because reference counting is what frees almost everything | [`t10-16`](t10-the-napkin/t10.ipynb) |
| del removes one name rather than the object, so a second name holding the same object keeps it alive | [`t10-16`](t10-the-napkin/t10.ipynb) |
| two 257 literals in one source file are the same object because of the compiler, and building them one at a time from a string is what actually shows the small integer cache | [`t10-19`](t10-the-napkin/t10.ipynb) |

## Z01. C for people who will only ever read C

| Claim | Proved by |
| --- | --- |
| a Python list is five fields and nothing else: a reference count, a type pointer, a size, an arrow to the slot array, and a count of how many slots exist | not observable from Python: the five fields are a C struct, and Python is only ever handed the list rather than its layout |
| PyList_SET_ITEM steals, which is why list_append_impl creates a reference with Py_NewRef before handing the object over rather than passing it straight through | not observable from Python: who owns a reference is a contract between two C functions, and Python sees only the count that comes out of the other end |
| appending an object to a list adds one to its reference count, because the list takes a reference of its own | [`z01-11`](z01-reading-c/z01.ipynb) |
| popping it back out hands over the reference the list was holding rather than making a fresh one, so the count does not go up again | [`z01-11`](z01-reading-c/z01.ipynb) |
| a list that runs out of room asks for one eighth more than it needs plus six, rounded down to a multiple of four, which gives the sequence 4, 8, 16, 24, 32, 40, 52, 64, 76, 92 | [`z01-16`](z01-reading-c/z01.ipynb) |
| that line of C can be transcribed into Python and it then agrees with a real list on every one of two thousand appends | [`z01-16`](z01-reading-c/z01.ipynb) |

## Z02. How to be lost productively

| Claim | Proved by |
| --- | --- |
| your own machine already has the Lib half of that tree on disk, a few hundred thousand lines of it, and you can find and count it without downloading anything | [`z02-07`](z02-being-lost/z02.ipynb) |
| about a third of the C in the tree, 371,643 lines of it across 206 files, is produced by a script when CPython is built | not observable from Python: the count is over a checkout of CPython, and this lesson deliberately does not download one |
| a generated file says so in its own first three lines, and usually names both the script that wrote it and the file it was written from, which is enough to find every one of them in your own standard library | [`z02-09`](z02-being-lost/z02.ipynb) |
| _opcode_metadata.py in your own standard library is generated from Python/bytecodes.c, the same input as the biggest generated C file in the tree | [`z02-11`](z02-being-lost/z02.ipynb) |
| a map of about ten keyword rules is enough to answer most questions about where in CPython to look, with one row left over for the ones it misses | [`z02-16`](z02-being-lost/z02.ipynb) |
| a standard library module written in Python with a C accelerator behind it is called thing with the accelerator called _thing, and the running interpreter names both halves of every pair | [`z02-18`](z02-being-lost/z02.ipynb) |
| whether a module written in C is linked into the interpreter or loaded from a file beside it is a build choice rather than a fact about Python, so the same module can have a file on one install and none on another | [`z02-21`](z02-being-lost/z02.ipynb) |
| each entry carries the issue number in its metadata, which is the link from a line of code to the argument about why the line is there | [`z02-28`](z02-being-lost/z02.ipynb) |
