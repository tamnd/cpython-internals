"""Turning a scene file into the GIF that ends up in the repository.

Two steps, and the second one is not optional. Manim can write a GIF directly and the file
it writes is enormous, because it dumps every frame at full colour with no shared palette.
The same animation through ffmpeg with a generated palette comes out several times smaller
and looks the same, and the difference between those two numbers is whether this repository
stays clonable once there are forty animations in it.

The rendered files are committed, like the diagrams and the notebooks, because a reader on
GitHub or in Colab is looking at a page and not running a build. Unlike the diagrams they
are not compared byte for byte by CI: video encoders are not reproducible across versions
and platforms, and a check that fails when somebody upgrades ffmpeg is a check people learn
to ignore. What CI does instead is render the scenes again and fail if one of them raises,
which catches the mistake that actually happens.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

#: Where the committed GIFs live, relative to the repository root.
RENDERED = Path("anim") / "rendered"

#: Manim's quality flags. Medium is 1280 by 720 at 30 frames a second, which is more than
#: the GIF keeps, and rendering above what you keep is how you get sharp text after the
#: downscale instead of soft text.
QUALITY = {"low": "-ql", "medium": "-qm", "high": "-qh"}

#: The GIF is 960 wide, which is readable on a phone and on a laptop, and 12 frames a
#: second, which is enough for shapes sliding around and is a third of the file size of 30.
GIF_WIDTH = 960
GIF_FPS = 12

#: Sixty four colours is plenty for flat fills and dark text, and it is where the palette
#: stops costing much. The Bayer dither keeps the flat areas flat, which matters here more
#: than in photographic footage: an error diffused dither turns a plain fill into noise that
#: changes every frame, and noise that changes every frame does not compress.
GIF_COLOURS = 64
GIF_FILTER = (
    f"fps={GIF_FPS},scale={GIF_WIDTH}:-1:flags=lanczos,split[a][b];"
    f"[a]palettegen=max_colors={GIF_COLOURS}[p];[b][p]paletteuse=dither=bayer:bayer_scale=4"
)


class RenderError(RuntimeError):
    """A scene did not render, or ffmpeg was not there to convert what it produced."""


def scene_file(slug: str, root: Path) -> Path:
    from .catalogue import module_name

    return root / "anim" / f"{module_name(slug)}.py"


def render(slug: str, root: Path, *, quality: str = "medium", into: Path | None = None) -> Path:
    """Render one animation and write its GIF, returning where it went."""
    source = scene_file(slug, root)
    if not source.is_file():
        raise RenderError(f"{slug} has no scene file at {source}")
    if shutil.which("ffmpeg") is None:
        raise RenderError("ffmpeg is not on PATH, and the GIF cannot be made without it")

    destination = (into or root / RENDERED) / f"{slug}.gif"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as scratch:
        video = _manim(slug, source, Path(scratch), quality)
        _to_gif(video, destination)
    return destination


def _manim(slug: str, source: Path, scratch: Path, quality: str) -> Path:
    from .catalogue import class_name

    if quality not in QUALITY:
        raise RenderError(f"unknown quality {quality!r}, expected one of {sorted(QUALITY)}")
    command = [
        sys.executable,
        "-m",
        "manim",
        "render",
        QUALITY[quality],
        "--format=mp4",
        "--media_dir",
        str(scratch),
        "-o",
        slug,
        str(source),
        class_name(slug),
    ]
    finished = subprocess.run(command, capture_output=True, text=True, check=False)
    if finished.returncode != 0:
        raise RenderError(f"{slug} did not render\n{finished.stdout}\n{finished.stderr}")
    made = sorted(scratch.rglob(f"{slug}.mp4"))
    if not made:
        raise RenderError(f"{slug} rendered but produced no mp4 under {scratch}")
    return made[0]


def _to_gif(video: Path, destination: Path) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(video),
        "-vf",
        GIF_FILTER,
        "-loop",
        "0",
        str(destination),
    ]
    finished = subprocess.run(command, capture_output=True, text=True, check=False)
    if finished.returncode != 0:
        raise RenderError(f"ffmpeg could not convert {video}\n{finished.stderr}")
