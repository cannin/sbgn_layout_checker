package rendersbgn

import (
	"encoding/xml"
	"errors"
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"
)

// xmlElement is the lightweight DOM representation used by render_sbgn.
type xmlElement struct {
	Name     string
	Attrs    map[string]string
	Children []*xmlElement
	Text     string
}

// ParseFile parses the SBGN-ML document at path.
// Parameters: path is an SBGN-ML file.
func ParseFile(path string) (Document, error) {
	file, err := os.Open(path)
	if err != nil {
		return Document{}, err
	}
	defer file.Close()

	root, err := parseXML(file)
	if err != nil {
		return Document{}, fmt.Errorf("parse %s: %w", path, err)
	}
	return parseSBGN(root)
}

// parseXML builds the same lightweight XML tree used by render_sbgn.
// Parameters: reader supplies XML tokens from an SBGN-ML document.
func parseXML(reader io.Reader) (*xmlElement, error) {
	decoder := xml.NewDecoder(reader)
	var root *xmlElement
	var stack []*xmlElement
	for {
		token, err := decoder.Token()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			return nil, err
		}
		switch typed := token.(type) {
		case xml.StartElement:
			node := &xmlElement{Name: typed.Name.Local, Attrs: map[string]string{}}
			for _, attr := range typed.Attr {
				node.Attrs[attr.Name.Local] = attr.Value
			}
			if len(stack) == 0 {
				root = node
			} else {
				parent := stack[len(stack)-1]
				parent.Children = append(parent.Children, node)
			}
			stack = append(stack, node)
		case xml.EndElement:
			if len(stack) == 0 {
				return nil, errors.New("unexpected XML end element")
			}
			stack = stack[:len(stack)-1]
		case xml.CharData:
			if len(stack) > 0 {
				stack[len(stack)-1].Text += string(typed)
			}
		}
	}
	if root == nil {
		return nil, errors.New("empty XML document")
	}
	return root, nil
}

// parseSBGN normalizes glyphs and arcs from the parsed XML tree.
// Parameters: root is the SBGN-ML document root.
func parseSBGN(root *xmlElement) (Document, error) {
	var mapNodes []*xmlElement
	collectDescendantsByName(root, "map", &mapNodes)
	if len(mapNodes) == 0 {
		return Document{}, errors.New("SBGN file missing map element")
	}

	document := Document{Language: elementAttr(mapNodes[0], "language")}
	for _, mapNode := range mapNodes {
		for _, node := range childElements(mapNode) {
			if node.Name == "glyph" {
				parseGlyphNode(node, "", &document.Glyphs)
			}
		}
	}
	var arcNodes []*xmlElement
	collectDescendantsByName(root, "arc", &arcNodes)
	for _, node := range arcNodes {
		arc, err := parseArcNode(node)
		if err != nil {
			return Document{}, err
		}
		document.Arcs = append(document.Arcs, arc)
	}
	return document, nil
}

// parseGlyphNode flattens one glyph subtree, preserving parent relationships.
// Parameters: node is the glyph element; parentID is its XML parent glyph;
// glyphs receives parsed records.
func parseGlyphNode(node *xmlElement, parentID string, glyphs *[]Glyph) {
	glyph := Glyph{
		ID:             elementAttr(node, "id"),
		ParentID:       parentID,
		CompartmentRef: elementAttr(node, "compartmentRef"),
		ClassName:      elementAttr(node, "class"),
		Orientation:    elementAttr(node, "orientation"),
	}
	for _, child := range childElements(node) {
		switch child.Name {
		case "label":
			glyph.Label = parseLabel(child)
		case "bbox":
			glyph.BBox = parseBBox(child)
		case "port":
			x, okX := parseFloat(elementAttr(child, "x"))
			y, okY := parseFloat(elementAttr(child, "y"))
			if okX && okY {
				glyph.Ports = append(glyph.Ports, Port{
					ID: elementAttr(child, "id"), Point: Point{X: x, Y: y},
				})
			}
		}
	}
	*glyphs = append(*glyphs, glyph)
	for _, child := range childElements(node) {
		if child.Name == "glyph" {
			parseGlyphNode(child, glyph.ID, glyphs)
		}
	}
}

// parseArcNode converts one arc element into a complete ordered polyline.
// Parameters: node is the arc XML element.
func parseArcNode(node *xmlElement) (Arc, error) {
	arc := Arc{
		ID:        elementAttr(node, "id"),
		ClassName: elementAttr(node, "class"),
		Source:    elementAttr(node, "source"),
		Target:    elementAttr(node, "target"),
	}
	var startNode *xmlElement
	var endNode *xmlElement
	var nextNodes []*xmlElement
	for _, child := range childElements(node) {
		switch child.Name {
		case "start":
			startNode = child
		case "next":
			nextNodes = append(nextNodes, child)
		case "end":
			endNode = child
		case "glyph":
			arc.AuxiliaryGlyphs = append(arc.AuxiliaryGlyphs, parseArcGlyphNode(child))
		}
	}
	if startNode == nil || endNode == nil {
		return Arc{}, fmt.Errorf("arc %q missing start or end", arc.ID)
	}
	for _, pointNode := range append(append([]*xmlElement{startNode}, nextNodes...), endNode) {
		x, okX := parseFloat(elementAttr(pointNode, "x"))
		y, okY := parseFloat(elementAttr(pointNode, "y"))
		if !okX || !okY {
			return Arc{}, fmt.Errorf("arc %q has invalid coordinates", arc.ID)
		}
		arc.Points = append(arc.Points, Point{X: x, Y: y})
	}
	return arc, nil
}

// parseArcGlyphNode parses an edge label or other arc auxiliary glyph.
// Parameters: node is a glyph nested directly in an arc.
func parseArcGlyphNode(node *xmlElement) ArcGlyph {
	glyph := ArcGlyph{ID: elementAttr(node, "id"), ClassName: elementAttr(node, "class")}
	for _, child := range childElements(node) {
		switch child.Name {
		case "bbox":
			glyph.BBox = parseBBox(child)
		case "label":
			glyph.Label = parseLabel(child)
		}
	}
	return glyph
}

// parseLabel parses label text and the optional label bounding box.
// Parameters: node is a label element.
func parseLabel(node *xmlElement) Label {
	label := Label{Text: strings.ReplaceAll(elementAttr(node, "text"), "\r", "")}
	for _, child := range childElements(node) {
		if child.Name == "bbox" {
			label.BBox = parseBBox(child)
			break
		}
	}
	return label
}

// parseBBox parses a bounding-box element.
// Parameters: node is the bbox XML element.
func parseBBox(node *xmlElement) *BBox {
	x, okX := parseFloat(elementAttr(node, "x"))
	y, okY := parseFloat(elementAttr(node, "y"))
	w, okW := parseFloat(elementAttr(node, "w"))
	h, okH := parseFloat(elementAttr(node, "h"))
	if !okX || !okY || !okW || !okH {
		return nil
	}
	return &BBox{X: x, Y: y, W: w, H: h}
}

// childElements returns direct child elements.
// Parameters: element is the parent node.
func childElements(element *xmlElement) []*xmlElement {
	return element.Children
}

// elementAttr returns an attribute or an empty string.
// Parameters: element is the XML node; name is the local attribute name.
func elementAttr(element *xmlElement, name string) string {
	if element == nil {
		return ""
	}
	return element.Attrs[name]
}

// collectDescendantsByName appends matching descendants in document order.
// Parameters: element is the search root; name is the local element name; out
// receives matches.
func collectDescendantsByName(element *xmlElement, name string, out *[]*xmlElement) {
	for _, child := range childElements(element) {
		if child.Name == name {
			*out = append(*out, child)
		}
		collectDescendantsByName(child, name, out)
	}
}

// parseFloat parses one required numeric attribute.
// Parameters: value is the attribute text.
func parseFloat(value string) (float64, bool) {
	if strings.TrimSpace(value) == "" {
		return 0, false
	}
	parsed, err := strconv.ParseFloat(value, 64)
	return parsed, err == nil
}
