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

51 claims across 12 lessons, 4 of them not observable from Python.

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

Not marked up yet.

## T04. Names get scopes

Not marked up yet.

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

Not marked up yet.

## T07. The machine runs

Not marked up yet.

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
