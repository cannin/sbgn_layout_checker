# Chapter 4 rule coverage

Source: `pd_level1_version2_1.pdf`, Chapter 4, "Layout Rules for a Process
Description" (printed pages 56-61; PDF pages 62-67).

The checker reports mandatory rules as errors and recommendations as warnings.
It uses source-coordinate bounding boxes, so findings involving rounded,
elliptical, or irregular glyphs are conservative.

| Section | Rule | Status |
|---|---|---|
| 4.2.1 | Nodes may not overlap or touch except allowed containment and meaningful complex-subunit contact. | Implemented with axis-aligned bounding boxes. |
| 4.2.2 | An edge crossing a node must be drawn above it. | Not derivable from standard SBGN-ML geometry. |
| 4.2.3 | Edges may not overlap node borders. | Implemented for positive-length collinear overlap. |
| 4.2.4 | Edges may not overlap or touch; self-crossing is forbidden; an edge may cross a node boundary at most twice and another edge at most once. | Implemented. Shared graph endpoints are exempt. |
| 4.2.5 | Nodes must be horizontal or vertical. | Explicit non-axis-aligned orientation values are rejected. |
| 4.2.6 | Consumption/production attach at centers of opposite process sides; modulation uses the other sides. | Implemented from ports or explicit arc endpoints. |
| 4.2.7 | A node label is partly inside its node and does not contact nodes or labels. | Implemented when an explicit label bbox exists. |
| 4.2.8 | An edge label does not contact nodes. | Implemented when an arc-label bbox exists. |
| 4.2.9 | Processes and arcs obey participant-compartment placement. | Implemented when participant compartments can be resolved. |
| 4.3.1 | Avoid node-edge crossings. | Implemented as warnings. |
| 4.3.2 | Labels are horizontal/non-empty; node labels are inside; edge labels are near their edge and avoid edges/labels. | Bounding-box overlap checks are implemented; orientation and proximity are not. |
| 4.3.3 | Minimize edge crossings. | Every proper crossing is reported as a warning. |
| 4.3.4 | Association/dissociation branch points are close to the process symbol. | Not enforced. |
| 4.3.5 | Units of information do not hide their node structure or overlap elements. | Overlap with other glyph boxes is implemented; hiding structure is not. |
| 4.4 | Crossing angle, compactness, length, bends, similarity, symmetry, proximity, direction, and compartment styling suggestions. | Length, bend, drawing-size, and crossing-angle metrics are emitted; no pass/fail threshold is imposed. |

## Underspecified rules

The following language lacks enough precision for interoperable automatic
pass/fail decisions. The checker deliberately does not invent conformance
thresholds for it.

- **4.2.1, meaningful touching:** the specification gives macromolecules in a
  complex as an example but does not exhaustively define which contacts have
  "specific meaning." The checker exempts touching entity-pool siblings with
  the same complex parent.
- **4.2.2, drawn on top:** SBGN-ML does not define a portable paint-order field,
  and visual export order is renderer-specific.
- **4.2.4, crossing identity:** the text does not define tolerance, whether a
  crossing at a bend is one event, or whether coincident graph endpoints count
  as touching. The checker uses a `1e-9` source-coordinate tolerance, deduplicates
  coincident crossings, and exempts a shared graph endpoint.
- **4.2.5, orientation:** many glyphs have no orientation attribute, and the
  chapter does not define how orientation is inferred for symmetric shapes.
- **4.2.6, attachment:** no coordinate tolerance is specified, and "process"
  is ambiguous for association/dissociation glyphs. The checker includes all
  process-node classes and uses the same `1e-9` tolerance.
- **4.2.7-4.2.8, label extent:** label bounding boxes are optional, while font,
  wrapping, and rotation differ by renderer. Checks requiring label geometry
  are skipped when a bbox is absent.
- **4.2.9, participants and compartments:** "participant" and "all edges/arcs"
  are not formally scoped for logical/modulatory chains, and ownership may be
  absent from SBGN-ML. The checker uses directly connected endpoints and resolves
  explicit `compartmentRef`, then XML nesting, then the smallest compartment
  containing the glyph center. A rule is skipped when ownership is unresolved.
- **4.3.1 and 4.3.3, avoid/minimize:** neither "unavoidable" nor a baseline for
  "minimized" is defined. The checker reports occurrences without declaring an
  optimum.
- **4.3.2, label quality:** "close to the edge" has no distance threshold, and
  horizontal orientation is normally absent from SBGN-ML.
- **4.3.4, branch proximity:** "comparable to, or smaller than" gives neither a
  precise branching-point construction nor a tolerance.
- **4.3.5, hide the structure:** visual obstruction has no quantitative test.
- **4.4, all suggestions:** "close to 90 degrees," "compact," "long," "few,"
  "similar," "symmetric," "related," "close together," and a consistent
  direction all require thresholds or semantic groupings not supplied by the
  specification. Compartment shading is optional and color carries no SBGN
  meaning.

## Reused `render_sbgn` behavior

`go/internal/rendersbgn` adapts the MIT-licensed Go model, streaming XML parser,
first-occurrence ID lookup, port-parent lookup, hidden-glyph classification,
and process-port endpoint resolution from `render_sbgn` commit
`f2985994e867f7c94d46c52284b555f02ea3af76`. Label bounding boxes and
`compartmentRef` are retained as checker-specific additions.
