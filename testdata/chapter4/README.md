# Chapter 4 negative layout fixtures

This directory contains 44 small SBGN-PD Level 1 Version 2.1 documents: two
variants for each numbered guideline in Sections 4.2 and 4.3, plus two for each
of the eight suggestions in Section 4.4. Labels are intentionally simple
(`A`, `B`, and `C`).

Every `.sbgn` document passes the semantic `sbgn-validator`. They intentionally
exercise bad layout geometry, not bad SBGN grammar. `cases.json` maps each file
to its target guideline and, where the rule is machine-checkable, the expected
Go finding kind.

Three guidelines cannot be represented as a portable SBGN-ML violation:
paint order (4.2.2), arbitrary glyph rotation (4.2.5), and compartment shading
(4.4). Their files are valid representation probes and their intended visual
violation is recorded by the filename/manifest. Other qualitative Section 4.4
fixtures exercise the relevant metric without asserting a universal failure
threshold.

Regenerate and validate the suite from the repository root:

```bash
python3 scripts/generate_chapter4_fixtures.py
./scripts/validate-fixtures.sh
```
