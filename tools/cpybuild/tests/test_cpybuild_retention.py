"""What the tidy up is allowed to delete.

Every test in here is really the same test asked from a different side: this code deletes
container images, deleting one is not reversible, and the way anybody finds out it was wrong
is a reader a year from now getting a digest that no longer resolves. So the interesting cases
are all the ones where the answer is no.
"""

from __future__ import annotations

from cpybuild import retention
from cpybuild.retention import Version, anchors, doomed, reachable, why

SAFE = "sha256:" + "a" * 64
LOOSE = "sha256:" + "b" * 64
PART = "sha256:" + "c" * 64
DEEPER = "sha256:" + "d" * 64


def version(id: int, day: int, digest: str = LOOSE, tags: tuple[str, ...] = ()) -> Version:
    return Version(id=id, digest=digest, created=f"2026-08-{day:02d}T04:17:00Z", tags=tags)


def test_an_old_untagged_image_nothing_points_at_can_go():
    versions = [version(one, day=one) for one in range(1, 6)]
    assert [one.id for one in doomed(versions, set(), keep=2)] == [3, 2, 1]


def test_a_release_keeps_its_image_however_old_it_is():
    """The whole reason this is not a retention action with a number in it."""
    versions = [version(1, day=1, digest=SAFE)] + [version(one, day=one) for one in range(2, 6)]
    assert 1 not in [one.id for one in doomed(versions, {SAFE}, keep=2)]


def test_a_tagged_version_is_the_current_image_for_a_build_and_stays():
    versions = [version(1, day=1, tags=("debug",))] + [version(one, day=one) for one in range(2, 6)]
    assert 1 not in [one.id for one in doomed(versions, set(), keep=2)]


def test_the_newest_are_kept_whatever_else_is_true_of_them():
    """An image published an hour ago is not protected yet, and deleting it would undo the run."""
    versions = [version(one, day=one) for one in range(1, 6)]
    kept = {one.id for one in versions} - {one.id for one in doomed(versions, set(), keep=3)}
    assert kept == {5, 4, 3}


def test_nothing_is_deleted_when_there_is_less_than_the_floor():
    versions = [version(one, day=one) for one in range(1, 4)]
    assert doomed(versions, set(), keep=120) == []


def test_the_newest_first_ordering_is_by_date_and_not_by_id():
    """Ids are not handed out in the order images are built when a job is retried."""
    versions = [version(99, day=1), version(1, day=9), version(50, day=5)]
    assert [one.id for one in doomed(versions, set(), keep=1)] == [50, 99]


def test_two_versions_made_in_the_same_second_still_have_an_order():
    """Ten images from one run share a timestamp, and an unstable sort would keep a random one."""
    versions = [version(one, day=4) for one in (7, 3, 9)]
    assert [one.id for one in doomed(versions, set(), keep=1)] == [7, 3]


def test_a_version_list_from_the_registry_is_read_as_it_arrives():
    body = [
        {
            "id": 42,
            "name": SAFE,
            "created_at": "2026-08-01T04:17:00Z",
            "metadata": {"container": {"tags": ["debug"]}},
        }
    ]
    one = retention.read(body)[0]
    assert (one.id, one.digest, one.tags) == (42, SAFE, ("debug",))


def test_a_version_with_no_metadata_at_all_is_read_as_untagged():
    """The registry omits the key rather than sending an empty list, and a crash here would
    stop the tidy up on the one version it most wants to remove."""
    assert retention.read([{"id": 1, "name": LOOSE, "created_at": ""}])[0].tags == ()


def test_a_version_with_a_null_tag_list_is_read_as_untagged():
    body = [{"id": 1, "name": LOOSE, "created_at": "", "metadata": {"container": {"tags": None}}}]
    assert retention.read(body)[0].tags == ()


def test_the_log_line_says_why_things_were_kept_and_not_only_how_many():
    versions = [version(1, day=1, digest=SAFE), version(2, day=2, tags=("debug",))]
    said = why(versions, {SAFE}, keep=0)
    assert "1 tagged" in said
    assert "1 named by a release or part of something named" in said


def test_the_keeping_starts_from_the_tagged_versions_as_well_as_the_named_ones():
    versions = [version(1, day=1, tags=("debug",)), version(2, day=2, digest=PART)]
    assert anchors(versions, {SAFE}) == {SAFE, LOOSE}


def test_a_manifest_inside_a_kept_index_is_kept_too():
    """Issue #126. This is the one that broke every image in the package at once."""
    inside = {SAFE: [PART, DEEPER]}
    assert reachable({SAFE}, lambda one: inside.get(one, [])) == {SAFE, PART, DEEPER}


def test_an_index_inside_an_index_is_followed_all_the_way_down():
    """Nothing produces this today. The bug was somebody assuming a fixed depth."""
    inside = {SAFE: [PART], PART: [DEEPER]}
    assert reachable({SAFE}, lambda one: inside.get(one, [])) == {SAFE, PART, DEEPER}


def test_two_indexes_sharing_a_manifest_do_not_send_the_walk_round_forever():
    """Two runs of a cached build push the same halves, so sharing is the normal case."""
    inside = {SAFE: [PART], LOOSE: [PART], PART: [SAFE]}
    assert reachable({SAFE, LOOSE}, lambda one: inside.get(one, [])) == {SAFE, LOOSE, PART}


def test_a_part_of_a_kept_index_survives_a_tidy_up_that_would_otherwise_take_it():
    """The whole story at once: an old untagged manifest that only a tagged index points at.

    Before #126 this returned both 3 and 1, and deleting 1 left the `debug` tag resolving to an
    index whose amd64 half was gone.
    """
    versions = [
        version(1, day=1, digest=PART),
        version(2, day=2, digest=SAFE, tags=("debug",)),
        version(3, day=3),
    ]
    inside = {SAFE: [PART]}
    safe = reachable(anchors(versions, set()), lambda one: inside.get(one, []))
    assert [one.id for one in doomed(versions, safe, keep=0)] == [3]
