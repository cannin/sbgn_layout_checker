// Package rendersbgn contains the SBGN model and parsing/path helpers reused
// from render_sbgn's Go renderer.
//
// The implementation is adapted from:
// https://github.com/cannin/render_sbgn/tree/f2985994e867f7c94d46c52284b555f02ea3af76/go
package rendersbgn

// Point is a coordinate in the SBGN source coordinate space.
type Point struct {
	X float64 `json:"x"`
	Y float64 `json:"y"`
}

// BBox is an axis-aligned SBGN bounding box.
type BBox struct {
	X float64 `json:"x"`
	Y float64 `json:"y"`
	W float64 `json:"width"`
	H float64 `json:"height"`
}

// Label stores label text and its optional explicit layout box.
type Label struct {
	Text string `json:"text"`
	BBox *BBox  `json:"bbox,omitempty"`
}

// Port is a named connection point on a glyph.
type Port struct {
	ID string `json:"id"`
	Point
}

// Glyph is render_sbgn's flattened representation of an SBGN glyph.
type Glyph struct {
	ID             string `json:"id"`
	ParentID       string `json:"parent_id,omitempty"`
	CompartmentRef string `json:"compartment_ref,omitempty"`
	ClassName      string `json:"class"`
	BBox           *BBox  `json:"bbox,omitempty"`
	Label          Label  `json:"label"`
	Ports          []Port `json:"ports,omitempty"`
	Orientation    string `json:"orientation,omitempty"`
}

// ArcGlyph is an auxiliary glyph attached to an SBGN arc.
type ArcGlyph struct {
	ID        string `json:"id"`
	ClassName string `json:"class"`
	BBox      *BBox  `json:"bbox,omitempty"`
	Label     Label  `json:"label"`
}

// Arc stores an SBGN arc and its complete visible polyline.
type Arc struct {
	ID              string     `json:"id"`
	ClassName       string     `json:"class"`
	Source          string     `json:"source"`
	Target          string     `json:"target"`
	Points          []Point    `json:"points"`
	AuxiliaryGlyphs []ArcGlyph `json:"auxiliary_glyphs,omitempty"`
}

// Document is the normalized subset of SBGN-ML needed by the checker.
type Document struct {
	Language string  `json:"language"`
	Glyphs   []Glyph `json:"glyphs"`
	Arcs     []Arc   `json:"arcs"`
}

// ResolvedArc adds endpoint glyph IDs to an arc's rendered path.
type ResolvedArc struct {
	Arc
	SourceID string `json:"source_id"`
	TargetID string `json:"target_id"`
}

// Rect converts a bounding box to its left, top, right, and bottom edges.
func (bbox BBox) Rect() (float64, float64, float64, float64) {
	return bbox.X, bbox.Y, bbox.X + bbox.W, bbox.Y + bbox.H
}

// Center returns the center point of a bounding box.
func (bbox BBox) Center() Point {
	return Point{X: bbox.X + bbox.W/2.0, Y: bbox.Y + bbox.H/2.0}
}
