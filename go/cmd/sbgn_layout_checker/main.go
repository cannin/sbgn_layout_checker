// Command sbgn_layout_checker checks SBGN-PD layout rules from Chapter 4.
package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/cannin/sbgn_layout_checker/go/checker"
)

const version = "0.1.0"

// main runs the CLI and reports operational errors on standard error.
func main() {
	if err := run(os.Args[1:]); err != nil {
		fmt.Fprintf(os.Stderr, "sbgn_layout_checker: %v\n", err)
		os.Exit(1)
	}
}

// run parses options, analyzes inputs, and writes the selected report format.
// Parameters: args excludes the executable name.
func run(args []string) error {
	flags := flag.NewFlagSet("sbgn_layout_checker", flag.ContinueOnError)
	format := flags.String("format", "markdown", "report format: markdown or json")
	output := flags.String("output", "", "output file (default: stdout)")
	flags.StringVar(output, "o", "", "output file (shorthand)")
	failOnError := flags.Bool("fail-on-error", false, "exit unsuccessfully when requirement errors are found")
	showVersion := flags.Bool("version", false, "print version and exit")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if *showVersion {
		fmt.Println(version)
		return nil
	}
	inputs := flags.Args()
	if len(inputs) == 0 {
		inputs = []string{defaultExamplePath()}
	}
	paths, err := checker.CollectFiles(inputs)
	if err != nil {
		return err
	}
	reports, err := checker.AnalyzeFiles(paths)
	if err != nil {
		return err
	}

	var contents []byte
	switch strings.ToLower(*format) {
	case "markdown", "md":
		contents = []byte(checker.MarkdownReport(reports, reproductionCommand(inputs, *format, *output)))
	case "json":
		contents, err = checker.JSONReport(reports)
		if err == nil {
			contents = append(contents, '\n')
		}
	default:
		return fmt.Errorf("unsupported format %q; use markdown or json", *format)
	}
	if err != nil {
		return err
	}
	if *output == "" || *output == "-" {
		_, err = os.Stdout.Write(contents)
	} else {
		if directory := filepath.Dir(*output); directory != "." {
			if err = os.MkdirAll(directory, 0o755); err != nil {
				return err
			}
		}
		err = os.WriteFile(*output, contents, 0o644)
	}
	if err != nil {
		return err
	}
	if *failOnError && hasErrors(reports) {
		return fmt.Errorf("layout requirement errors found")
	}
	return nil
}

// defaultExamplePath selects the shared examples from the root or go directory.
func defaultExamplePath() string {
	for _, candidate := range []string{"examples/sbgn_examples", "../examples/sbgn_examples"} {
		if info, err := os.Stat(candidate); err == nil && info.IsDir() {
			return candidate
		}
	}
	return "examples/sbgn_examples"
}

// reproductionCommand returns a shell-readable approximation of this invocation.
// Parameters: inputs, format, and output are the effective CLI arguments.
func reproductionCommand(inputs []string, format string, output string) string {
	parts := []string{"go", "run", "./go/cmd/sbgn_layout_checker", "--format", format}
	if output != "" {
		parts = append(parts, "--output", output)
	}
	parts = append(parts, inputs...)
	return strings.Join(parts, " ")
}

// hasErrors reports whether any file contains a mandatory-rule violation.
// Parameters: reports are completed analyses.
func hasErrors(reports []checker.FileReport) bool {
	for _, report := range reports {
		for _, finding := range report.Findings {
			if finding.Severity == checker.SeverityError {
				return true
			}
		}
	}
	return false
}
