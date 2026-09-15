package checker

import (
	"fmt"
	"math"
	"strings"

	"github.com/cannin/sbgn_layout_checker/go/internal/rendersbgn"
)

type attachmentSide string

const (
	sideLeft   attachmentSide = "left"
	sideRight  attachmentSide = "right"
	sideTop    attachmentSide = "top"
	sideBottom attachmentSide = "bottom"
)

// checkProcessConnections implements Section 4.2.6 using explicit arc endpoints and ports.
// Parameters: arcs are parsed arcs; glyphByID and portParentByID resolve endpoint ownership.
func checkProcessConnections(arcs []rendersbgn.Arc, glyphByID map[string]*rendersbgn.Glyph, portParentByID map[string]string) []Finding {
	type processConnections struct {
		consumptionSides []attachmentSide
		productionSides  []attachmentSide
		modulationSides  []attachmentSide
	}
	connections := map[string]*processConnections{}
	var findings []Finding
	for _, arc := range arcs {
		processID, reference, point, ok := processEndpoint(arc, glyphByID, portParentByID)
		if !ok {
			continue
		}
		process := glyphByID[processID]
		side, centered, valid := classifyAttachment(*process.BBox, point)
		if !valid {
			findings = append(findings, Finding{
				Rule: "4.2.6", Severity: SeverityError, Kind: "process_arc_not_on_side",
				Message:  fmt.Sprintf("arc %q does not attach to a side of process %q", arc.ID, processID),
				Elements: []string{arc.ID, processID},
			})
			continue
		}
		entry := connections[processID]
		if entry == nil {
			entry = &processConnections{}
			connections[processID] = entry
		}
		switch arc.ClassName {
		case "consumption":
			entry.consumptionSides = append(entry.consumptionSides, side)
			if !centered {
				findings = append(findings, Finding{
					Rule: "4.2.6", Severity: SeverityError, Kind: "process_flow_not_centered",
					Message:  fmt.Sprintf("%s arc %q is not centered on a side of process %q", arc.ClassName, arc.ID, processID),
					Elements: []string{arc.ID, processID, reference},
				})
			}
		case "production":
			entry.productionSides = append(entry.productionSides, side)
			if !centered {
				findings = append(findings, Finding{
					Rule: "4.2.6", Severity: SeverityError, Kind: "process_flow_not_centered",
					Message:  fmt.Sprintf("%s arc %q is not centered on a side of process %q", arc.ClassName, arc.ID, processID),
					Elements: []string{arc.ID, processID, reference},
				})
			}
		case "modulation", "stimulation", "catalysis", "inhibition", "necessary stimulation":
			entry.modulationSides = append(entry.modulationSides, side)
		}
	}

	for processID, entry := range connections {
		flowAxis := ""
		flowSides := append(append([]attachmentSide{}, entry.consumptionSides...), entry.productionSides...)
		for _, side := range flowSides {
			axis := sideAxis(side)
			if flowAxis == "" {
				flowAxis = axis
			} else if axis != flowAxis {
				findings = append(findings, Finding{
					Rule: "4.2.6", Severity: SeverityError, Kind: "process_flow_sides_not_opposite",
					Message:  fmt.Sprintf("consumption and production arcs use non-opposite sides of process %q", processID),
					Elements: []string{processID},
				})
				flowAxis = "mixed"
				break
			}
		}
		if flowAxis == "" || flowAxis == "mixed" {
			continue
		}
		sameSide := false
		for _, consumptionSide := range entry.consumptionSides {
			for _, productionSide := range entry.productionSides {
				if consumptionSide == productionSide {
					sameSide = true
					break
				}
			}
			if sameSide {
				break
			}
		}
		if sameSide {
			findings = append(findings, Finding{
				Rule: "4.2.6", Severity: SeverityError, Kind: "process_flow_sides_not_opposite",
				Message:  fmt.Sprintf("consumption and production arcs use the same side of process %q", processID),
				Elements: []string{processID},
			})
		}
		for _, side := range entry.modulationSides {
			if sideAxis(side) == flowAxis {
				findings = append(findings, Finding{
					Rule: "4.2.6", Severity: SeverityError, Kind: "modulation_on_flow_side",
					Message:  fmt.Sprintf("a modulatory arc uses a consumption/production side of process %q", processID),
					Elements: []string{processID},
				})
				break
			}
		}
	}
	return findings
}

// processEndpoint finds the process-like endpoint and its rendered attachment point.
// Parameters: arc is inspected; glyphByID and portParentByID resolve references.
func processEndpoint(arc rendersbgn.Arc, glyphByID map[string]*rendersbgn.Glyph, portParentByID map[string]string) (string, string, rendersbgn.Point, bool) {
	if len(arc.Points) < 2 {
		return "", "", rendersbgn.Point{}, false
	}
	for _, endpoint := range []struct {
		reference string
		point     rendersbgn.Point
	}{
		{arc.Source, arc.Points[0]},
		{arc.Target, arc.Points[len(arc.Points)-1]},
	} {
		glyphID := endpoint.reference
		if parentID, ok := portParentByID[endpoint.reference]; ok {
			glyphID = parentID
		}
		glyph := glyphByID[glyphID]
		if glyph == nil || glyph.BBox == nil || !isProcessClass(glyph.ClassName) {
			continue
		}
		point := endpoint.point
		for _, port := range glyph.Ports {
			if port.ID == endpoint.reference {
				point = port.Point
				break
			}
		}
		return glyphID, endpoint.reference, point, true
	}
	return "", "", rendersbgn.Point{}, false
}

// isProcessClass reports process nodes covered by Section 4.2.6.
// Parameters: className is an SBGN glyph class.
func isProcessClass(className string) bool {
	switch className {
	case "process", "omitted process", "uncertain process", "association", "dissociation":
		return true
	default:
		return false
	}
}

// classifyAttachment identifies the nearest box side and whether it is centered.
// Parameters: bbox is the process symbol; point is the arc or port endpoint.
func classifyAttachment(bbox rendersbgn.BBox, point rendersbgn.Point) (attachmentSide, bool, bool) {
	center := bbox.Center()
	dx, dy := point.X-center.X, point.Y-center.Y
	if math.Abs(dx) <= geometryEpsilon && math.Abs(dy) <= geometryEpsilon {
		return "", false, false
	}
	if math.Abs(dx) >= math.Abs(dy) {
		side := sideRight
		if dx < 0 {
			side = sideLeft
		}
		onSide := point.Y >= bbox.Y-geometryEpsilon && point.Y <= bbox.Y+bbox.H+geometryEpsilon
		if side == sideLeft {
			onSide = onSide && point.X <= bbox.X+geometryEpsilon
		} else {
			onSide = onSide && point.X >= bbox.X+bbox.W-geometryEpsilon
		}
		return side, math.Abs(dy) <= geometryEpsilon, onSide
	}
	side := sideBottom
	if dy < 0 {
		side = sideTop
	}
	onSide := point.X >= bbox.X-geometryEpsilon && point.X <= bbox.X+bbox.W+geometryEpsilon
	if side == sideTop {
		onSide = onSide && point.Y <= bbox.Y+geometryEpsilon
	} else {
		onSide = onSide && point.Y >= bbox.Y+bbox.H-geometryEpsilon
	}
	return side, math.Abs(dx) <= geometryEpsilon, onSide
}

// sideAxis maps opposite rectangle sides to their shared axis.
// Parameters: side is one classified attachment side.
func sideAxis(side attachmentSide) string {
	if side == sideLeft || side == sideRight {
		return "horizontal"
	}
	return "vertical"
}

// checkLabels implements the checks possible from explicit label bounding boxes.
// Parameters: glyphs contain node labels; arcs contain edge-label auxiliary glyphs.
func checkLabels(glyphs []rendersbgn.Glyph, arcs []rendersbgn.ResolvedArc) []Finding {
	var findings []Finding
	var nodeLabels []labelBox
	var edgeLabels []labelBox
	for _, glyph := range glyphs {
		if glyph.Label.BBox == nil || glyph.BBox == nil {
			continue
		}
		label := labelBox{id: glyph.ID + "::label", ownerID: glyph.ID, bbox: *glyph.Label.BBox}
		nodeLabels = append(nodeLabels, label)
		if !rectsInteriorOverlap(label.bbox, *glyph.BBox) {
			findings = append(findings, Finding{
				Rule: "4.2.7", Severity: SeverityError, Kind: "node_label_outside_node",
				Message: fmt.Sprintf("label for node %q has no area inside its node", glyph.ID), Elements: []string{glyph.ID},
			})
		} else if !rectContains(*glyph.BBox, label.bbox) {
			findings = append(findings, Finding{
				Rule: "4.3.2", Severity: SeverityWarning, Kind: "node_label_not_fully_inside",
				Message: fmt.Sprintf("label for node %q is not completely inside its node", glyph.ID), Elements: []string{glyph.ID},
			})
		}
	}
	for _, arc := range arcs {
		for _, glyph := range arc.AuxiliaryGlyphs {
			if glyph.BBox != nil && strings.TrimSpace(glyph.Label.Text) != "" {
				edgeLabels = append(edgeLabels, labelBox{id: glyph.ID + "::label", edgeID: arc.ID, bbox: *glyph.BBox})
			}
		}
	}

	for _, label := range nodeLabels {
		for _, glyph := range glyphs {
			if glyph.BBox == nil || glyph.ID == label.ownerID {
				continue
			}
			if rectsContact(label.bbox, *glyph.BBox) {
				findings = append(findings, Finding{
					Rule: "4.2.7", Severity: SeverityError, Kind: "node_label_overlaps_node",
					Message:  fmt.Sprintf("label for node %q overlaps or touches node %q", label.ownerID, glyph.ID),
					Elements: []string{label.ownerID, glyph.ID},
				})
			}
		}
	}
	allLabels := append(append([]labelBox{}, nodeLabels...), edgeLabels...)
	for first := range allLabels {
		for second := first + 1; second < len(allLabels); second++ {
			if rectsContact(allLabels[first].bbox, allLabels[second].bbox) {
				rule := "4.3.2"
				severity := SeverityWarning
				if allLabels[first].ownerID != "" || allLabels[second].ownerID != "" {
					rule = "4.2.7"
					severity = SeverityError
				}
				findings = append(findings, Finding{
					Rule: rule, Severity: severity, Kind: "label_label_overlap",
					Message:  fmt.Sprintf("labels %q and %q overlap or touch", allLabels[first].id, allLabels[second].id),
					Elements: []string{allLabels[first].id, allLabels[second].id},
				})
			}
		}
	}
	for _, label := range edgeLabels {
		for _, glyph := range glyphs {
			if glyph.BBox != nil && rectsContact(label.bbox, *glyph.BBox) {
				findings = append(findings, Finding{
					Rule: "4.2.8", Severity: SeverityError, Kind: "edge_label_overlaps_node",
					Message:  fmt.Sprintf("edge label %q overlaps or touches node %q", label.id, glyph.ID),
					Elements: []string{label.id, glyph.ID},
				})
			}
		}
		for _, arc := range arcs {
			for index := 0; index+1 < len(arc.Points); index++ {
				if segmentEntersRectInterior(arc.Points[index], arc.Points[index+1], label.bbox) || segmentOverlapsRectBorder(arc.Points[index], arc.Points[index+1], label.bbox) {
					findings = append(findings, Finding{
						Rule: "4.3.2", Severity: SeverityWarning, Kind: "edge_label_overlaps_edge",
						Message:  fmt.Sprintf("edge label %q overlaps arc %q", label.id, arc.ID),
						Elements: []string{label.id, arc.ID},
					})
					break
				}
			}
		}
	}
	return findings
}

// checkCompartments implements the decidable portion of Section 4.2.9.
// Parameters: glyphs and arcs form the diagram; glyphByID resolves participants.
func checkCompartments(glyphs []rendersbgn.Glyph, arcs []rendersbgn.ResolvedArc, glyphByID map[string]*rendersbgn.Glyph) []Finding {
	var findings []Finding
	compartments := collectCompartments(glyphs)
	for _, process := range glyphs {
		if !isProcessClass(process.ClassName) || process.BBox == nil {
			continue
		}
		attached := attachedProcessArcs(process.ID, arcs)
		participantCompartments := map[string]bool{}
		allKnown := len(attached) > 0
		for _, arc := range attached {
			participantID := arc.SourceID
			if participantID == process.ID {
				participantID = arc.TargetID
			}
			participant := glyphByID[participantID]
			if participant == nil {
				allKnown = false
				continue
			}
			compartmentID := owningCompartment(*participant, compartments, glyphByID)
			if compartmentID == "" {
				allKnown = false
				continue
			}
			participantCompartments[compartmentID] = true
		}
		if len(participantCompartments) == 1 && allKnown {
			var compartmentID string
			for id := range participantCompartments {
				compartmentID = id
			}
			compartment := glyphByID[compartmentID]
			if compartment == nil || compartment.BBox == nil {
				continue
			}
			if !rectContains(*compartment.BBox, *process.BBox) {
				findings = append(findings, Finding{
					Rule: "4.2.9", Severity: SeverityError, Kind: "process_outside_participant_compartment",
					Message:  fmt.Sprintf("process %q is not inside participant compartment %q", process.ID, compartmentID),
					Elements: []string{process.ID, compartmentID},
				})
			}
			for _, arc := range attached {
				if !polylineInsideRect(arc.Points, *compartment.BBox) {
					findings = append(findings, Finding{
						Rule: "4.2.9", Severity: SeverityError, Kind: "process_arc_outside_compartment",
						Message:  fmt.Sprintf("arc %q of process %q leaves participant compartment %q", arc.ID, process.ID, compartmentID),
						Elements: []string{arc.ID, process.ID, compartmentID},
					})
				}
			}
		} else if len(participantCompartments) >= 2 {
			processCompartment := owningCompartment(process, compartments, glyphByID)
			if processCompartment != "" && !participantCompartments[processCompartment] {
				findings = append(findings, Finding{
					Rule: "4.2.9", Severity: SeverityError, Kind: "process_in_unrelated_compartment",
					Message:  fmt.Sprintf("process %q is in compartment %q, which contains none of its participants", process.ID, processCompartment),
					Elements: []string{process.ID, processCompartment},
				})
			}
		}
	}
	return findings
}

// collectCompartments builds a compartment lookup from glyphs with geometry.
// Parameters: glyphs is the parsed flattened glyph list.
func collectCompartments(glyphs []rendersbgn.Glyph) map[string]*rendersbgn.Glyph {
	compartments := map[string]*rendersbgn.Glyph{}
	for index := range glyphs {
		glyph := &glyphs[index]
		if glyph.ClassName == "compartment" && glyph.BBox != nil && glyph.ID != "" {
			compartments[glyph.ID] = glyph
		}
	}
	return compartments
}

// attachedProcessArcs returns arcs connected to one process.
// Parameters: processID is matched against resolved source and target IDs; arcs is the diagram edge list.
func attachedProcessArcs(processID string, arcs []rendersbgn.ResolvedArc) []rendersbgn.ResolvedArc {
	var attached []rendersbgn.ResolvedArc
	for _, arc := range arcs {
		if arc.SourceID == processID || arc.TargetID == processID {
			attached = append(attached, arc)
		}
	}
	return attached
}

// owningCompartment resolves explicit ownership, nesting, or smallest geometric containment.
// Parameters: glyph is located; compartments and glyphByID provide candidate owners.
func owningCompartment(glyph rendersbgn.Glyph, compartments map[string]*rendersbgn.Glyph, glyphByID map[string]*rendersbgn.Glyph) string {
	if _, ok := compartments[glyph.CompartmentRef]; ok {
		return glyph.CompartmentRef
	}
	parentID := glyph.ParentID
	for parentID != "" {
		if _, ok := compartments[parentID]; ok {
			return parentID
		}
		parent := glyphByID[parentID]
		if parent == nil {
			break
		}
		parentID = parent.ParentID
	}
	if glyph.BBox == nil {
		return ""
	}
	center := glyph.BBox.Center()
	bestID := ""
	bestArea := math.Inf(1)
	for id, compartment := range compartments {
		if id == glyph.ID || compartment.BBox == nil || !pointInRect(center, *compartment.BBox) {
			continue
		}
		area := compartment.BBox.W * compartment.BBox.H
		if area < bestArea {
			bestID, bestArea = id, area
		}
	}
	return bestID
}

// polylineInsideRect reports whether every point of a polyline is in a rectangle.
// Parameters: points is the polyline; bbox is the containing rectangle.
func polylineInsideRect(points []rendersbgn.Point, bbox rendersbgn.BBox) bool {
	for _, point := range points {
		if !pointInRect(point, bbox) {
			return false
		}
	}
	return true
}

// checkUnitsOfInformation implements the objective overlap part of Section 4.3.5.
// Parameters: glyphs are parsed nodes; glyphByID resolves each unit's owner.
func checkUnitsOfInformation(glyphs []rendersbgn.Glyph) []Finding {
	var findings []Finding
	for _, unit := range glyphs {
		if unit.ClassName != "unit of information" || unit.BBox == nil {
			continue
		}
		for _, other := range glyphs {
			if other.BBox == nil || other.ID == unit.ID || other.ID == unit.ParentID {
				continue
			}
			if rectsInteriorOverlap(*unit.BBox, *other.BBox) {
				findings = append(findings, Finding{
					Rule: "4.3.5", Severity: SeverityWarning, Kind: "unit_of_information_overlap",
					Message:  fmt.Sprintf("unit of information %q overlaps or touches element %q", unit.ID, other.ID),
					Elements: []string{unit.ID, other.ID},
				})
			}
		}
	}
	return findings
}

// measureDrawing computes neutral metrics for underspecified Section 4.4 suggestions.
// Parameters: glyphs and arcs supply drawing bounds, lengths, and bend counts; metrics receives results.
func measureDrawing(glyphs []rendersbgn.Glyph, arcs []rendersbgn.ResolvedArc, metrics *Metrics) {
	minX, minY := math.Inf(1), math.Inf(1)
	maxX, maxY := math.Inf(-1), math.Inf(-1)
	for _, glyph := range glyphs {
		if glyph.BBox == nil {
			continue
		}
		minX = math.Min(minX, glyph.BBox.X)
		minY = math.Min(minY, glyph.BBox.Y)
		maxX = math.Max(maxX, glyph.BBox.X+glyph.BBox.W)
		maxY = math.Max(maxY, glyph.BBox.Y+glyph.BBox.H)
	}
	if !math.IsInf(minX, 0) {
		metrics.DrawingWidth = maxX - minX
		metrics.DrawingHeight = maxY - minY
	}
	for _, arc := range arcs {
		if len(arc.Points) > 2 {
			metrics.ArcBends += len(arc.Points) - 2
		}
		for index := 0; index+1 < len(arc.Points); index++ {
			metrics.TotalArcLength += math.Hypot(arc.Points[index+1].X-arc.Points[index].X, arc.Points[index+1].Y-arc.Points[index].Y)
		}
	}
}
