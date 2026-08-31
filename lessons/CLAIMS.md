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

185 claims across 18 lessons, 18 of them not observable from Python.

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
