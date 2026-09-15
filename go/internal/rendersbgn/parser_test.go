package rendersbgn

import (
	"os"
	"path/filepath"
	"testing"
)

// TestParseFileRetainsCheckerGeometry verifies fields added around reused parsing code.
func TestParseFileRetainsCheckerGeometry(t *testing.T) {
	t.Parallel()
	path := filepath.Join(t.TempDir(), "test.sbgn")
	contents := `<?xml version="1.0"?>
<sbgn xmlns="http://sbgn.org/libsbgn/0.3">
  <map language="process description">
    <glyph id="comp" class="compartment"><bbox x="0" y="0" w="100" h="100"/></glyph>
    <glyph id="node" class="macromolecule" compartmentRef="comp">
      <label text="A"><bbox x="11" y="12" w="8" h="4"/></label>
      <bbox x="10" y="10" w="20" h="10"/>
    </glyph>
    <glyph id="process" class="process"><bbox x="50" y="10" w="10" h="10"/><port id="p1" x="45" y="15"/><port id="p2" x="65" y="15"/></glyph>
    <arc id="a1" class="consumption" source="node" target="p1"><start x="30" y="15"/><end x="45" y="15"/></arc>
  </map>
</sbgn>`
	if err := os.WriteFile(path, []byte(contents), 0o600); err != nil {
		t.Fatal(err)
	}
	document, err := ParseFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if document.Language != "process description" || len(document.Glyphs) != 3 || len(document.Arcs) != 1 {
		t.Fatalf("unexpected parsed document: %+v", document)
	}
	if document.Glyphs[1].CompartmentRef != "comp" || document.Glyphs[1].Label.BBox == nil {
		t.Fatalf("checker geometry was not retained: %+v", document.Glyphs[1])
	}
	resolved := ResolveArcs(document.Arcs, document.Glyphs)
	if len(resolved) != 1 || resolved[0].TargetID != "process" || resolved[0].Points[1] != (Point{X: 45, Y: 15}) {
		t.Fatalf("unexpected resolved arc: %+v", resolved)
	}
}
