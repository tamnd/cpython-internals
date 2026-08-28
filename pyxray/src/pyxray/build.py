"""Which interpreter am I actually looking at?

Every observation in this material is build dependent. The refcount you see, whether an
object is immortal, whether the JIT is running, what `dis` prints, and whether the small
integer cache stops at 256 or at 1024 all depend on which binary is executing the cell.
A reader who does not know which one they are on will eventually see a result that
contradicts the prose and conclude the prose is wrong.

So every lesson opens with the banner, and the banner is not optional.
"""

from __future__ import annotations

import platform
import sys
import sysconfig
from dataclasses import dataclass, field
from typing import Any

#: The version every citation, every claim and every golden in this project is written
#: against. Anything else is legal to run on and gets called out in the banner.
PINNED_VERSION = (3, 15, 0)
PINNED_RELEASELEVEL = "candidate"


def _config(name: str) -> Any:
    try:
        return sysconfig.get_config_var(name)
    except Exception:
        return None


def _probe(thunk) -> bool:
    """Run a capability probe, treating any failure as an absence.

    Probes run on stock interpreters, on debug builds, on free threaded builds and under
    WebAssembly. A probe that raises on one of those is telling us the capability is not
    there, which is exactly what we wanted to know, so it must not take the notebook down
    with it.
    """
    try:
        return bool(thunk())
    except Exception:
        return False


def capabilities() -> dict[str, bool]:
    """What this interpreter lets us do, probed rather than assumed.

    This is the function the browser tier lives or dies on. Pyodide is a real CPython
    compiled to WebAssembly, but it is not the same build as the one on your laptop, and
    the honest way to find out what it supports is to ask it.
    """
    probes = {
        "testinternalcapi": lambda: __import__("_testinternalcapi") is not None,
        "testcapi": lambda: __import__("_testcapi") is not None,
        "ctypes": lambda: __import__("ctypes").sizeof(__import__("ctypes").c_void_p) > 0,
        # These three are called rather than looked up, because a module can exist and
        # still refuse to work. Pyodide is the case that taught us that.
        "monitoring": lambda: sys.monitoring.get_tool(sys.monitoring.DEBUGGER_ID) or True,
        "settrace": lambda: sys.settrace(sys.gettrace()) or True,
        "gc": lambda: __import__("gc").get_count() is not None,
        "opcode_metadata": lambda: __import__("_opcode_metadata").opmap is not None,
        "specialization_stats": lambda: hasattr(__import__("_opcode"), "get_specialization_stats"),
        "debugmallocstats": lambda: hasattr(sys, "_debugmallocstats"),
        "is_immortal": lambda: hasattr(sys, "_is_immortal"),
    }
    return {name: _probe(thunk) for name, thunk in probes.items()}


@dataclass(frozen=True)
class Build:
    """A description of the running interpreter, complete enough to explain a surprise."""

    version: str
    version_info: tuple
    implementation: str
    executable: str
    platform: str
    debug: bool
    free_threaded: bool
    gil_enabled: bool
    jit_available: bool
    jit_enabled: bool
    jit_active: bool
    tail_call: bool
    pymalloc: bool
    stats: bool
    wasm: bool
    capabilities: dict[str, bool] = field(default_factory=dict)

    @property
    def is_pinned(self) -> bool:
        """Is this the exact version the project's claims are written against?"""
        return (
            self.version_info[:3] == PINNED_VERSION and self.version_info[3] == PINNED_RELEASELEVEL
        )

    @property
    def is_pinned_minor(self) -> bool:
        """Same minor release, so bytecode and object layout should match."""
        return self.version_info[:2] == PINNED_VERSION[:2]

    def missing(self) -> list[str]:
        """Capabilities this build does not have, so a lesson can say so up front."""
        return sorted(name for name, present in self.capabilities.items() if not present)

    def summary(self) -> str:
        """One line, because a banner nobody reads teaches nothing."""
        marks = []
        if self.debug:
            marks.append("debug")
        if self.free_threaded:
            marks.append("free threaded")
        if not self.gil_enabled:
            marks.append("GIL off")
        if self.jit_enabled:
            marks.append("JIT on")
        if self.tail_call:
            marks.append("tail call")
        if self.wasm:
            marks.append("WebAssembly")
        if not marks:
            marks.append("stock release build")
        return f"{self.implementation} {self.version} on {self.platform}, {', '.join(marks)}"

    def warnings(self) -> list[str]:
        """Things that will make an observation in this material come out differently."""
        notes = []
        if not self.is_pinned_minor:
            notes.append(
                f"this is {self.version_info[0]}.{self.version_info[1]}, and everything here "
                f"is written against {PINNED_VERSION[0]}.{PINNED_VERSION[1]}, so bytecode and "
                f"some object layouts will differ from the prose"
            )
        elif not self.is_pinned:
            notes.append(
                "same minor release as the pin but not the exact build; "
                "bytecode should match, exact sizes may not"
            )
        if self.debug:
            notes.append(
                "a debug build changes sizes, adds checks and changes timing, so do not "
                "take performance measurements here"
            )
        if self.free_threaded:
            notes.append(
                "the free threaded build has a different object header, a different "
                "allocator and a different collector, so refcounts and sizes will not "
                "match the default build"
            )
        missing = self.missing()
        if missing:
            notes.append(f"not available on this build: {', '.join(missing)}")
        return notes


def current() -> Build:
    """Describe the interpreter running this code."""
    info = sys.implementation
    jit = getattr(sys, "_jit", None)
    gil = _probe(sys._is_gil_enabled) if hasattr(sys, "_is_gil_enabled") else True
    return Build(
        version=sys.version.split()[0],
        version_info=tuple(sys.version_info),
        implementation=info.name,
        executable=sys.executable or "(embedded)",
        platform=f"{platform.system() or sys.platform} {platform.machine()}".strip(),
        debug=hasattr(sys, "gettotalrefcount"),
        free_threaded=bool(_config("Py_GIL_DISABLED")),
        gil_enabled=gil,
        jit_available=_probe(lambda: jit.is_available()) if jit else False,
        jit_enabled=_probe(lambda: jit.is_enabled()) if jit else False,
        jit_active=_probe(lambda: jit.is_active()) if jit else False,
        tail_call=bool(_config("Py_TAIL_CALL_INTERP")),
        pymalloc=bool(_config("WITH_PYMALLOC")),
        stats=bool(_config("Py_STATS")),
        wasm=sys.platform in {"emscripten", "wasi"},
        capabilities=capabilities(),
    )


def banner(build: Build | None = None) -> str:
    """The text every lesson opens with."""
    build = build or current()
    lines = [build.summary()]
    lines.extend(f"  note: {note}" for note in build.warnings())
    return "\n".join(lines)
