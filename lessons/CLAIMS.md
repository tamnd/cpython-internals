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

102 claims across 12 lessons, 7 of them not observable from Python.

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

Not marked up yet.

## T09. Memory appears and disappears

Not marked up yet.

## T10. The napkin

Not marked up yet.

## Z01. C for people who will only ever read C

Not marked up yet.

## Z02. How to be lost productively

Not marked up yet.
