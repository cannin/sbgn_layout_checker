// Package checker validates geometric layout rules from Chapter 4 of the
// SBGN Process Description Level 1 Version 2.1 specification.
package checker

import (
	"fmt"
	"math"
	"sort"
	"strings"

	"github.com/cannin/sbgn_layout_checker/go/internal/rendersbgn"
)

// Severity distinguishes mandatory requirements from recommendations.
type Severity string

const (
	// SeverityError denotes a violated Chapter 4 requirement.
	SeverityError Severity = "error"
	// SeverityWarning denotes a violated or measurable recommendation.
	SeverityWarning Severity = "warning"
)

// Finding is one layout issue tied to a specification section.
type Finding struct {
	Rule     string            `json:"rule"`
	Severity Severity          `json:"severity"`
	Kind     string            `json:"kind"`
	Message  string            `json:"message"`
	Elements []string          `json:"elements,omitempty"`
	Point    *rendersbgn.Point `json:"point,omitempty"`
}

// Metrics summarizes measurable layout properties from Chapter 4.
type Metrics struct {
	Glyphs               int     `json:"glyphs"`
	Arcs                 int     `json:"arcs"`
	ResolvedArcs         int     `json:"resolved_arcs"`
	ArcCrossings         int     `json:"arc_crossings"`
	ArcNodeCrossings     int     `json:"arc_node_crossings"`
	TotalArcLength       float64 `json:"total_arc_length"`
	ArcBends             int     `json:"arc_bends"`
	MinimumCrossingAngle float64 `json:"minimum_crossing_angle_degrees,omitempty"`
	DrawingWidth         float64 `json:"drawing_width"`
	DrawingHeight        float64 `json:"drawing_height"`
}

// FileReport contains findings and metrics for one SBGN-ML file.
type FileReport struct {
	Path     string    `json:"path"`
	Language string    `json:"language"`
	Metrics  Metrics   `json:"metrics"`
	Findings []Finding `json:"findings"`
}

type labelBox struct {
	id      string
	ownerID string
	edgeID  string
	bbox    rendersbgn.BBox
}

// AnalyzeFile parses and checks one SBGN-ML file.
// Parameters: path names the file to analyze.
func AnalyzeFile(path string) (FileReport, error) {
	document, err := rendersbgn.ParseFile(path)
	if err != nil {
		return FileReport{}, err
	}
	if strings.ToLower(strings.TrimSpace(document.Language)) != "process description" {
		return FileReport{}, fmt.Errorf("map language %q is not process description", document.Language)
	}
	report := AnalyzeDocument(document)
	report.Path = path
	return report, nil
}

// AnalyzeDocument runs all implemented Chapter 4 checks on one document.
// Parameters: document is a normalized SBGN-ML document.
func AnalyzeDocument(document rendersbgn.Document) FileReport {
	resolvedArcs := rendersbgn.ResolveArcs(document.Arcs, document.Glyphs)
	report := FileReport{
		Language: document.Language,
		Metrics: Metrics{
			Glyphs:       len(document.Glyphs),
			Arcs:         len(document.Arcs),
			ResolvedArcs: len(resolvedArcs),
		},
	}

	glyphByID, portParentByID := rendersbgn.BuildLookups(document.Glyphs)
	report.Findings = append(report.Findings, checkNodeOverlaps(document.Glyphs, glyphByID)...)
	report.Findings = append(report.Findings, checkArcInteractions(resolvedArcs, document.Glyphs, &report.Metrics)...)
	report.Findings = append(report.Findings, checkOrientations(document.Glyphs)...)
	report.Findings = append(report.Findings, checkProcessConnections(document.Arcs, glyphByID, portParentByID)...)
	report.Findings = append(report.Findings, checkLabels(document.Glyphs, resolvedArcs)...)
	report.Findings = append(report.Findings, checkCompartments(document.Glyphs, resolvedArcs, glyphByID)...)
	report.Findings = append(report.Findings, checkUnitsOfInformation(document.Glyphs)...)
	measureDrawing(document.Glyphs, resolvedArcs, &report.Metrics)
	sort.SliceStable(report.Findings, func(i, j int) bool {
		if report.Findings[i].Rule != report.Findings[j].Rule {
			return report.Findings[i].Rule < report.Findings[j].Rule
		}
		if report.Findings[i].Kind != report.Findings[j].Kind {
			return report.Findings[i].Kind < report.Findings[j].Kind
		}
		return strings.Join(report.Findings[i].Elements, "\x00") < strings.Join(report.Findings[j].Elements, "\x00")
	})
	if report.Findings == nil {
		report.Findings = []Finding{}
	}
	return report
}

// checkNodeOverlaps implements the axis-aligned portion of Section 4.2.1.
// Parameters: glyphs are parsed nodes; glyphByID resolves parent classes.
func checkNodeOverlaps(glyphs []rendersbgn.Glyph, glyphByID map[string]*rendersbgn.Glyph) []Finding {
	var findings []Finding
	for firstIndex := range glyphs {
		first := &glyphs[firstIndex]
		if first.BBox == nil || first.ID == "" {
			continue
		}
		for secondIndex := firstIndex + 1; secondIndex < len(glyphs); secondIndex++ {
			second := &glyphs[secondIndex]
			if second.BBox == nil || second.ID == "" || !rectsContact(*first.BBox, *second.BBox) {
				continue
			}
			if allowedNodeContact(first, second, glyphByID) {
				continue
			}
			kind := "node_touch"
			if rectsInteriorOverlap(*first.BBox, *second.BBox) {
				kind = "node_overlap"
			}
			findings = append(findings, Finding{
				Rule: "4.2.1", Severity: SeverityError, Kind: kind,
				Message:  fmt.Sprintf("nodes %q and %q overlap or touch without an allowed containment relationship", first.ID, second.ID),
				Elements: []string{first.ID, second.ID},
			})
		}
	}
	return findings
}

// allowedNodeContact applies the explicit containment and complex-subunit exceptions.
// Parameters: first and second are contacting nodes; glyphByID resolves parents.
func allowedNodeContact(first, second *rendersbgn.Glyph, glyphByID map[string]*rendersbgn.Glyph) bool {
	if first.ParentID == second.ID {
		return isAuxiliaryClass(first.ClassName) || mayContain(second.ClassName, first.ClassName)
	}
	if second.ParentID == first.ID {
		return isAuxiliaryClass(second.ClassName) || mayContain(first.ClassName, second.ClassName)
	}
	if rectContains(*first.BBox, *second.BBox) && mayContain(first.ClassName, second.ClassName) {
		return true
	}
	if rectContains(*second.BBox, *first.BBox) && mayContain(second.ClassName, first.ClassName) {
		return true
	}
	if !rectsInteriorOverlap(*first.BBox, *second.BBox) && first.ParentID != "" && first.ParentID == second.ParentID {
		parent := glyphByID[first.ParentID]
		if parent != nil && isComplexClass(parent.ClassName) && isEntityPoolNode(first.ClassName) && isEntityPoolNode(second.ClassName) {
			return true
		}
	}
	return false
}

// isAuxiliaryClass reports glyphs intentionally attached to a parent node.
// Parameters: className is an SBGN glyph class.
func isAuxiliaryClass(className string) bool {
	return className == "unit of information" || className == "state variable" || className == "terminal"
}

// mayContain implements the containment table in Section 3.4.2.
// Parameters: containerClass and childClass are normalized SBGN class names.
func mayContain(containerClass, childClass string) bool {
	if containerClass == "compartment" {
		return true
	}
	if !isComplexClass(containerClass) {
		return false
	}
	return isEntityPoolNode(childClass) || childClass == "state variable" ||
		childClass == "unit of information" || isComplexClass(childClass)
}

// isEntityPoolNode reports classes allowed as complex subunits.
// Parameters: className is an SBGN glyph class.
func isEntityPoolNode(className string) bool {
	switch className {
	case "unspecified entity", "simple chemical", "macromolecule", "nucleic acid feature",
		"simple chemical multimer", "macromolecule multimer", "nucleic acid feature multimer":
		return true
	default:
		return false
	}
}

// isComplexClass reports complex and complex-multimer containers.
// Parameters: className is an SBGN glyph class.
func isComplexClass(className string) bool {
	return className == "complex" || className == "complex multimer"
}

// checkArcInteractions implements Sections 4.2.3, 4.2.4, 4.3.1, and 4.3.3.
// Parameters: arcs are resolved polylines; glyphs are parsed nodes; metrics receives counts.
func checkArcInteractions(arcs []rendersbgn.ResolvedArc, glyphs []rendersbgn.Glyph, metrics *Metrics) []Finding {
	var findings []Finding
	for _, arc := range arcs {
		findings = append(findings, checkOneArcAgainstNodes(arc, glyphs, metrics)...)
		findings = append(findings, checkArcSelfIntersections(arc)...)
	}
	for firstIndex := range arcs {
		for secondIndex := firstIndex + 1; secondIndex < len(arcs); secondIndex++ {
			findings = append(findings, checkArcPair(arcs[firstIndex], arcs[secondIndex], metrics)...)
		}
	}
	return findings
}

// checkOneArcAgainstNodes checks border overlaps, repeated boundary crossings, and avoidable node crossings.
// Parameters: arc is one polyline; glyphs are candidate nodes; metrics receives crossing counts.
func checkOneArcAgainstNodes(arc rendersbgn.ResolvedArc, glyphs []rendersbgn.Glyph, metrics *Metrics) []Finding {
	var findings []Finding
	for index := range glyphs {
		glyph := &glyphs[index]
		if glyph.BBox == nil || rendersbgn.IsHiddenGlyphClass(glyph.ClassName) {
			continue
		}
		borderOverlap := false
		var boundaryPoints []rendersbgn.Point
		crossesInterior := false
		for pointIndex := 0; pointIndex+1 < len(arc.Points); pointIndex++ {
			start, end := arc.Points[pointIndex], arc.Points[pointIndex+1]
			borderOverlap = borderOverlap || segmentOverlapsRectBorder(start, end, *glyph.BBox)
			for _, point := range rectBoundaryIntersections(start, end, *glyph.BBox) {
				if !containsPoint(boundaryPoints, point) {
					boundaryPoints = append(boundaryPoints, point)
				}
			}
			crossesInterior = crossesInterior || segmentEntersRectInterior(start, end, *glyph.BBox)
		}
		if borderOverlap {
			findings = append(findings, Finding{
				Rule: "4.2.3", Severity: SeverityError, Kind: "node_border_edge_overlap",
				Message:  fmt.Sprintf("arc %q overlaps the border of node %q", arc.ID, glyph.ID),
				Elements: []string{arc.ID, glyph.ID},
			})
		}
		if len(boundaryPoints) > 2 {
			findings = append(findings, Finding{
				Rule: "4.2.4", Severity: SeverityError, Kind: "node_boundary_crossed_more_than_twice",
				Message:  fmt.Sprintf("arc %q crosses node %q's boundary %d times", arc.ID, glyph.ID, len(boundaryPoints)),
				Elements: []string{arc.ID, glyph.ID},
			})
		}
		if glyph.ClassName != "compartment" && glyph.ID != arc.SourceID && glyph.ID != arc.TargetID && crossesInterior {
			metrics.ArcNodeCrossings++
			findings = append(findings, Finding{
				Rule: "4.3.1", Severity: SeverityWarning, Kind: "node_edge_crossing",
				Message:  fmt.Sprintf("arc %q crosses non-endpoint node %q", arc.ID, glyph.ID),
				Elements: []string{arc.ID, glyph.ID},
			})
		}
	}
	return findings
}

// checkArcSelfIntersections reports forbidden non-adjacent segment contacts.
// Parameters: arc is one resolved polyline.
func checkArcSelfIntersections(arc rendersbgn.ResolvedArc) []Finding {
	for first := 0; first+1 < len(arc.Points); first++ {
		for second := first + 2; second+1 < len(arc.Points); second++ {
			kind, point := segmentIntersection(arc.Points[first], arc.Points[first+1], arc.Points[second], arc.Points[second+1])
			if kind == intersectionNone {
				continue
			}
			return []Finding{{
				Rule: "4.2.4", Severity: SeverityError, Kind: "edge_self_intersection",
				Message: fmt.Sprintf("arc %q intersects itself", arc.ID), Elements: []string{arc.ID}, Point: point,
			}}
		}
	}
	return nil
}

// checkArcPair reports touching/overlap violations and measures proper crossings.
// Parameters: first and second are resolved polylines; metrics receives crossing counts.
func checkArcPair(first, second rendersbgn.ResolvedArc, metrics *Metrics) []Finding {
	var findings []Finding
	var crossings []rendersbgn.Point
	contactReported := false
	for firstIndex := 0; firstIndex+1 < len(first.Points); firstIndex++ {
		for secondIndex := 0; secondIndex+1 < len(second.Points); secondIndex++ {
			kind, point := segmentIntersection(first.Points[firstIndex], first.Points[firstIndex+1], second.Points[secondIndex], second.Points[secondIndex+1])
			switch kind {
			case intersectionProper:
				if point != nil && !containsPoint(crossings, *point) {
					crossings = append(crossings, *point)
					angle := crossingAngle(first.Points[firstIndex], first.Points[firstIndex+1], second.Points[secondIndex], second.Points[secondIndex+1])
					if metrics.MinimumCrossingAngle == 0 || angle < metrics.MinimumCrossingAngle {
						metrics.MinimumCrossingAngle = angle
					}
				}
			case intersectionTouch, intersectionOverlap:
				if contactReported || legitimateSharedTerminalContact(first, second, firstIndex, secondIndex, kind, point) {
					continue
				}
				contactReported = true
				findings = append(findings, Finding{
					Rule: "4.2.4", Severity: SeverityError, Kind: "edge_edge_overlap_or_touch",
					Message:  fmt.Sprintf("arcs %q and %q overlap or touch", first.ID, second.ID),
					Elements: []string{first.ID, second.ID}, Point: point,
				})
			}
		}
	}
	metrics.ArcCrossings += len(crossings)
	for _, point := range crossings {
		pointCopy := point
		findings = append(findings, Finding{
			Rule: "4.3.3", Severity: SeverityWarning, Kind: "edge_crossing",
			Message:  fmt.Sprintf("arcs %q and %q cross", first.ID, second.ID),
			Elements: []string{first.ID, second.ID}, Point: &pointCopy,
		})
	}
	if len(crossings) > 1 {
		findings = append(findings, Finding{
			Rule: "4.2.4", Severity: SeverityError, Kind: "edges_cross_more_than_once",
			Message:  fmt.Sprintf("arcs %q and %q cross %d times", first.ID, second.ID, len(crossings)),
			Elements: []string{first.ID, second.ID},
		})
	}
	return findings
}

// legitimateSharedTerminalContact recognizes branches meeting at a shared node.
// Parameters: first and second are arcs; remaining values describe the contact.
func legitimateSharedTerminalContact(first, second rendersbgn.ResolvedArc, _ int, _ int, _ intersectionKind, _ *rendersbgn.Point) bool {
	return first.SourceID == second.SourceID || first.SourceID == second.TargetID ||
		first.TargetID == second.SourceID || first.TargetID == second.TargetID
}

// crossingAngle returns the acute angle between two segment directions.
// Parameters: a-b and c-d are crossing segments.
func crossingAngle(a, b, c, d rendersbgn.Point) float64 {
	dx1, dy1 := b.X-a.X, b.Y-a.Y
	dx2, dy2 := d.X-c.X, d.Y-c.Y
	denominator := math.Hypot(dx1, dy1) * math.Hypot(dx2, dy2)
	if denominator <= geometryEpsilon {
		return 0
	}
	cosine := math.Abs((dx1*dx2 + dy1*dy2) / denominator)
	cosine = math.Min(1.0, math.Max(0.0, cosine))
	return math.Acos(cosine) * 180.0 / math.Pi
}

// checkOrientations implements the machine-readable part of Section 4.2.5.
// Parameters: glyphs are parsed nodes.
func checkOrientations(glyphs []rendersbgn.Glyph) []Finding {
	var findings []Finding
	for _, glyph := range glyphs {
		orientation := strings.ToLower(strings.TrimSpace(glyph.Orientation))
		if orientation == "" || orientation == "horizontal" || orientation == "vertical" ||
			orientation == "left" || orientation == "right" || orientation == "up" || orientation == "down" {
			continue
		}
		findings = append(findings, Finding{
			Rule: "4.2.5", Severity: SeverityError, Kind: "invalid_node_orientation",
			Message:  fmt.Sprintf("node %q has non-axis-aligned orientation %q", glyph.ID, glyph.Orientation),
			Elements: []string{glyph.ID},
		})
	}
	return findings
}
