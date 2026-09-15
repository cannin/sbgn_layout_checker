"""Tests for SBGN layout intersection checks."""

from pathlib import Path

from render_sbgn_py.renderer import PixelRect, Point

from sbgn_layout_checker.analyze_sbgn_layout import (
    ResolvedArc,
    analyze_sbgn_file,
    arc_pair_crossings,
    collect_sbgn_files,
    proper_segment_intersection,
    segment_enters_rectangle_interior,
)


def make_arc(arc_id: str, points: tuple[Point, ...]) -> ResolvedArc:
    """Build a resolved arc for geometry tests.

    Args:
        arc_id: Test arc identifier.
        points: Ordered path points.

    Returns:
        Resolved arc with placeholder endpoints.
    """

    return ResolvedArc(
        id=arc_id,
        class_name="production",
        points=points,
        source_id=f"{arc_id}-source",
        target_id=f"{arc_id}-target",
    )


def test_proper_segment_intersection_counts_crossing() -> None:
    """Count a transverse intersection inside both segments."""

    crossing = proper_segment_intersection(
        Point(0.0, 5.0),
        Point(10.0, 5.0),
        Point(5.0, 0.0),
        Point(5.0, 10.0),
    )

    assert crossing == Point(5.0, 5.0)


def test_proper_segment_intersection_ignores_shared_endpoint() -> None:
    """Do not count two segments that only meet at an endpoint."""

    crossing = proper_segment_intersection(
        Point(0.0, 0.0),
        Point(5.0, 5.0),
        Point(5.0, 5.0),
        Point(10.0, 0.0),
    )

    assert crossing is None


def test_proper_segment_intersection_ignores_collinear_overlap() -> None:
    """Do not count overlapping collinear segments as crossings."""

    crossing = proper_segment_intersection(
        Point(0.0, 0.0),
        Point(10.0, 0.0),
        Point(5.0, 0.0),
        Point(15.0, 0.0),
    )

    assert crossing is None


def test_arc_pair_can_have_multiple_crossings() -> None:
    """Count distinct proper intersections of two polyline arcs."""

    horizontal = make_arc(
        "horizontal",
        (Point(0.0, 5.0), Point(10.0, 5.0)),
    )
    zigzag = make_arc(
        "zigzag",
        (
            Point(2.0, 0.0),
            Point(2.0, 10.0),
            Point(8.0, 10.0),
            Point(8.0, 0.0),
        ),
    )

    assert arc_pair_crossings(horizontal, zigzag) == (
        Point(2.0, 5.0),
        Point(8.0, 5.0),
    )


def test_segment_enters_rectangle_interior() -> None:
    """Detect a segment passing through the rectangle interior."""

    rectangle = PixelRect(
        x0=2.0,
        y0=2.0,
        width=6.0,
        height=6.0,
        center=Point(5.0, 5.0),
    )

    assert segment_enters_rectangle_interior(
        Point(0.0, 5.0), Point(10.0, 5.0), rectangle
    )


def test_segment_touching_rectangle_boundary_is_not_overlap() -> None:
    """Ignore a segment that follows a rectangle boundary."""

    rectangle = PixelRect(
        x0=2.0,
        y0=2.0,
        width=6.0,
        height=6.0,
        center=Point(5.0, 5.0),
    )

    assert not segment_enters_rectangle_interior(
        Point(0.0, 2.0), Point(10.0, 2.0), rectangle
    )


def test_collect_sbgn_files_recurses_and_sorts(tmp_path: Path) -> None:
    """Collect only SBGN files from nested input directories."""

    nested = tmp_path / "nested"
    nested.mkdir()
    second = nested / "second.sbgn"
    first = tmp_path / "first.sbgn"
    ignored = tmp_path / "ignored.xml"
    for path in (second, first, ignored):
        path.touch()

    assert collect_sbgn_files([tmp_path]) == (first, second)


def test_example_suite_has_expected_checker_counts() -> None:
    """Analyze all 12 fixed SBGN examples as an integration regression test."""

    example_directory = Path(__file__).parents[2] / "examples" / "sbgn_examples"
    files = collect_sbgn_files([example_directory])
    results = tuple(analyze_sbgn_file(path) for path in files)

    assert len(results) == 12
    assert sum(result.parsed_arc_count for result in results) == 557
    assert all(
        result.parsed_arc_count == result.resolved_arc_count for result in results
    )
    assert sum(len(result.arc_crossings) for result in results) == 37
    assert sum(len(result.arc_node_overlaps) for result in results) == 94


def test_fcose_example_suite_has_expected_checker_counts() -> None:
    """Verify all generated fCoSE examples remain valid regression fixtures."""

    fcose_directory = Path(__file__).parents[2] / "examples" / "sbgn_examples_fcose"
    files = collect_sbgn_files([fcose_directory])
    results = tuple(analyze_sbgn_file(path) for path in files)

    assert len(results) == 12
    assert sum(result.parsed_arc_count for result in results) == 557
    assert all(
        result.parsed_arc_count == result.resolved_arc_count for result in results
    )
    assert sum(len(result.arc_crossings) for result in results) == 425
    assert sum(len(result.arc_node_overlaps) for result in results) == 164
