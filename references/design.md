# Design defaults

- Generous white canvas; proportions follow graph depth/width, not a fixed three-band template.
- Default type: 宋体 node names 28 pt bold; Cambria Math formulas 25 pt with 宋体 CJK fallback; notes 22 pt; title 40 pt. These are Visio points, not screenshot pixels. Choose canvas/export scale for the presentation.
- Dark text #203641. Distinct stages may use green #16755F, blue #22659B, purple #68518A and pale fills. Name sections so color is not the only cue. Orange dashed routes can separate controls/weights from solid data paths when defined in the legend.
- Process boxes contain short action names. Put formulas, variable meanings and necessary parameters below; explain unfamiliar terms briefly, e.g. “转为 0～255 整数” when accurate.
- Prefer explicit arguments to compressed notation when helpful for the audience. Keep meaningful indices elsewhere. Replace code-only flags with the transformation or equivalent relation relevant to the explanation.
- Draw required intermediate operations separately. Distinguish scalar/weight routes from color/tensor data. Show original-input bypasses and reference inputs explicitly.
- Route arrows clear of notes/formulas. Center labels on route gaps. Junction dots mean real joins/branches; use bridges or reroute other crossings.
- Native root bars span full radicands. Native fraction parts and rules follow the node. Put parameters on a separate line when they disturb expression alignment.
- Increase space/canvas before reducing fonts. White label backgrounds must not cover neighboring annotations.

## Reference and examples

`assets/accepted-reference.vsdx` and `.png` retain the user's accepted 2026-11-12 diagram as style/editability references. Its low-light algorithm, machine setup, resolution, iteration count and step size are not skill defaults.

The three JSON examples are synthetic engine demonstrations, not claims about a real network or experiment.
