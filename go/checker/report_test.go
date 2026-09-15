package checker

import (
	"strings"
	"testing"
)

func TestMarkdownReportIncludesTwoFileMetricComparison(t *testing.T) {
	reports := []FileReport{
		{
			Path: "before.sbgn",
			Metrics: Metrics{
				Glyphs:               10,
				Arcs:                 8,
				ResolvedArcs:         8,
				ArcCrossings:         3,
				ArcNodeCrossings:     2,
				TotalArcLength:       120.5,
				ArcBends:             6,
				MinimumCrossingAngle: 30,
				DrawingWidth:         400,
				DrawingHeight:        300,
			},
			Findings: []Finding{{Severity: SeverityError}, {Severity: SeverityWarning}},
		},
		{
			Path: "after.sbgn",
			Metrics: Metrics{
				Glyphs:               10,
				Arcs:                 8,
				ResolvedArcs:         8,
				ArcCrossings:         1,
				ArcNodeCrossings:     0,
				TotalArcLength:       100.25,
				ArcBends:             4,
				MinimumCrossingAngle: 75,
				DrawingWidth:         350,
				DrawingHeight:        310,
			},
		},
	}

	report := MarkdownReport(reports, "")
	for _, expected := range []string{
		"## Metric comparison",
		"Baseline: `before.sbgn`",
		"Candidate: `after.sbgn`",
		"| Requirement errors | 1 | 0 | -1 |",
		"| Arc crossings | 3 | 1 | -2 |",
		"| Total arc length | 120.50 | 100.25 | -20.25 |",
		"| Minimum crossing angle (degrees) | 30.00 | 75.00 | +45.00 |",
		"| Drawing height | 300.00 | 310.00 | +10.00 |",
	} {
		if !strings.Contains(report, expected) {
			t.Errorf("report does not contain %q", expected)
		}
	}
}

func TestMarkdownReportUsesNotAvailableForMissingCrossingAngle(t *testing.T) {
	reports := []FileReport{
		{Path: "before.sbgn", Metrics: Metrics{MinimumCrossingAngle: 45}},
		{Path: "after.sbgn"},
	}

	report := MarkdownReport(reports, "")
	expected := "| Minimum crossing angle (degrees) | 45.00 | n/a | n/a |"
	if !strings.Contains(report, expected) {
		t.Errorf("report does not contain %q", expected)
	}
}

func TestMarkdownReportOmitsComparisonForOtherFileCounts(t *testing.T) {
	for _, reports := range [][]FileReport{
		{{Path: "only.sbgn"}},
		{{Path: "one.sbgn"}, {Path: "two.sbgn"}, {Path: "three.sbgn"}},
	} {
		report := MarkdownReport(reports, "")
		if strings.Contains(report, "## Metric comparison") {
			t.Errorf("unexpected comparison for %d reports", len(reports))
		}
	}
}
