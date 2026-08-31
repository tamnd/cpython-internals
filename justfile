# Every CI job is runnable here under the same name it has in the workflow. If a check
# only exists in CI, contributors find out it failed after they pushed, which is the
# slowest possible feedback loop and the reason the two drift apart.

pinned_tag := "v3.15.0rc1"
pinned_version := "3.15"
cpython_src := env("CPYTHON_SRC", "vendor/cpython")

default:
    @just --list

# Install the workspace and its dev tools.
setup:
    uv sync --all-packages

# Fetch the pinned CPython source. Shallow and blobless, so it is about 200 MB rather
# than several gigabytes, and it is the only thing every citation is checked against.
vendor:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -d "{{cpython_src}}/.git" ]; then
        echo "already have a checkout at {{cpython_src}}"
    else
        git clone --depth 1 --branch {{pinned_tag}} --filter=blob:none \
            https://github.com/python/cpython.git "{{cpython_src}}"
    fi
    git -C "{{cpython_src}}" rev-parse HEAD

# The full local check, in the order that fails fastest.
check: lint test citations claims blueprints diagrams lessons notebooks probe dist images animations tier1 boss

lint:
    uv run ruff check .
    uv run ruff format --check .

fmt:
    uv run ruff format .
    uv run ruff check --fix .

test:
    uv run pytest

# The same suite on the version the browser tier runs. Everything here is written against
# 3.15, and the reader in a Colab or Pyodide tab is on 3.14, so the tests that encode a
# version difference have to be exercised from both sides or they only prove one of them.
#
# The install is editable on purpose. With a plain `--with ./pyxray` uv reuses a wheel it
# built earlier, so edits made since then are silently not tested, and the run passes for
# the wrong reason. That is worse than no second interpreter at all.
test-3-14:
    uv run --python 3.14 --isolated --with pytest --with ./tools/refcheck --with-editable ./pyxray \
        pytest pyxray/tests -q -p no:cacheprovider

# Resolve every citation in the project against the pinned tree.
citations:
    uv run refcheck verify

# Check the blueprints have the shape somebody can implement from: the nine sections in
# order, the header block, the invariant numbering, and no fact deferred to a lesson. The
# second line covers the ones with a source document under blueprints/sources: their
# generated sections have to still match what the grammar says today.
blueprints:
    uv run bpcheck lint
    uv run bpc check

# Regenerate the compiled sections of a blueprint after editing its source document or
# moving the pin, then read the diff. Same deal as the diagrams and the notebooks: the
# output is committed because that is what GitHub renders, so something has to check it.
build-blueprints:
    uv run bpc build

# Confirm every committed diagram still matches the script that draws it. Same deal as the
# notebooks below: the `.excalidraw` and the `.svg` are both generated and both committed,
# because GitHub and Colab render an image from the repository and cannot run a build first.
diagrams:
    uv run nbdiagram check

# Redraw the diagrams after editing a lesson's diagrams.py.
build-diagrams:
    uv run nbdiagram build

# Confirm every committed notebook still matches the builder that produced it. Notebooks
# are generated and also committed, because a reader clicking a Colab badge cannot run a
# build step first, and anything generated and committed drifts unless something checks.
lessons:
    uv run nbbuild check

# Every behavioural claim in the lessons has a runnable cell behind it, and the committed
# ledger still matches. Fast, no kernel: it re-runs each builder and asks it for its claims,
# and a claim whose evidence has moved out from under it fails in the builder rather than
# here. Deliberately before the slow half of the checks for that reason.
claims:
    uv run nbbuild claims --check

# Rewrite lessons/CLAIMS.md after marking up a claim.
build-claims:
    uv run nbbuild claims

# Rewrite GLOSSARY.md after editing the terms. There is no separate checker recipe for it,
# because the test suite already compares the committed file against the module, and one
# check that runs everywhere beats two that disagree.
build-glossary:
    uv run pyxray-glossary

# Regenerate the notebooks after editing a builder.
build-lessons:
    uv run nbbuild build

# Check every lesson notebook has the shape a reader needs, then actually run it. The run
# is the slow half, and it is the half that matters: a lesson whose fourth cell raises is
# worse than no lesson, because the reader assumes they broke it.
notebooks:
    uv run nbcheck lint
    uv run nbcheck blocks
    uv run nbcheck run

# Run every lesson on both interpreters and check that the cells whose output differs are
# the ones declared as differing. This is the slowest recipe here by a distance, because it
# executes every notebook twice, so it is not part of `check`. CI does it in the two
# notebook jobs it already runs and compares the results afterwards, which costs it nothing.
versions:
    #!/usr/bin/env bash
    set -euo pipefail
    rm -rf build/versions
    uv run nbversion record --into build/versions
    UV_PROJECT_ENVIRONMENT=/tmp/venv-314 uv run --python 3.14 --all-packages \
        nbversion record --into build/versions
    uv run nbversion compare build/versions/{{pinned_version}} build/versions/3.14

# The structural checks on their own, with no kernel, for while you are still writing.
# `blocks` prints the hook, tour and lesson word counts for all twelve whether or not any
# of them is over, because the number worth knowing while writing is how much room is left.
notebooks-lint:
    uv run nbcheck lint
    uv run nbcheck blocks

# Check the animations without a renderer: every storyboard is inside the ninety second
# cap, every shape it draws is in the visual system, and the scene file, the committed GIF
# and the index page all still agree with the plan. Milliseconds, and no manim needed.
animations:
    uv run xraymanim check

# Re-render every animation. Needs `uv sync --extra anim` first, and ffmpeg on PATH. This is
# minutes rather than seconds, which is why it is not part of `check`.
build-animations:
    uv run --extra anim xraymanim render

# Read the committed probe results and fail when a surface the lessons need has stopped
# working in the browser, or when the report and the notebook have fallen behind the checks.
# Milliseconds: it reads two JSON files, it does not boot anything.
probe:
    uv run wasmprobe check probes/pyodide
    uv run nbcheck run probes

# Record the probe again on both runtimes and rewrite the report and the notebook. Needs
# node and `npm install` in tools/wasmprobe, and a 3.14 to compare against, because Pyodide
# ships 3.14 and a native 3.15 control would confuse a version difference for a build one.
#
# There is no `nbcheck lint probes` anywhere here on purpose. Those rules are written for a
# lesson: install pyxray, print the version banner, and so on. The probe installs nothing,
# which is the whole point of it, so it would fail two rules for doing its job properly.
build-probe:
    UV_PROJECT_ENVIRONMENT=/tmp/venv-314 uv run --python 3.14 --all-packages \
        wasmprobe native --into probes/pyodide
    uv run wasmprobe browser --into probes/pyodide
    uv run wasmprobe lessons --into probes/pyodide
    uv run wasmprobe report probes/pyodide --into probes/pyodide/report.md
    uv run wasmprobe notebook --into probes/pyodide/probe.ipynb

# Read the committed distribution survey and print what it means. Instant, needs nothing.
#
# This does not fail when a distribution is missing the module. That is a fact about Fedora,
# not about this repository, and a build that went red every time somebody ran it would not
# change how Fedora packages Python. It fails when the report has fallen behind the survey.
dist:
    uv run distprobe check probes/distributions

# Ask every channel again. Pulls container images and runs a package manager inside each, so
# it is several minutes on a cold cache and it needs Docker running. The Pyodide row is
# copied out of the wasmprobe recording rather than measured a second time, so `just
# build-probe` should run before this one when both are due.
build-dist:
    uv run distprobe survey --into probes/distributions
    uv run distprobe report probes/distributions --into probes/distributions/report.md

# Read the committed image lockfile and say whether it still describes this project. Offline
# and instant: it never reaches for the registry, because a check that needs the network is a
# check that fails on a train, and what is worth catching here is a lockfile that has fallen
# behind the pin or is missing a build somebody added.
#
# It also reads the devcontainer, because that file names the debug image by digest and the two
# drift the moment somebody edits one of them by hand. The way that drift shows up otherwise is
# a reader spending an evening in an interpreter a month older than the lessons say it is.
images:
    uv run cpybuild check

# Build one configuration locally, for when you are changing the Dockerfile. Fifteen to twenty
# five minutes cold and a couple of minutes warm, and it pushes nothing. The published images
# come from the cpython-images workflow, which is the only thing that compiles CPython on a
# schedule. Run `just images-list` to see the five names.
build-image config="debug":
    #!/usr/bin/env bash
    set -euo pipefail
    args=()
    while IFS= read -r one; do args+=(--build-arg "$one"); done < <(uv run cpybuild buildargs {{config}})
    docker build -f images/cpython/Dockerfile "${args[@]}" \
        -t cpython-internals/cpython:{{config}} .

# The five builds and what each one is for.
images-list:
    uv run cpybuild list

# Read the committed Tier 1 recordings and say whether they still belong to the experiments
# that produced them, the image this project pins, and the lessons that show them. Instant and
# offline: it never starts a container, because the recording exists so that nobody has to.
tier1:
    uv run tier1 check

# Run every Tier 1 experiment in its published image and rewrite the recordings. Needs Docker
# and a couple of hundred megabytes of image on a cold cache. Read the diff before committing
# it: a measured number moving a little is expected, and a line changing is a finding.
build-tier1:
    uv run tier1 record

# The same run without writing anything, which is what CI does. A measured number is compared
# by its label and not by its value, because the count moves by one or two between two runs of
# the same image, and a check that goes red for that is a check somebody deletes.
verify-tier1:
    uv run tier1 verify

# Check every boss fight is still assembled, then run each grader against the submission that
# should pass and the one that should fail. Both halves matter. A grader nobody has watched
# fail is a grader that might be waving everything through, and that goes wrong silently.
boss:
    uv run boss check
    uv run boss verify

# The same, over twenty different generated corpora rather than one. Slower, and worth running
# after touching a grader, because a fight can be right on seed zero and wrong on seed eleven.
boss-wide:
    uv run boss verify --seeds 20

# Rewrite the citation lockfile after a human has read the diff. This is deliberately
# not part of `check`, because a checker that silently repairs itself checks nothing.
recheck:
    uv run refcheck verify --update
    @echo "read the diff to citations.lock.json before committing it"

# Print the GitHub permalink for a citation, for pasting into prose or a review.
url citation:
    uv run refcheck url "{{citation}}"

# Print the cited lines, so you can confirm a citation says what you think it says.
show citation:
    uv run refcheck show "{{citation}}"
