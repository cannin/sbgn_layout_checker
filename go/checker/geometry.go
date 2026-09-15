package checker

import (
	"math"

	"github.com/cannin/sbgn_layout_checker/go/internal/rendersbgn"
)

const geometryEpsilon = 1e-9

type intersectionKind int

const (
	intersectionNone intersectionKind = iota
	intersectionProper
	intersectionTouch
	intersectionOverlap
)

// crossProduct returns the signed cross product of vectors AB and AC.
// Parameters: a is the shared origin; b and c are vector endpoints.
func crossProduct(a, b, c rendersbgn.Point) float64 {
	return (b.X-a.X)*(c.Y-a.Y) - (b.Y-a.Y)*(c.X-a.X)
}

// pointEqual reports whether two source-coordinate points are effectively equal.
// Parameters: first and second are the compared points.
func pointEqual(first, second rendersbgn.Point) bool {
	return math.Abs(first.X-second.X) <= geometryEpsilon && math.Abs(first.Y-second.Y) <= geometryEpsilon
}

// pointOnSegment reports whether a point lies on the closed segment AB.
// Parameters: point is tested against segment start-end.
func pointOnSegment(point, start, end rendersbgn.Point) bool {
	if math.Abs(crossProduct(start, end, point)) > geometryEpsilon {
		return false
	}
	return point.X >= math.Min(start.X, end.X)-geometryEpsilon &&
		point.X <= math.Max(start.X, end.X)+geometryEpsilon &&
		point.Y >= math.Min(start.Y, end.Y)-geometryEpsilon &&
		point.Y <= math.Max(start.Y, end.Y)+geometryEpsilon
}

// segmentIntersection classifies the geometric contact between two segments.
// Parameters: a-b and c-d are the two closed line segments.
func segmentIntersection(a, b, c, d rendersbgn.Point) (intersectionKind, *rendersbgn.Point) {
	if pointEqual(a, b) || pointEqual(c, d) {
		return intersectionNone, nil
	}
	abc := crossProduct(a, b, c)
	abd := crossProduct(a, b, d)
	cda := crossProduct(c, d, a)
	cdb := crossProduct(c, d, b)

	proper := ((abc > geometryEpsilon && abd < -geometryEpsilon) ||
		(abc < -geometryEpsilon && abd > geometryEpsilon)) &&
		((cda > geometryEpsilon && cdb < -geometryEpsilon) ||
			(cda < -geometryEpsilon && cdb > geometryEpsilon))
	if proper {
		dx1, dy1 := b.X-a.X, b.Y-a.Y
		dx2, dy2 := d.X-c.X, d.Y-c.Y
		denominator := dx1*dy2 - dy1*dx2
		parameter := ((c.X-a.X)*dy2 - (c.Y-a.Y)*dx2) / denominator
		point := rendersbgn.Point{X: a.X + parameter*dx1, Y: a.Y + parameter*dy1}
		return intersectionProper, &point
	}

	collinear := math.Abs(abc) <= geometryEpsilon && math.Abs(abd) <= geometryEpsilon &&
		math.Abs(cda) <= geometryEpsilon && math.Abs(cdb) <= geometryEpsilon
	if collinear {
		useX := math.Abs(b.X-a.X) >= math.Abs(b.Y-a.Y)
		firstA, firstB, secondA, secondB := a.X, b.X, c.X, d.X
		if !useX {
			firstA, firstB, secondA, secondB = a.Y, b.Y, c.Y, d.Y
		}
		overlap := math.Min(math.Max(firstA, firstB), math.Max(secondA, secondB)) -
			math.Max(math.Min(firstA, firstB), math.Min(secondA, secondB))
		if overlap > geometryEpsilon {
			return intersectionOverlap, nil
		}
		if overlap >= -geometryEpsilon {
			for _, point := range []rendersbgn.Point{a, b, c, d} {
				if pointOnSegment(point, a, b) && pointOnSegment(point, c, d) {
					copy := point
					return intersectionTouch, &copy
				}
			}
		}
		return intersectionNone, nil
	}

	for _, candidate := range []struct {
		point rendersbgn.Point
		start rendersbgn.Point
		end   rendersbgn.Point
	}{
		{a, c, d}, {b, c, d}, {c, a, b}, {d, a, b},
	} {
		if pointOnSegment(candidate.point, candidate.start, candidate.end) {
			point := candidate.point
			return intersectionTouch, &point
		}
	}
	return intersectionNone, nil
}

// segmentEntersRectInterior reports whether a segment enters an open rectangle.
// Parameters: start-end is the line segment; bbox is the rectangle.
func segmentEntersRectInterior(start, end rendersbgn.Point, bbox rendersbgn.BBox) bool {
	xInterval, xOK := openAxisInterval(start.X, end.X-start.X, bbox.X, bbox.X+bbox.W)
	yInterval, yOK := openAxisInterval(start.Y, end.Y-start.Y, bbox.Y, bbox.Y+bbox.H)
	if !xOK || !yOK {
		return false
	}
	lower := math.Max(0.0, math.Max(xInterval[0], yInterval[0]))
	upper := math.Min(1.0, math.Min(xInterval[1], yInterval[1]))
	return upper-lower > geometryEpsilon
}

// openAxisInterval returns parameters placing a segment axis inside open bounds.
// Parameters: start and delta describe the axis; lower-upper are open bounds.
func openAxisInterval(start, delta, lower, upper float64) ([2]float64, bool) {
	if upper-lower <= geometryEpsilon {
		return [2]float64{}, false
	}
	if math.Abs(delta) <= geometryEpsilon {
		if lower < start && start < upper {
			return [2]float64{math.Inf(-1), math.Inf(1)}, true
		}
		return [2]float64{}, false
	}
	first := (lower - start) / delta
	second := (upper - start) / delta
	return [2]float64{math.Min(first, second), math.Max(first, second)}, true
}

// rectsContact reports overlap or boundary contact between two boxes.
// Parameters: first and second are closed rectangles.
func rectsContact(first, second rendersbgn.BBox) bool {
	return first.X <= second.X+second.W+geometryEpsilon &&
		second.X <= first.X+first.W+geometryEpsilon &&
		first.Y <= second.Y+second.H+geometryEpsilon &&
		second.Y <= first.Y+first.H+geometryEpsilon
}

// rectsInteriorOverlap reports a positive-area intersection between two boxes.
// Parameters: first and second are closed rectangles.
func rectsInteriorOverlap(first, second rendersbgn.BBox) bool {
	width := math.Min(first.X+first.W, second.X+second.W) - math.Max(first.X, second.X)
	height := math.Min(first.Y+first.H, second.Y+second.H) - math.Max(first.Y, second.Y)
	return width > geometryEpsilon && height > geometryEpsilon
}

// rectContains reports whether outer fully contains inner, including boundaries.
// Parameters: outer is the candidate container; inner is the contained box.
func rectContains(outer, inner rendersbgn.BBox) bool {
	return inner.X >= outer.X-geometryEpsilon && inner.Y >= outer.Y-geometryEpsilon &&
		inner.X+inner.W <= outer.X+outer.W+geometryEpsilon &&
		inner.Y+inner.H <= outer.Y+outer.H+geometryEpsilon
}

// pointInRect reports whether a point is in a closed rectangle.
// Parameters: point is tested against bbox.
func pointInRect(point rendersbgn.Point, bbox rendersbgn.BBox) bool {
	return point.X >= bbox.X-geometryEpsilon && point.X <= bbox.X+bbox.W+geometryEpsilon &&
		point.Y >= bbox.Y-geometryEpsilon && point.Y <= bbox.Y+bbox.H+geometryEpsilon
}

// segmentOverlapsRectBorder reports a positive-length collinear border overlap.
// Parameters: start-end is an edge segment; bbox supplies four border segments.
func segmentOverlapsRectBorder(start, end rendersbgn.Point, bbox rendersbgn.BBox) bool {
	topLeft := rendersbgn.Point{X: bbox.X, Y: bbox.Y}
	topRight := rendersbgn.Point{X: bbox.X + bbox.W, Y: bbox.Y}
	bottomLeft := rendersbgn.Point{X: bbox.X, Y: bbox.Y + bbox.H}
	bottomRight := rendersbgn.Point{X: bbox.X + bbox.W, Y: bbox.Y + bbox.H}
	for _, border := range [][2]rendersbgn.Point{
		{topLeft, topRight}, {topRight, bottomRight},
		{bottomRight, bottomLeft}, {bottomLeft, topLeft},
	} {
		kind, _ := segmentIntersection(start, end, border[0], border[1])
		if kind == intersectionOverlap {
			return true
		}
	}
	return false
}

// rectBoundaryIntersections returns unique points where a segment meets a box border.
// Parameters: start-end is an edge segment; bbox supplies four border segments.
func rectBoundaryIntersections(start, end rendersbgn.Point, bbox rendersbgn.BBox) []rendersbgn.Point {
	topLeft := rendersbgn.Point{X: bbox.X, Y: bbox.Y}
	topRight := rendersbgn.Point{X: bbox.X + bbox.W, Y: bbox.Y}
	bottomLeft := rendersbgn.Point{X: bbox.X, Y: bbox.Y + bbox.H}
	bottomRight := rendersbgn.Point{X: bbox.X + bbox.W, Y: bbox.Y + bbox.H}
	var points []rendersbgn.Point
	for _, border := range [][2]rendersbgn.Point{
		{topLeft, topRight}, {topRight, bottomRight},
		{bottomRight, bottomLeft}, {bottomLeft, topLeft},
	} {
		kind, point := segmentIntersection(start, end, border[0], border[1])
		if (kind == intersectionProper || kind == intersectionTouch) && point != nil {
			if !containsPoint(points, *point) {
				points = append(points, *point)
			}
		}
	}
	return points
}

// containsPoint reports whether points already contains candidate.
// Parameters: points is the searched slice; candidate is compared geometrically.
func containsPoint(points []rendersbgn.Point, candidate rendersbgn.Point) bool {
	for _, point := range points {
		if pointEqual(point, candidate) {
			return true
		}
	}
	return false
}
