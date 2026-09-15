package checker

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/cannin/sbgn_layout_checker/go/internal/rendersbgn"
)

// TestSegmentIntersection verifies proper crossings and endpoint touches remain distinct.
func TestSegmentIntersection(t *testing.T) {
	t.Parallel()
	proper, point := segmentIntersection(
		rendersbgn.Point{X: 0, Y: 5}, rendersbgn.Point{X: 10, Y: 5},
		rendersbgn.Point{X: 5, Y: 0}, rendersbgn.Point{X: 5, Y: 10},
	)
	if proper != intersectionProper || point == nil || !pointEqual(*point, rendersbgn.Point{X: 5, Y: 5}) {
		t.Fatalf("expected proper crossing at (5,5), got kind=%v point=%v", proper, point)
	}

	touch, _ := segmentIntersection(
		rendersbgn.Point{X: 0, Y: 0}, rendersbgn.Point{X: 5, Y: 5},
		rendersbgn.Point{X: 5, Y: 5}, rendersbgn.Point{X: 10, Y: 0},
	)
	if touch != intersectionTouch {
		t.Fatalf("expected endpoint touch, got %v", touch)
	}
}

// TestChapter4Fixtures checks both variants of every documented guideline.
func TestChapter4Fixtures(t *testing.T) {
	t.Parallel()
	type fixtureCase struct {
		Path         string `json:"path"`
		Section      string `json:"section"`
		ExpectedKind string `json:"expected_kind"`
	}
	fixtureDirectory := filepath.Join("..", "..", "testdata", "chapter4")
	manifestBytes, err := os.ReadFile(filepath.Join(fixtureDirectory, "cases.json"))
	if err != nil {
		t.Fatal(err)
	}
	var cases []fixtureCase
	if err := json.Unmarshal(manifestBytes, &cases); err != nil {
		t.Fatal(err)
	}
	if len(cases) != 44 {
		t.Fatalf("expected 44 fixtures, got %d", len(cases))
	}
	sectionCounts := map[string]int{}
	for _, fixture := range cases {
		fixture := fixture
		t.Run(fixture.Path, func(t *testing.T) {
			report, err := AnalyzeFile(filepath.Join(fixtureDirectory, fixture.Path))
			if err != nil {
				t.Fatal(err)
			}
			if fixture.ExpectedKind != "" && !hasFindingKind(report.Findings, fixture.ExpectedKind) {
				t.Fatalf("expected %s finding for %s; got %+v", fixture.ExpectedKind, fixture.Section, report.Findings)
			}
		})
		sectionCounts[fixture.Section]++
	}
	for section, count := range sectionCounts {
		if count != 2 {
			t.Errorf("section %s has %d fixtures, expected 2", section, count)
		}
	}
}

// hasFindingKind reports whether a finding list contains a kind.
func hasFindingKind(findings []Finding, kind string) bool {
	for _, finding := range findings {
		if finding.Kind == kind {
			return true
		}
	}
	return false
}

// TestAnalyzeDocument finds representative mandatory and recommended issues.
func TestAnalyzeDocument(t *testing.T) {
	t.Parallel()
	document := rendersbgn.Document{
		Language: "process description",
		Glyphs: []rendersbgn.Glyph{
			{ID: "a", ClassName: "macromolecule", BBox: &rendersbgn.BBox{X: 0, Y: 0, W: 10, H: 10}},
			{ID: "b", ClassName: "macromolecule", BBox: &rendersbgn.BBox{X: 9, Y: 9, W: 10, H: 10}},
			{ID: "c", ClassName: "macromolecule", BBox: &rendersbgn.BBox{X: 30, Y: 0, W: 10, H: 10}},
			{ID: "d", ClassName: "macromolecule", BBox: &rendersbgn.BBox{X: 30, Y: 20, W: 10, H: 10}},
		},
		Arcs: []rendersbgn.Arc{
			{ID: "vertical", ClassName: "production", Source: "c", Target: "d", Points: []rendersbgn.Point{{X: 35, Y: 5}, {X: 35, Y: 25}}},
			{ID: "horizontal", ClassName: "production", Source: "a", Target: "b", Points: []rendersbgn.Point{{X: 20, Y: 15}, {X: 45, Y: 15}}},
		},
	}
	report := AnalyzeDocument(document)
	if !hasFinding(report.Findings, "4.2.1", "node_overlap") {
		t.Fatal("expected node-overlap requirement finding")
	}
	if !hasFinding(report.Findings, "4.3.3", "edge_crossing") {
		t.Fatal("expected edge-crossing recommendation finding")
	}
}

// TestExampleCrossingCount preserves parity with the original Python checker.
func TestExampleCrossingCount(t *testing.T) {
	paths, err := CollectFiles([]string{filepath.Join("..", "..", "examples", "sbgn_examples")})
	if err != nil {
		t.Fatal(err)
	}
	reports, err := AnalyzeFiles(paths)
	if err != nil {
		t.Fatal(err)
	}
	totalArcs, totalCrossings := 0, 0
	for _, report := range reports {
		totalArcs += report.Metrics.Arcs
		totalCrossings += report.Metrics.ArcCrossings
	}
	if len(reports) != 12 || totalArcs != 557 || totalCrossings != 37 {
		t.Fatalf("unexpected fixture totals: files=%d arcs=%d crossings=%d", len(reports), totalArcs, totalCrossings)
	}
}

// TestAnalyzeFileRejectsOtherLanguages keeps the checker scoped to SBGN-PD.
func TestAnalyzeFileRejectsOtherLanguages(t *testing.T) {
	t.Parallel()
	path := filepath.Join(t.TempDir(), "activity-flow.sbgn")
	contents := `<?xml version="1.0"?><sbgn xmlns="http://sbgn.org/libsbgn/0.3"><map id="m" language="activity flow"><glyph id="a" class="biological activity"><bbox x="0" y="0" w="10" h="10"/></glyph></map></sbgn>`
	if err := os.WriteFile(path, []byte(contents), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := AnalyzeFile(path); err == nil {
		t.Fatal("expected a non-PD map error")
	}
}

// hasFinding reports whether a finding list contains a rule/kind pair.
func hasFinding(findings []Finding, rule string, kind string) bool {
	for _, finding := range findings {
		if finding.Rule == rule && finding.Kind == kind {
			return true
		}
	}
	return false
}
