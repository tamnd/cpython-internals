# cpybuild

Five ways of building CPython, compiled once in CI and pulled by digest everywhere else, so that nobody in this project ever has to have a working C toolchain to see what a debug build says.

## Why five

A lot of what the lessons observe is a property of the binary and not of the language. The reference count of a small integer, whether an object is immortal, how many bytes a dict occupies, what the eval loop looks like when you step into it: change how CPython was configured and some of those change with it. The material would rather show a reader that than pretend there is one true answer, and to show it, it needs the same commit built more than one way.

| Build | What it is for |
|---|---|
| `debug` | `--with-pydebug --with-assertions`. `sys.gettotalrefcount` exists here and nowhere else. Two to three times slower, so no timing in the material is ever taken on it. |
| `release` | No configure flags at all. The control, and what almost every reader is running. |
| `freethreaded` | `--disable-gil`. A different object header, split reference counts, a different collector. |
| `jit` | `--enable-experimental-jit`. Needed to run a tier 2 trace rather than describe one. |
| `tailcall` | `--with-tail-call-interp`, built with Clang. The eval loop as a chain of tail calls instead of one enormous switch. |

Each is built for amd64 and arm64, because half the readers are on an Apple laptop and half are on an x86 box, and a number measured on one of those is not automatically true on the other.

## Running it

```
just images
```

The fast half. It reads the committed lockfile and says whether it still describes this project: every build present for both architectures, every digest shaped like a digest, and the whole thing recorded against the CPython commit the citations are pinned to. Offline and instant, because a check that needs the network is a check that fails on a train.

Not part of `just check` yet. There is no lockfile until the workflow has run once and its pull request has been merged, and a recipe that passes because the file it reads does not exist is worse than no recipe.

```
just build-image debug
```

Builds one configuration locally, for when you are changing the Dockerfile. Fifteen to twenty five minutes cold, a couple of minutes warm, and it does not push anything.

Everything else is the `cpython-images` workflow. It runs weekly, on any change under `patches/`, and on a button. Nothing else in the repository ever compiles CPython.

## Pulling one

```
docker run --rm -it $(uv run cpybuild reference debug) python3
```

`reference` prints `ghcr.io/tamnd/cpython-internals/cpython:debug@sha256:...`, which pulls by digest and still says which build it is when a person reads it. Use the digest rather than the tag anywhere the answer matters. A tag is a name somebody can move, and an experiment that silently ran against a different binary than the one it was written for is worse than an experiment that failed.

A devcontainer that does this for you, so that opening the repository puts you in the debug build with the source and gdb already there, is the next piece and is not written yet.

## The lockfile

`images/cpython.lock.json` at the top of the repository is the record: ten digests, when each was built, and the CPython tag and commit they were built from. It is generated, and it is committed, the same way the citation lockfile and the probe recordings are.

The workflow does not push it to `main`. It opens a pull request, because a bot moving a digest under a protected branch is not something anybody wants to discover after the fact, and because the diff is the only place the weekly rebuild is visible. The CPython commit never moves, so a change in there is Debian moving underneath: a patched OpenSSL, a newer libc.

## What is in here

`configs.py` is the list of five and the reason each one is on it. It lives here rather than in the workflow because two copies of a matrix drift, and the copy in YAML is the one nobody runs locally. `cpybuild matrix` prints it as JSON and the workflow reads that, so adding a sixth build is a change to this file and nothing else.

`images.py` is the lockfile: reading it, writing it sorted so a rebuild is a readable diff, and `problems()`, which returns everything wrong with it at once rather than the first thing. Reporting one of eight missing builds would mean eight runs of a twenty minute job.

`cli.py` has two audiences that want opposite things. A person wants to see the builds and what they are for. A workflow wants one string on standard output with nothing around it, so it can put it in a shell variable. Every subcommand a workflow uses prints one thing and nothing else, and there is a test for each saying so.

## The Dockerfile

`images/cpython/Dockerfile` at the top of the repository, two stages. The build stage installs the packages `cpybuild packages` names, fetches the pinned commit blobless and shallow, applies anything in `patches/`, and compiles with `ccache` on a buildkit cache mount. The final stage is `debian:trixie-slim` with only the runtime libraries, so the compiler and the two hundred megabytes of headers do not travel.

The release image comes out around 700 MB unpacked on arm64, and most of that is CPython rather than Debian: 170 MB of the `test` package, 80 MB of static library, and a 37 MB binary that still has its debug symbols. Nothing is trimmed out of it beyond one duplicate. `make install` leaves two copies of `libpython3.15.a` and one is made a symlink to the other, which is 80 MB for nothing lost. It would be easy to strip the binary and delete the tests and get under half that, and the image would no longer be what you get by typing `./configure && make`, which is the one thing the release build is for.

Only the `debug` image carries the CPython source tree and gdb, with a `.gdbinit` that has already sourced `Tools/gdb/libpython.py`. The source is most of what that image weighs, and stepping through C without it is a wall of addresses rather than an experiment.

Both stages run the interpreter before the build is allowed to finish, and the workflow runs it a third time out of the published image. The third one catches what the first two cannot: a path that is only wrong once the image has been pushed and pulled again.

## Patches

`patches/` at the top of the repository is deliberately empty. Anything in it is applied to the pinned checkout in sorted order, and it exists for the case where a lesson needs an instrumented interpreter that upstream would not want. A patch here means every image is running something that is not CPython, so the bar is high and the README in that directory says what it is.
