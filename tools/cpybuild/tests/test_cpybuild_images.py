"""The lockfile, and the reason it holds digests rather than tags."""

from __future__ import annotations

import pytest
from cpybuild import images
from cpybuild.configs import ARCHITECTURES, CONFIGURATIONS
from cpybuild.images import Broken, Built, Lock, problems

from refcheck import PINNED_COMMIT, PINNED_TAG

ONE = "sha256:" + "a" * 64
TWO = "sha256:" + "b" * 64


def full(**changed) -> Lock:
    """A lockfile with nothing wrong with it, which the tests then break one thing at a time."""
    lock = Lock(**changed)
    for config in CONFIGURATIONS:
        for arch in ARCHITECTURES:
            lock.record(config.key, arch, ONE)
        lock.record_index(config.key, TWO)
    return lock


#: A devcontainer, cut down to the line these tests are about.
BOX = '{\n  "name": "a box",\n  "image": "%s"\n}\n'


def box(lock: Lock, config: str = "debug") -> str:
    return BOX % lock.reference_index(config)


def released(**by_tag):
    """Stand in for git: a mapping from tag to the lockfile body at that tag."""
    return lambda name: by_tag.get(name)


def test_the_digests_of_a_release_are_kept_however_old_it_is():
    """Somebody checking out v0.2.0 has to get the interpreter it was written against."""
    old = full()
    old.record("debug", "amd64", TWO)
    kept = images.protected(["v0.2.0"], released(**{"v0.2.0": old.as_json()}))
    assert TWO in kept


def test_a_tag_from_before_the_images_existed_is_not_an_error():
    assert images.protected(["v0.0.1"], released()) == set()


def test_every_release_is_read_and_not_only_the_newest():
    """Two versions of the site can point at two different debug images, and both are live."""
    first, second = full(), full()
    first.record("debug", "amd64", ONE)
    second.record("debug", "amd64", TWO)
    kept = images.protected(
        ["v0.1.0", "v0.2.0"],
        released(**{"v0.1.0": first.as_json(), "v0.2.0": second.as_json()}),
    )
    assert {ONE, TWO} <= kept


def test_a_release_whose_lockfile_cannot_be_read_stops_the_tidy_up():
    """Skipping it would quietly unprotect that release's images and then delete them."""
    with pytest.raises(Broken) as caught:
        images.protected(["v0.3.0"], released(**{"v0.3.0": "{not json"}))
    assert "v0.3.0" in str(caught.value)


def test_digests_of_a_lockfile_is_every_image_in_it():
    """The joined ones are in here too, which is the half a tidy up would otherwise delete."""
    assert images.digests(full()) == {ONE, TWO}


def test_a_complete_lockfile_has_nothing_to_say():
    assert problems(full()) == []


def test_a_reference_is_a_digest_and_not_a_tag():
    """A tag is a name somebody can move. The image is the digest."""
    said = full().reference("debug", "amd64")
    assert said.endswith(f"@{ONE}")
    assert said.startswith(images.REGISTRY)


def test_a_reference_keeps_the_tag_as_well_for_a_person_reading_it():
    """`:debug@sha256:...` pulls by digest and still says which build it is."""
    assert ":debug@" in full().reference("debug", "amd64")


def test_asking_for_an_image_that_was_never_built_says_so(tmp_path):
    with pytest.raises(Broken) as caught:
        Lock().reference("debug", "amd64")
    assert "debug" in str(caught.value)


def test_a_missing_build_is_named_rather_than_counted():
    lock = full()
    del lock.images["jit"]["arm64"]
    assert problems(lock) == ["no jit image for arm64"]


def test_every_missing_build_is_reported_at_once():
    """Reporting the first of eight means eight runs of a twenty minute job."""
    lock = full()
    del lock.images["jit"]
    del lock.images["debug"]
    assert len(problems(lock)) == 4


def test_a_digest_that_is_not_one_is_caught():
    lock = full()
    lock.images["debug"]["amd64"] = Built(digest="latest", built="2026-08-29")
    assert "not one" in problems(lock)[0]


def test_a_short_digest_is_not_a_digest():
    lock = full()
    lock.images["debug"]["amd64"] = Built(digest="sha256:abc", built="2026-08-29")
    assert problems(lock)


def test_a_lockfile_built_from_a_different_tag_is_stale():
    """The images and the citations have to describe the same CPython or the lessons lie."""
    found = problems(full(tag="v3.14.0"))
    assert PINNED_TAG in found[0]


def test_a_lockfile_built_from_a_different_commit_is_stale():
    assert any("commit" in one for one in problems(full(commit="0" * 40)))


def test_a_build_in_the_lockfile_that_is_not_in_the_list_is_reported():
    """Otherwise a removed configuration leaves an image nobody rebuilds and nobody deletes."""
    lock = full()
    lock.record("pgo", "amd64", TWO)
    assert "pgo is in the lockfile and not in the configuration list" in problems(lock)


def test_recording_a_build_dates_it():
    lock = Lock()
    lock.record("debug", "amd64", ONE)
    assert lock.get("debug", "amd64").built.count("-") == 2


def test_recording_the_same_build_twice_replaces_it():
    lock = Lock()
    lock.record("debug", "amd64", ONE)
    lock.record("debug", "amd64", TWO)
    assert lock.get("debug", "amd64").digest == TWO


def test_a_lockfile_survives_a_round_trip():
    lock = full()
    assert Lock.from_json(lock.as_json()).as_json() == lock.as_json()


def test_a_lockfile_is_written_sorted_so_a_rebuild_is_a_readable_diff():
    lock = Lock()
    lock.record("release", "arm64", ONE)
    lock.record("debug", "amd64", TWO)
    body = lock.as_json()
    assert body.index('"debug"') < body.index('"release"')


def test_a_lockfile_ends_in_a_newline():
    assert full().as_json().endswith("}\n")


def test_a_fresh_lockfile_starts_on_the_pin():
    assert Lock().tag == PINNED_TAG
    assert Lock().commit == PINNED_COMMIT


def test_no_lockfile_at_all_says_what_to_run(tmp_path):
    with pytest.raises(Broken) as caught:
        Lock.load(tmp_path / "nothing.json")
    assert "cpython-images" in str(caught.value)


def test_writing_a_lockfile_makes_the_directory(tmp_path):
    path = tmp_path / "deep" / "cpython.lock.json"
    full().write(path)
    assert Lock.load(path).tag == PINNED_TAG


def test_the_joined_image_is_what_a_person_pulls():
    """Neither half is: an index is its own object and its digest is neither of theirs."""
    said = full().reference_index("debug")
    assert said == f"{images.REGISTRY}:debug@{TWO}"


def test_a_lockfile_with_no_joined_image_is_incomplete():
    lock = full()
    del lock.indexes["jit"]
    assert problems(lock) == ["no joined jit image, so nothing can pull it without an arch"]


def test_a_joined_digest_that_is_not_a_digest_is_caught():
    lock = full()
    lock.indexes["debug"] = Built(digest="debug-latest", built="2026-08-29")
    assert any("joined debug" in one for one in problems(lock))


def test_asking_for_a_joined_image_that_was_never_published_says_so():
    with pytest.raises(Broken) as caught:
        Lock().reference_index("debug")
    assert "debug" in str(caught.value)


def test_a_joined_image_for_a_build_nobody_configured_is_reported():
    lock = full()
    lock.record_index("pgo", ONE)
    assert "pgo is in the lockfile and not in the configuration list" in problems(lock)


def test_a_lockfile_with_joined_images_survives_a_round_trip():
    lock = full()
    assert Lock.from_json(lock.as_json()).as_json() == lock.as_json()


def test_an_older_lockfile_with_no_joined_images_still_reads():
    """The file on disk predates them, and a reader that refused it would be a broken bisect."""
    body = full().as_json().replace('"indexes"', '"other"')
    assert Lock.from_json(body).indexes == {}


def test_a_devcontainer_pointing_at_the_lockfile_is_fine():
    lock = full()
    assert images.devcontainer_problems(lock, box(lock)) == []


def test_a_devcontainer_left_behind_by_a_rebuild_is_caught():
    """The whole reason this is checked: the two files are updated together and edited apart."""
    lock = full()
    stale = BOX % f"{images.REGISTRY}:debug@{ONE}"
    said = images.devcontainer_problems(lock, stale)
    assert len(said) == 1
    assert ONE in said[0] and TWO in said[0]


def test_a_devcontainer_naming_a_tag_rather_than_a_digest_is_caught():
    lock = full()
    assert images.devcontainer_problems(lock, BOX % f"{images.REGISTRY}:debug")


def test_a_devcontainer_with_no_image_at_all_says_so():
    assert images.devcontainer_problems(full(), '{"name": "a box"}')


def test_retargeting_keeps_everything_around_the_image():
    """It is a file with comments in it that somebody is meant to read, so it is edited rather
    than regenerated."""
    before = '// a comment\n{\n  "image": "old",\n  "name": "a box"\n}\n'
    after = images.retarget(before, "new")
    assert '"image": "new"' in after
    assert after.startswith("// a comment")
    assert '"name": "a box"' in after


def test_retargeting_a_file_with_no_image_refuses_rather_than_appending():
    with pytest.raises(Broken):
        images.retarget('{"name": "a box"}', "new")


def test_the_committed_devcontainer_pulls_the_committed_debug_image():
    """The one test in here that reads the real files, because they are the ones that ship."""
    lock = Lock.load(images.LOCKFILE)
    said = images.DEVCONTAINER.read_text(encoding="utf-8")
    assert images.devcontainer_problems(lock, said) == []
