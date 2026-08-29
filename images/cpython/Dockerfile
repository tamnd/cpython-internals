# One CPython, built five ways. Which way is a build argument, and the argument list comes
# from `cpybuild matrix` so the workflow and the local build cannot disagree about it.
#
# Two stages. The first compiles, which needs a couple of hundred megabytes of headers and a
# compiler. The second is what gets published, and carries the runtime libraries, the
# interpreter, and for the debug build a debugger and the source it is stepping through.
#
# Nothing here pins a base image by digest, deliberately. Debian trixie moves under us and
# that is the point: these images are meant to say what CPython does on a current Linux, and
# an image frozen against a distribution from a year ago stops being able to say that. The
# CPython side is pinned exactly, by commit, which is the half that has to be reproducible.

ARG DEBIAN=trixie

FROM debian:${DEBIAN} AS build

# What to build, and how. Every one of these comes from cpybuild.configs, and the workflow
# passes them in rather than repeating them.
ARG CPYTHON_COMMIT
ARG CONFIG=release
ARG CONFIGURE_FLAGS=""
ARG PACKAGES=""
ARG CC=""
ARG LLVM=""

ENV DEBIAN_FRONTEND=noninteractive

# ccache is here rather than in the package list because it is a property of building, not of
# a configuration. The workflow mounts its cache directory, so a rebuild with no source change
# is a couple of minutes instead of twenty.
#
# The LLVM repository is added only when a build asks for a version, which today is only the
# JIT. CPython's JIT wants one exact LLVM major version and Debian trixie is two behind it, so
# installing the `llvm` package gets the wrong one and the build fails several minutes in with
# a message about a tool it could not find. Every other build uses what Debian has.
RUN apt-get -qq update \
    && apt-get -qq install -y --no-install-recommends ca-certificates ccache git \
    && if [ -n "${LLVM}" ]; then \
        apt-get -qq install -y --no-install-recommends curl gnupg; \
        curl -fsSL https://apt.llvm.org/llvm-snapshot.gpg.key \
            -o /etc/apt/trusted.gpg.d/apt.llvm.org.asc; \
        . /etc/os-release; \
        echo "deb http://apt.llvm.org/${VERSION_CODENAME}/ llvm-toolchain-${VERSION_CODENAME}-${LLVM} main" \
            > /etc/apt/sources.list.d/llvm.list; \
        apt-get -qq update; \
    fi \
    && apt-get -qq install -y --no-install-recommends ${PACKAGES} \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/usr/lib/ccache:${PATH}" CCACHE_DIR=/ccache

# A blobless clone of one commit. The full history is about two gigabytes and none of it is
# needed to compile a tag.
WORKDIR /src
RUN git init -q cpython \
    && git -C cpython remote add origin https://github.com/python/cpython.git \
    && git -C cpython fetch -q --depth 1 --filter=blob:none origin "${CPYTHON_COMMIT}" \
    && git -C cpython checkout -q FETCH_HEAD \
    && git -C cpython rev-parse HEAD

# The patch series. Empty today, and the directory exists so that the day something has to be
# carried, applying it is one step in one place rather than a fork nobody can find.
COPY patches/ /patches/
RUN set -eu; \
    for one in $(find /patches -name '*.patch' | sort); do \
        echo "applying ${one}"; \
        git -C /src/cpython apply --verbose "${one}"; \
    done

WORKDIR /src/cpython
RUN --mount=type=cache,target=/ccache \
    set -eu; \
    if [ -n "${CC}" ]; then export CC="${CC}"; fi; \
    ./configure --prefix=/opt/python ${CONFIGURE_FLAGS} > /tmp/configure.log 2>&1 \
        || { tail -40 /tmp/configure.log; exit 1; }; \
    make -j"$(nproc)" > /tmp/make.log 2>&1 || { tail -60 /tmp/make.log; exit 1; }; \
    make install > /tmp/install.log 2>&1 || { tail -40 /tmp/install.log; exit 1; }; \
    ccache --show-stats

# The interpreter has to work before the image is worth publishing. `-c` rather than the test
# suite: the full suite is half an hour and this is a smoke test, not a validation of CPython.
RUN /opt/python/bin/python3 -c "import sys, ssl, sqlite3, zlib, lzma, ctypes, _testinternalcapi; \
print(sys.version)"

# `make install` leaves two copies of the static library, one in `lib` and one in the config
# directory, and on this build they are eighty megabytes each. One becomes a symlink to the
# other, so both paths still resolve and both still read the same bytes.
#
# This has to happen here rather than in the final stage. Layers only ever add, so deleting or
# replacing an eighty megabyte file after it has been copied in makes the image bigger, not
# smaller. It was written that way first and the image grew by a hundred megabytes.
#
# Nothing else is trimmed. Stripping the debug symbols out of the binary would save another
# thirty and would also mean the release image is no longer what you get by typing
# `./configure && make`, which is the one thing this build is for.
RUN set -eu; \
    one=$(find /opt/python/lib -maxdepth 1 -name 'libpython*.a' | head -1); \
    if [ -n "${one}" ]; then \
        for copy in /opt/python/lib/python*/config-*/"$(basename "${one}")"; do \
            [ -f "${copy}" ] || continue; \
            ln -sf "../../$(basename "${one}")" "${copy}"; \
        done; \
    fi

# The source, trimmed. Object files and the git directory are most of the weight and neither
# is any use to a debugger. Only the debug image keeps this, and it keeps it because stepping
# through C with no source is a wall of addresses rather than an experiment.
RUN set -eu; \
    find /src/cpython -name '*.o' -delete; \
    rm -rf /src/cpython/.git /src/cpython/build; \
    mkdir -p /opt/source; \
    if [ "${CONFIG}" = "debug" ]; then cp -a /src/cpython /opt/source/cpython; fi


FROM debian:${DEBIAN}-slim AS final

ARG CONFIG=release
ARG CPYTHON_COMMIT
ARG CPYTHON_TAG
ARG SUMMARY=""
ARG DEBUGGER=""

ENV DEBIAN_FRONTEND=noninteractive

# The runtime halves of the -dev packages the build stage installed. Kept explicit rather than
# copied wholesale, because a slim image that quietly grew a compiler is how a five hundred
# megabyte base image happens.
RUN apt-get -qq update \
    && apt-get -qq install -y --no-install-recommends \
        ca-certificates \
        libbz2-1.0 \
        libffi8 \
        libgdbm6 \
        liblzma5 \
        libncursesw6 \
        libreadline8 \
        libsqlite3-0 \
        libssl3 \
        libzstd1 \
        uuid-runtime \
        zlib1g \
    && if [ -n "${DEBUGGER}" ]; then \
        apt-get -qq install -y --no-install-recommends gdb; \
    fi \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /opt/python /opt/python
COPY --from=build /opt/source /usr/src

ENV PATH=/opt/python/bin:$PATH

# CPython's own gdb helper, which is what makes a C stack readable: it prints Python frames
# out of the interpreter's data structures instead of leaving you to read PyObject pointers.
RUN set -eu; \
    if [ -d /usr/src/cpython ]; then \
        printf 'add-auto-load-safe-path /\ndirectory /usr/src/cpython\nsource /usr/src/cpython/Tools/gdb/libpython.py\n' \
            > /root/.gdbinit; \
    fi; \
    ln -sf /opt/python/bin/python3 /usr/local/bin/python3

# The interpreter runs in the published image and not only in the build stage, because the
# usual way this breaks is a runtime library that was in the fat base image and is not in the
# slim one, and that only shows up here.
RUN python3 -c "import sys, ssl, sqlite3, zlib, lzma, ctypes, _testinternalcapi; print(sys.version)"

# The PSF licence travels with the interpreter. This image ships a built CPython, so the
# notice has to be in it and findable without unpacking anything.
COPY --from=build /src/cpython/LICENSE /usr/share/licenses/cpython/LICENSE

LABEL org.opencontainers.image.title="CPython ${CPYTHON_TAG}, ${CONFIG} build" \
      org.opencontainers.image.description="${SUMMARY}" \
      org.opencontainers.image.source="https://github.com/tamnd/cpython-internals" \
      org.opencontainers.image.licenses="PSF-2.0" \
      org.opencontainers.image.revision="${CPYTHON_COMMIT}" \
      org.opencontainers.image.version="${CPYTHON_TAG}" \
      internals.cpython.config="${CONFIG}"

CMD ["python3"]
