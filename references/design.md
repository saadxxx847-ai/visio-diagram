# Design defaults

- Generous white canvas; proportions follow graph depth/width, not a fixed three-band template.
- Default type: 宋体 node names 28 pt bold; Cambria Math formulas 25 pt with 宋体 CJK fallback; notes 22 pt; title 40 pt. These are Visio points, not screenshot pixels. Choose the page size for the presentation.
- Dark text #203641. Distinct stages may use green #16755F, blue #22659B, purple #68518A and pale fills. Name sections so color is not the only cue. Orange dashed routes can separate controls/weights from solid data paths when defined in the legend.
- Put a short, self-contained expression in the action box when it fits at the normal graph font size. Use compact function names for long, nested or multiline equations and place their full definitions below. Keep needed parameters near the operation.
- Prefer explicit arguments to compressed notation when helpful for the audience. Keep meaningful indices elsewhere. Replace code-only flags with the transformation or equivalent relation relevant to the explanation.
- Keep terms used only to evaluate one operation together in its complete formula. Give an intermediate result its own box when it feeds another operation or helps the reader follow a decision or a data path. Distinguish scalar/weight routes from color/tensor data. Show original-input bypasses and reference inputs explicitly.
- Route arrows clear of notes/formulas. Center labels on route gaps. Junction dots mean real joins/branches; use bridges or reroute other crossings.
- Use the structured `sqrt` part for a square root. It draws a native horizontal bar over the entire radicand and follows the node with its editable text. Use a second short row for a parameter when it improves legibility.
- Increase space/canvas before reducing fonts. White label backgrounds must not cover neighboring annotations.

## Paired algorithm diagrams

For algorithm diagrams and formula-driven workflows, deliver two editable VSDX files by default. Follow an explicit request for a single layout.

- **主流程版** (`_主流程版.vsdx`). Show the stages and essential data paths. Use concise operator names and symbols. Put short expressions in boxes where they read clearly, and use the same-page formulas layout below for full expressions.
- **逐框讲解版** (`_逐框讲解版.vsdx`). Give each operation a readable label in the user’s language. Put its complete formula directly below the corresponding box and briefly explain any symbol or condition the reader needs. For the visual pattern, see [the accepted editable reference](../assets/accepted-reference.vsdx).
- Use the same source version, inputs, outputs, formulas, and parameters in both files. Use matching stage names or translations, colors, and variable symbols so the reader can find the same step in either drawing. Verify the saved pair against the source and check formulas, branches, and connectors in each file.

## Same-page formulas

Use this layout when the user asks for English functions and symbols in the flow and a shared `Formulas` section. Start with [formulas-below.json](../assets/examples/formulas-below.json).

- Draw the complete flow in the upper area. Use short English operator names, variables and compact expressions in boxes. Use arrowheads at destinations and use operator circles such as `⊙` for pixelwise products or `+` for sums when they match the operation.
- Route shared inputs and bypasses explicitly. A small blank ellipse used as an edge endpoint makes a movable branch point. Use a bridge where independent routes cross and leave space for the arrowhead after each inline label.
- Reserve a single `Formulas` area beneath the flow. Put the long expressions there as editable `texts`, in flow order or under matching stage headings. Write each formula once. Use the same operator names, variables, subscripts and meanings in both places. Include units, scales and parameters where they are needed to interpret the formula.
- Widen the canvas or reflow the routes and formula columns before reducing the type. Review formula symbols, label gaps and the distinction between branches and crossings in the reopened VSDX.

## Reference and examples

`assets/accepted-reference.vsdx` and `.png` retain the user's accepted 2026-11-12 diagram as style/editability references. Its low-light algorithm, machine setup, resolution, iteration count and step size are not skill defaults.

The JSON examples demonstrate the renderer using synthetic inputs.
