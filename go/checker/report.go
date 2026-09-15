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
