package checker

import (
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// CollectFiles expands files and directories into a sorted unique SBGN list.
// Parameters: inputs are file or directory paths.
func CollectFiles(inputs []string) ([]string, error) {
	files := map[string]bool{}
	for _, input := range inputs {
		info, err := os.Stat(input)
		if err != nil {
			return nil, err
		}
		if !info.IsDir() {
			if strings.EqualFold(filepath.Ext(input), ".sbgn") {
				files[filepath.Clean(input)] = true
			}
			continue
		}
		err = filepath.WalkDir(input, func(path string, entry fs.DirEntry, walkErr error) error {
			if walkErr != nil {
				return walkErr
			}
			if !entry.IsDir() && strings.EqualFold(filepath.Ext(path), ".sbgn") {
				files[filepath.Clean(path)] = true
			}
			return nil
		})
		if err != nil {
			return nil, err
		}
	}
	paths := make([]string, 0, len(files))
	for path := range files {
		paths = append(paths, path)
	}
	sort.Strings(paths)
	if len(paths) == 0 {
		return nil, fmt.Errorf("no .sbgn files found")
	}
	return paths, nil
}

// AnalyzeFiles checks every input path and returns reports in input order.
// Parameters: paths are concrete SBGN-ML files.
func AnalyzeFiles(paths []string) ([]FileReport, error) {
	reports := make([]FileReport, 0, len(paths))
	for _, path := range paths {
		report, err := AnalyzeFile(path)
		if err != nil {
			return nil, fmt.Errorf("analyze %s: %w", path, err)
		}
		reports = append(reports, report)
	}
	return reports, nil
}

// JSONReport serializes reports as indented JSON.
// Parameters: reports are completed file analyses.
func JSONReport(reports []FileReport) ([]byte, error) {
	return json.MarshalIndent(struct {
		Specification string       `json:"specification"`
		Reports       []FileReport `json:"reports"`
	}{
		Specification: "SBGN Process Description Level 1 Version 2.1, Chapter 4",
		Reports:       reports,
	}, "", "  ")
}

// MarkdownReport renders a human-readable report with rule-linked findings.
// Parameters: reports are completed file analyses; command reproduces the run.
func MarkdownReport(reports []FileReport, command string) string {
	totalErrors, totalWarnings := 0, 0
	var builder strings.Builder
	builder.WriteString("# SBGN layout checker report\n\n")
	builder.WriteString("Specification: SBGN Process Description Level 1 Version 2.1, Chapter 4.\n\n")
	for _, report := range reports {
		for _, finding := range report.Findings {
			if finding.Severity == SeverityError {
				totalErrors++
			} else {
				totalWarnings++
			}
		}
	}
	fmt.Fprintf(&builder, "Analyzed **%d SBGN files**: **%d requirement errors**, **%d recommendation warnings**.\n\n", len(reports), totalErrors, totalWarnings)
	builder.WriteString("| File | Glyphs | Arcs | Crossings | Arc-node crossings | Errors | Warnings |\n")
	builder.WriteString("|---|---:|---:|---:|---:|---:|---:|\n")
	for _, report := range reports {
		errors, warnings := findingCounts(report.Findings)
		fmt.Fprintf(&builder, "| `%s` | %d | %d | %d | %d | %d | %d |\n",
			report.Path, report.Metrics.Glyphs, report.Metrics.Arcs,
			report.Metrics.ArcCrossings, report.Metrics.ArcNodeCrossings,
			errors, warnings)
	}
	if len(reports) == 2 {
		writeMetricComparison(&builder, reports[0], reports[1])
	}
	for _, report := range reports {
		if len(report.Findings) == 0 {
			continue
		}
		fmt.Fprintf(&builder, "\n## %s\n\n", report.Path)
		for _, finding := range report.Findings {
			fmt.Fprintf(&builder, "- **%s %s** `%s`: %s\n", finding.Severity, finding.Rule, finding.Kind, finding.Message)
		}
	}
	builder.WriteString("\n## Coverage notes\n\n")
	builder.WriteString("See [`docs/chapter4_rules.md`](../docs/chapter4_rules.md) for exact coverage, assumptions, and underspecified rules.\n")
	if command != "" {
		fmt.Fprintf(&builder, "\nReproduce with `%s`.\n", command)
	}
	return builder.String()
}

// writeMetricComparison appends baseline-to-candidate deltas for two reports.
// Parameters: builder receives Markdown; baseline and candidate preserve input order.
func writeMetricComparison(builder *strings.Builder, baseline FileReport, candidate FileReport) {
	baselineErrors, baselineWarnings := findingCounts(baseline.Findings)
	candidateErrors, candidateWarnings := findingCounts(candidate.Findings)
	baselineMetrics := baseline.Metrics
	candidateMetrics := candidate.Metrics

	builder.WriteString("\n## Metric comparison\n\n")
	fmt.Fprintf(builder, "Baseline: `%s`  \nCandidate: `%s`\n\n", baseline.Path, candidate.Path)
	builder.WriteString("Delta is candidate minus baseline.\n\n")
	builder.WriteString("| Metric | Baseline | Candidate | Delta |\n")
	builder.WriteString("|---|---:|---:|---:|\n")
	writeIntegerComparisonRow(builder, "Requirement errors", baselineErrors, candidateErrors)
	writeIntegerComparisonRow(builder, "Recommendation warnings", baselineWarnings, candidateWarnings)
	writeIntegerComparisonRow(builder, "Glyphs", baselineMetrics.Glyphs, candidateMetrics.Glyphs)
	writeIntegerComparisonRow(builder, "Arcs", baselineMetrics.Arcs, candidateMetrics.Arcs)
	writeIntegerComparisonRow(builder, "Resolved arcs", baselineMetrics.ResolvedArcs, candidateMetrics.ResolvedArcs)
	writeIntegerComparisonRow(builder, "Arc crossings", baselineMetrics.ArcCrossings, candidateMetrics.ArcCrossings)
	writeIntegerComparisonRow(builder, "Arc-node crossings", baselineMetrics.ArcNodeCrossings, candidateMetrics.ArcNodeCrossings)
	writeFloatComparisonRow(builder, "Total arc length", baselineMetrics.TotalArcLength, candidateMetrics.TotalArcLength)
	writeIntegerComparisonRow(builder, "Arc bends", baselineMetrics.ArcBends, candidateMetrics.ArcBends)
	writeOptionalAngleComparisonRow(builder, baselineMetrics.MinimumCrossingAngle, candidateMetrics.MinimumCrossingAngle)
	writeFloatComparisonRow(builder, "Drawing width", baselineMetrics.DrawingWidth, candidateMetrics.DrawingWidth)
	writeFloatComparisonRow(builder, "Drawing height", baselineMetrics.DrawingHeight, candidateMetrics.DrawingHeight)
}

// writeIntegerComparisonRow appends one integer-valued metric row.
// Parameters: builder receives Markdown; label names the metric; values are ordered baseline then candidate.
func writeIntegerComparisonRow(builder *strings.Builder, label string, baseline int, candidate int) {
	fmt.Fprintf(builder, "| %s | %d | %d | %+d |\n", label, baseline, candidate, candidate-baseline)
}

// writeFloatComparisonRow appends one floating-point metric row.
// Parameters: builder receives Markdown; label names the metric; values are ordered baseline then candidate.
func writeFloatComparisonRow(builder *strings.Builder, label string, baseline float64, candidate float64) {
	fmt.Fprintf(builder, "| %s | %.2f | %.2f | %+.2f |\n", label, baseline, candidate, candidate-baseline)
}

// writeOptionalAngleComparisonRow appends crossing angles when both layouts have one.
// Parameters: builder receives Markdown; values are ordered baseline then candidate.
func writeOptionalAngleComparisonRow(builder *strings.Builder, baseline float64, candidate float64) {
	if baseline == 0 || candidate == 0 {
		builder.WriteString("| Minimum crossing angle (degrees) | ")
		if baseline == 0 {
			builder.WriteString("n/a")
		} else {
			fmt.Fprintf(builder, "%.2f", baseline)
		}
		builder.WriteString(" | ")
		if candidate == 0 {
			builder.WriteString("n/a")
		} else {
			fmt.Fprintf(builder, "%.2f", candidate)
		}
		builder.WriteString(" | n/a |\n")
		return
	}
	writeFloatComparisonRow(builder, "Minimum crossing angle (degrees)", baseline, candidate)
}

// findingCounts counts mandatory errors and recommendation warnings.
// Parameters: findings is one report's issue list.
func findingCounts(findings []Finding) (int, int) {
	errors, warnings := 0, 0
	for _, finding := range findings {
		if finding.Severity == SeverityError {
			errors++
		} else {
			warnings++
		}
	}
	return errors, warnings
}
