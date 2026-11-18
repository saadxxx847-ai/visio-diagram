---
name: visio-diagram
description: 在 Windows 用 Visio COM 创建或修订原生可编辑的流程图、算法/网络结构图和系统架构图，交付可编辑 VSDX；需要公式排版、分支汇合及吸附连线时使用。
---

# Visio diagram

Deliver the native editable VSDX with glued one-dimensional connectors. Run Windows Python with Visio COM in the background. The user prefers this workflow without Computer Use.

## Workflow

1. **Establish content.** Read applicable project instructions and recent work records. Identify audience, diagram type, inputs/outputs, branches, merges and authoritative source/version. For code-backed diagrams, reconcile code and run records before drawing; retain evidence in the project. Old diagrams are references. Ask only about missing facts that materially change the graph.
2. **Plan layout.** Use one box per meaningful operation at the audience’s level. Keep terms used only within that operation in its full formula. For algorithm and formula-driven workflows, follow the [paired diagram layouts](references/design.md#paired-algorithm-diagrams). For networks and systems, keep the level of detail consistent across modules. Consult `assets/accepted-reference.png` when visual guidance is useful; its algorithm and dimensions are not defaults.
3. **Author a spec.** Read [references/spec.md](references/spec.md). Save a task-owned JSON spec describing content and explicit layout. Adapt the nearest example in `assets/examples/`: `branch-fusion.json`, `skip-network.json`, or `layered-system.json`. Reuse the renderer. Expand the page and reroute before shrinking type.
4. **Render.** Find an existing Windows Python with `pywin32`; run `scripts/render.py probe`. Run `scripts/render.py render SPEC --output NEW_NAME.vsdx`. Use a new revision name unless replacing is authorized. Resolve errors in `.audit.json`. For an unsupported formula/layout, extend a task-local copy of the engine and verify native editability.
5. **Verify.** The script reopens the saved VSDX and checks text, formula placement, radical bars, glue and movement. Review the saved layout and the notation around branches, merges and crowded routes. Fix the spec and repeat affected checks. `scripts/render.py verify FILE.vsdx --manifest FILE.manifest.json` checks an existing generated file; rerender after spec changes.
6. **Deliver.** Link both VSDX files for paired diagrams, or the requested VSDX for a single layout. Mention material limitations. Update the work record when required. Preserve spec/audit for revisions. Under cleanup authorization, remove only identified task-owned temporary crops/copies after checking final files; retain reusable scripts, sources and final artifacts.

## Revisions

- When asked to wait, collect feedback; apply it together once revision is authorized.
- Edit the spec for this engine's diagrams. If the user manually edited a VSDX, inspect it first: an older spec may be stale. Preserve their changes. See [references/maintenance.md](references/maintenance.md) for direct COM edits and limitations.
- Use mathematically faithful, audience-appropriate notation. Explain equivalences and zero/threshold conditions where relevant. A confusing use of a symbol does not justify removing that symbol everywhere.
- Style defaults yield to task-specific fonts, orientation, palette and detail.
- The skill supplies no remote host, experiment parameters, credentials or authority to rerun experiments. Source checks follow the current project.

## Completion

The VSDX reopens; objects are native; flow connectors are glued at both ends; formulas appear in the selected location and match the graph notation; radical bars span their operands, and audit errors are resolved. State whether evidence is current or a dated snapshot when this distinction matters.
