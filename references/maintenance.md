# Maintenance

## Existing files

Revise the current spec and render to a new stem. If the user edited the VSDX manually, first inspect it with invisible COM and compare IDs/text/geometry with the manifest. Preserve edits in the spec or patch a new VSDX directly. Save, close/reopen, and export PNG. The manifest checker requires matching IDs; rebuild metadata when shapes change. It does not cover arbitrary third-party VSDX without adaptation.

## Native mechanics

- Separate Visio.InvisibleApp instance; close only owned documents. Avoid EnsureDispatch and its generated COM wrapper cache.
- COM character positions are UTF-16 offsets; use Characters.CharProps(4, position), 1=super, 2=sub.
- Glue BeginX/EndX to shapes. Preserve Geometry row 0 when rebuilding native connector paths; subsequent rows are MoveTo/LineTo.
- Formula anchor follows node PinX/PinY; native text/rules follow anchor. Fraction/root rules are not flow connectors.
- Reopened TEXTHEIGHT/TEXTWIDTH plus geometric overlap checks are complementary: fitting text can still be covered by another label.
- Export saved layout before unsaved movement tests; discard test changes on close.

## Scope

Engine supports rectangles/diamonds/ellipses, explicit orthogonal routes, simple native math rows, containers and labels. It is not a general LaTeX engine or an automatic architecture extractor. Extend for demonstrated needs in a task copy first; update this personal skill when authorized.

Test changes with the three bundled examples in a task-owned directory, inspect PNGs and verify the changed behavior. Use a negative case for validator changes. Keep the accepted reference intact. Retain useful specs/reports; clean disposable outputs only within authorized scope.

After rendering all three bundled examples into one directory, run `scripts/check_engine.py OUTPUT_DIR`. It reopens each example, performs unsaved negative tests, writes `engine-test-report.json`, and creates `shape-check.vsdx/.png/.audit.json` for the additional diamond/ellipse test. Use a dedicated test directory. The report does not replace visual review.
