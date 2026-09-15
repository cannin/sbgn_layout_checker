package rendersbgn

// BuildLookups returns first-occurrence glyph and port-parent lookups, matching
// render_sbgn's duplicate-ID behavior.
// Parameters: glyphs is the flattened parsed glyph list.
func BuildLookups(glyphs []Glyph) (map[string]*Glyph, map[string]string) {
	glyphByID := map[string]*Glyph{}
	portParentByID := map[string]string{}
	for index := range glyphs {
		glyph := &glyphs[index]
		if glyph.ID == "" {
			continue
		}
		if _, exists := glyphByID[glyph.ID]; exists {
			continue
		}
		glyphByID[glyph.ID] = glyph
		for _, port := range glyph.Ports {
			if port.ID != "" {
				portParentByID[port.ID] = glyph.ID
			}
		}
	}
	return glyphByID, portParentByID
}

// ResolveArcs preserves explicit start/next/end points and resolves endpoint
// ports to their owning glyphs using render_sbgn's topology rules.
// Parameters: arcs and glyphs are parsed from the same SBGN document.
func ResolveArcs(arcs []Arc, glyphs []Glyph) []ResolvedArc {
	glyphByID, portParentByID := BuildLookups(glyphs)
	resolved := make([]ResolvedArc, 0, len(arcs))
	for _, arc := range arcs {
		sourceID := endpointGlyphID(arc.Source, portParentByID)
		targetID := endpointGlyphID(arc.Target, portParentByID)
		sourceGlyph := glyphByID[sourceID]
		targetGlyph := glyphByID[targetID]
		if sourceGlyph == nil || targetGlyph == nil || sourceGlyph.BBox == nil || targetGlyph.BBox == nil || len(arc.Points) < 2 {
			continue
		}
		if IsHiddenGlyphClass(sourceGlyph.ClassName) || IsHiddenGlyphClass(targetGlyph.ClassName) {
			continue
		}
		points := append([]Point(nil), arc.Points...)
		for index, reference := range []string{arc.Source, arc.Target} {
			glyph := sourceGlyph
			pointIndex := 0
			if index == 1 {
				glyph = targetGlyph
				pointIndex = len(points) - 1
			}
			if _, isPort := portParentByID[reference]; isPort && IsPortedGlyphClass(glyph.ClassName) {
				if port, ok := findPort(glyph, reference); ok {
					points[pointIndex] = port.Point
				}
			}
		}
		arc.Points = points
		resolved = append(resolved, ResolvedArc{Arc: arc, SourceID: sourceID, TargetID: targetID})
	}
	return resolved
}

// IsHiddenGlyphClass reports classes rendered as part of another glyph.
// Parameters: className is an SBGN glyph class.
func IsHiddenGlyphClass(className string) bool {
	return className == "unit of information" || className == "state variable" || className == "terminal"
}

// IsPortedGlyphClass reports classes whose visible line extends to explicit ports.
// Parameters: className is an SBGN glyph class.
func IsPortedGlyphClass(className string) bool {
	switch className {
	case "process", "omitted process", "uncertain process", "association", "dissociation", "and", "or", "not":
		return true
	default:
		return false
	}
}

// endpointGlyphID maps a port reference to its owning glyph.
// Parameters: reference is an arc endpoint; portParentByID maps ports to glyphs.
func endpointGlyphID(reference string, portParentByID map[string]string) string {
	if parentID, ok := portParentByID[reference]; ok {
		return parentID
	}
	return reference
}

// findPort returns a named glyph port.
// Parameters: glyph owns the searched port; id is the port identifier.
func findPort(glyph *Glyph, id string) (Port, bool) {
	for _, port := range glyph.Ports {
		if port.ID == id {
			return port, true
		}
	}
	return Port{}, false
}
