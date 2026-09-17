package main

import (
	"bytes"
	"io"
	"os"
	"testing"
)

func TestVersionMatchesRelease(t *testing.T) {
	if version != "0.1.1" {
		t.Fatalf("version = %q, want 0.1.1", version)
	}
}

func TestVersionFlag(t *testing.T) {
	original := os.Stdout
	reader, writer, err := os.Pipe()
	if err != nil {
		t.Fatal(err)
	}
	os.Stdout = writer
	t.Cleanup(func() { os.Stdout = original })

	if err := run([]string{"--version"}); err != nil {
		t.Fatal(err)
	}
	if err := writer.Close(); err != nil {
		t.Fatal(err)
	}
	var output bytes.Buffer
	if _, err := io.Copy(&output, reader); err != nil {
		t.Fatal(err)
	}
	if output.String() != "0.1.1\n" {
		t.Fatalf("output = %q, want 0.1.1\\n", output.String())
	}
}
