# refcheck

Every claim this project makes about CPython points at a specific region of a specific tagged tree. refcheck is what stops those pointers from going stale without anyone noticing.

That is not a hypothetical failure. It is the one that has made every other CPython explainer wrong. A resource written against 3.8 says the small integer cache runs from -5 to 256, and it was right, and then 3.15 changed the bound to 1024 and nothing anywhere told the author. A reader who finds one wrong claim reasonably stops trusting the other four hundred.

## The citation format

```
Objects/listobject.c:1232@v3.15.0rc1
Objects/listobject.c:1232-1240@v3.15.0rc1
Objects/listobject.c:1232-1240@v3.15.0rc1#list_append_impl
```

A path relative to the root of the CPython tree, a line or a line range, the tag the line numbers are true for, and optionally the name of the thing that is supposed to be there.

The trailing symbol is the part that does the work. A line number on its own drifts silently the moment upstream inserts a function above it, and the citation now points at something plausible and wrong, which is worse than pointing at nothing. A line number plus a name fails loudly instead, and the failure says where the name actually went.

Citations are written inline in prose, in notebook cells and in blueprints. The scanner reads Markdown, Python, notebooks and configuration files, and ignores notebook outputs, because a citation that only appears in a stored output is one nobody wrote.

## What gets checked

| Status | What it means |
|---|---|
| `wrong-tag` | The citation names a tag that is not what the tree is pinned to |
| `missing-file` | The path is not in the tree |
| `out-of-range` | The file is shorter than the citation claims |
| `symbol-not-found` | The named symbol is not in the cited lines, and here is where it really is |
| `too-long` | More than 40 lines cited, which means the author is pasting rather than pointing |
| `not-in-lock` | A new citation that no human has confirmed yet |
| `digest-mismatch` | The region changed since the lockfile was written |

The digest covers the cited lines plus five lines of context on each side. Context is included so that a function inserted immediately above a citation is caught, which is the most common way a line number goes wrong and the least likely to be noticed by eye.

Trailing whitespace is stripped before hashing because it changes for reasons unrelated to meaning. Nothing else is normalised. An indentation change in CPython is a real change to the thing being pointed at and the author should look at it.

## Using it

```
just vendor                                     # fetch the pinned tree, about 200 MB
just citations                                  # verify everything
just recheck                                    # re-baseline after reading the diff
just show Include/object.h:127-149@v3.15.0rc1   # print the lines, to confirm by eye
just url Include/object.h:127@v3.15.0rc1        # the clickable permalink
```

`recheck` is deliberately not part of `just check`. A checker that silently repairs itself checks nothing, so updating the lockfile is always an explicit act by a person who has read what changed.

The lockfile stores the first cited line as plain text next to each digest. That is there for whoever reviews the diff. A lockfile of nothing but hashes tells a reviewer that something moved but not what, and a reviewer who cannot see what moved approves the update without reading it.

## Where the tree comes from

In order: the `--tree` argument, then `CPYTHON_SRC`, then `vendor/cpython`. The environment variable exists so that somebody who already has a CPython checkout does not have to keep a second copy, and so CI can point at a cached one.

The tests skip rather than fail when no tree is present. Somebody changing the citation parser should not need 200 MB of CPython on disk to run the tests that cover it, and CI always has the tree, so the tests that need it always run somewhere.

## Testing

The resolver tests run against a real checkout of `v3.15.0rc1` and assert on real content, including that `_PY_NSMALLPOSINTS` is 1025 at the line we cite for it. They are not mocked, on purpose. The entire value of this tool is that it agrees with the actual tree, and a test suite that agrees with a fixture instead proves nothing about the thing the tool exists to do.
