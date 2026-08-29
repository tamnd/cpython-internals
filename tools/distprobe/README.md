# distprobe

Asks every Python a reader is likely to be holding whether it ships `_testinternalcapi`, and records the answer instead of guessing at it.

The compiler lessons take a reader through CPython's front end one stage at a time: source to AST, AST to an unoptimised control flow graph, graph to a code object. They do that without asking anybody to build CPython, by calling `compiler_codegen`, `optimize_cfg` and `assemble_code_object` on `_testinternalcapi`. That module is private, it has no compatibility promise, and it is not part of what a distribution has to ship. So the lessons rest on a fact about packaging that nobody had checked.

They do not all ship it. Fedora's `python3` does not, which is the finding this tool exists to have found, and it is a surprise because Fedora ships a newer Python than almost anybody else.

## Running it

```
just dist
```

The fast half, and the one in `just check`. It reads the committed survey, prints the counts, names the channels a reader would trip over, and fails when the report has fallen behind the recording. It reads one JSON file, so it needs nothing and takes no time.

It does not fail because a distribution said no. A build that went red every time somebody ran it would not change how Fedora packages Python, and after a week nobody would read the failure.

```
just build-dist
```

Asks everything again and rewrites the report. Needs Docker running. It pulls half a dozen images and runs a package manager inside most of them, so it is several minutes on a cold cache and rather longer on a cold network.

```
uv run distprobe list
uv run distprobe question
```

`list` prints the channels and whether this machine can reach them. `question` prints the source of the question, which is for the two channels this machine cannot reach: somebody on a Windows box can paste it into their own Python and send back the one line it prints.

## The one distinction everything rests on

A channel that could not be reached and a channel that answered no are different things, and they are kept apart everywhere in here. Docker not being installed is our problem. Fedora not packaging a module is Fedora's answer. A table that ran those together would be worse than no table at all, because the row worth reading would be indistinguishable from the broken one. That is why `Answer` has an `unreachable` field separate from its `internal` field, why the report has a `not measured` verdict next to `no module`, and why an unmeasured channel is not counted as a problem.

## What is in here

`question.py` holds the question as a string of Python, plus the types the answer is read back into. The source imports only `json`, `sys` and `sysconfig`, because it has to run on the Pythons where the answer is no and it cannot depend on the thing it is asking about. It prints one line beginning `DISTPROBE `, which is how the answer is found in the middle of several screens of package manager output.

`channels.py` is the list: three interpreters on this machine, six container images, and three that cannot be answered from here. The three that cannot are on the list anyway, each with a note saying what would answer it, because leaving them off would make the table look finished.

`run.py` builds the commands and collects the answers. The question reaches a container base64 encoded. Not for secrecy: a container is reached through `sh -c`, the source has quotes and newlines in it, and every layer of quoting in between is a chance to mangle it in a way that shows up as a syntax error blamed on the distribution. Bind mounting the file instead was tried first and Docker Desktop mounted the single file as a directory.

`borrowed.py` takes the Pyodide row out of the `wasmprobe` recording rather than measuring it a second time, so the two probes cannot end up disagreeing about what the browser said.

`report.py` renders the table. Every row says what happened rather than yes or no, because a tick would hide the two rows the table exists for: the one where the module is there and the functions are not, and the one where a second package fixes it. There is a column for the command a reader types, so somebody who just hit an ImportError can find their own row by recognising it.

## The results

They live in `probes/distributions` at the top of the repository: `answers.json` is the recording, `report.md` is generated from it, and `decision.md` is the written half of gate 4, which says what the lessons do about the channels that answered no.

## Containers, and one architecture

The container rows pin the distribution rather than whatever is installed on the laptop running this, so the answer is about Debian and not about one person's Debian. They run as one architecture, taken from the machine and written into the recording. Nothing found so far packages this differently on arm64 and amd64, but a recording that did not say which one it measured could not tell you that.
