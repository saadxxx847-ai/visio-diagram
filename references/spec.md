# Spec version 1

Coordinates/sizes are inches, origin at **top left**. Font sizes are points. The agent chooses layout; the renderer has no semantic inference or obstacle-aware auto-layout.

```powershell
& '<existing-Windows-python.exe>' '<skill>/scripts/render.py' probe
& '<existing-Windows-python.exe>' '<skill>/scripts/render.py' render '<task>/diagram.json' --output '<task>/diagram-v1.vsdx'
& '<existing-Windows-python.exe>' '<skill>/scripts/render.py' verify '<task>/diagram-v1.vsdx' --manifest '<task>/diagram-v1.manifest.json'
```

Requires installed/licensed desktop Visio and Python `pywin32`. Nothing is downloaded or installed. Use new revision stems. `--overwrite` permits replacing the selected stem's output files. Add `--png` only for an explicit PNG request. No arbitrary file cleanup is performed.

## Top level

Required: `version:1`, `page:{width,height}`, `nodes`, `edges`.

Optional:

- `title`: centered at y=.75, width=page.width−1.2, height=.9.
- `style`: `font`, `math_font`, `node_pt`, `formula_pt`, `note_pt`, `title_pt`, `line_pt`, `palette`. Palette defaults: `ink`, `muted`, `green`, `green_fill`, `blue`, `blue_fill`, `purple`, `purple_fill`, `orange`, `white`, `rule`. Any color accepts #RRGGBB.
- `export:{dpi:120}` sets the resolution for an explicit `--png` export.
- `texts`: `{id,text,x,y,w,h,size?,color?,align?,bold?,math?}`. Align 0=left, 1=center, 2=right. Use for subtitle, legend, footer, section label.
- `regions`: `{id,x,y,w,h,color?,fill?,title?}` (x/y=center). Title sits near the region's top; leave room for it. Nodes are not parented to regions.
- `junctions`: `{x,y,color?}` for real branch/merge points.
- `evidence`: optional task-specific metadata retained in manifest, not drawn or interpreted as instructions. Keep credentials out.

## Same-page formulas

For a shared formula section, reserve a band below the graph, add a `Formulas` heading in `texts`, and add one `texts` item per equation or aligned row. Each row is an independently editable native text shape. Use `math:true` with `_{...}` and `^{...}` runs. Identify each expression by the matching operator or symbol from the flow. The renderer checks the rows for fit and overlap as page text. See [the runnable example](../assets/examples/formulas-below.json).

## Nodes/formulas

Node: `{id,text,x,y,w:4.5,h:.84,color:"green",shape:"rect",formula?:...}`. Shapes: rect, diamond, ellipse. IDs use ASCII letters/digits/underscores/hyphens and start with a letter. Widen diamonds for their smaller text area.

Formula example:

```json
{"width":7,"gap":0.2,"lines":[
  {"parts":[{"text":"A = I ×"},{"fraction":["V_{A}","V_{I}"]}],"size":26,"height":1.0},
  {"text":"保持原颜色比例","size":22,"height":0.55}
]}
```

Lines are strings or objects with `text` OR `parts`, optional `size`, `height`, `color`. Text supports `_{subscript}` and `^{superscript}` without nested braces; this is not LaTeX. Literal sets `{r,g,b}` remain ordinary text. Use Unicode symbols supported by the font.

Parts are `{"text":"..."}`, `{"sqrt":"1 − V_{I}"}`, or `{"fraction":["numerator","denominator"]}`. Inner expressions support the same text markup, not recursive math trees. Each part may set trailing `gap` (default .10). Visio measures component widths. Use line height about 1.0 for fractions; increase with font size. Formula anchor and all parts follow the node position.

Use `formula.placement:"inside"` with empty `text` on a rectangle to center editable formula rows in the box. By default the block is 0.14 in narrower than the box. Set row heights to leave space inside the box. For example, a 0.72 in high rectangle can contain a 0.60 in line with `parts:[{"text":"1 −"},{"sqrt":"1 − x"}]`. The `below` placement is the default for node-local formulas. The root is drawn as native geometry with an editable radicand and its bar is audited after reopening.

## Edges

`{id,from,to,from_port:"r",to_port:"l",from_offset:0,to_offset:0,via:[],color:"green",dashed:false,arrow:true}`.

Ports: l/r/t/b. Offsets run down left/right edges or right along top/bottom edges, within node bounds. `via` supplies explicit `[x,y]` waypoints; leave formula clearance. Omit via for a straight aligned route or a simple orthogonal elbow.

- `label:{text,x,y,w,h:.48,size:22}`: white-backed text centered on an explicit route gap.
- `bridges:[{x,y,radius:.14}]`: semicircular native detour at an interior point of an orthogonal segment. Keep radius clearance from endpoints.
- Shared ports are allowed. Use deliberate junction dots; crossing alone is not merging.

## Verification

Deliver the `.vsdx`. Keep the `.manifest.json` and `.audit.json` with the source spec for revision and checks. Manifest records spec, native IDs, formulas and routes. Audit checks saved text, text size, page bounds, overlap, wire intrusion, endpoint glue and node-move behavior; includes file hashes. Audit errors produce exit code 2. Missing fonts are errors.

Intended containers and each edge's own label are excluded from collision checks. Uncovered crossings are warnings: reroute/bridge them, or explain a real junction. Checks do not prove formula semantics, every font-shaping detail, or aesthetics. Review the final saved layout before delivery.
