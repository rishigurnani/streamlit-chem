---
author: rgurnani96
created: 2026-08-09
---

# ChemLit — technical design

## Summary

How ChemLit is built on top of Streamlit without forking the rendering pipeline or
duplicating RDKit logic. The core idea: one shared `mol_utils` module owns all RDKit
interop, and each chemical feature is a thin layer over it (a display element, a
`column_config` type, a cache serializer, or a composition of existing widgets). This
document specifies the proto/backend/frontend split, the caching integration, and the
async model, and records the alternatives we rejected.

## Problem

RDKit `Mol` objects are C++-backed, expensive to compute over, and unsafe to pickle
across Streamlit sessions. A naive "one widget per feature" fork would (a) copy the
RDKit drawing/matching code into every element (churn + shotgun surgery), (b) add a
parallel data grid and a parallel cache, and (c) block the event loop on heavy work.
We need an architecture where new chemical features cost a proto + a thin viewer, and
where molecules flow through caching and state safely.

## Proposal

### Layering

```
                ┌─────────────────────────────────────────────┐
                │ elements/lib/mol_utils.py  (THE Mol-core)    │
                │  to_mol · to_query · get_substructure_match  │
                │  mol_to_svg                                  │
                └───────────────▲──────────────▲───────────────┘
                                │              │
     ┌──────────────────────────┘              └──────────────────────────┐
     │                                                                     │
 elements/molecule.py        column_config MoleculeColumn      cache serializer (Mol⇄bytes)
 (st.molecule, shipped)      (st.chem_dataframe, Phase 2)      (@st.cache_data, Phase 2)
     │                                                                     │
 compositions: st.smarts_input, st.mol_card (Phase 3) · st.chem_draw, st.mol_viewer (Phase 4)
                                     │
                          SAR: st.chem_space, r_group_decomposition (Phase 5)
```

**Separation of concerns / no shotgun surgery:** RDKit is imported for
drawing/matching in exactly one module (`mol_utils`). Elements never call RDKit
drawing APIs directly. A change to how we render (e.g. dark-mode aware canvas, atom
indices, stereo annotations) is a one-file change that every element inherits.

### Phase 1 — `st.molecule` (this PR)

**Proto** (`proto/streamlit/proto/Molecule.proto`), added to `Element.proto` as
`Molecule molecule = 67`:

```proto
message Molecule {
  string svg = 1;      // RDKit-rendered, self-contained 2D SVG
  string caption = 2;  // optional label beneath the structure
}
```

Rationale: rendering happens in Python (RDKit lives server-side), so the proto
carries a finished SVG and the frontend stays a thin, dependency-free viewer. This
mirrors how other server-rendered visuals are delivered and keeps the frontend
bundle free of an RDKit-JS dependency for the basic 2D case.

**Backend** (`elements/molecule.py`): `MoleculeMixin.molecule(...)` coerces input via
`mol_utils.to_mol`, computes highlights via `mol_utils.get_substructure_match`, renders
via `mol_utils.mol_to_svg`, and enqueues with the standard `create_layout_config`. An
integer `width`/`height` is forwarded to the RDKit canvas so a pinned pixel size is
honored at draw time; `"content"`/`"stretch"` fall back to a balanced default canvas
and are handled as layout on the frontend.

**Frontend** (`components/elements/Molecule/Molecule.tsx`): sanitizes the SVG with
DOMPurify (`USE_PROFILES: { svg, svgFilters }`) and renders it via
`dangerouslySetInnerHTML` inside a `<figure>`, with an optional `<figcaption>`.
Registered in `ElementNodeRenderer` as `case "molecule"`. This reuses the exact
sanitize-then-render pattern established by `st.html`'s `SanitizedHtml`.

### Phase 2 — the two big generalizations

**`MoleculeColumn` (`st.chem_dataframe`).** Add a column type to
`column_config_utils` whose cell renderer calls `mol_utils.mol_to_svg` on each row's
`Mol` (or SMILES). The existing dataframe already provides row selection, column
search, and mini-charts, so `st.chem_dataframe(df, mol_column=...)` becomes sugar
that injects a `MoleculeColumn` into `column_config` and returns the standard
dataframe selection state. SMARTS column search maps onto the existing column filter
using `mol_utils.get_substructure_match`. **No new data grid.**

**`Mol` cache serialization (`st.cache_mol`).** Register a type serializer in the
caching layer keyed on `rdkit.Chem.Mol`:

- serialize: `mol.ToBinary()` → `bytes`
- deserialize: `Chem.Mol(data)`
- hash (for `hashing.py`): hash the binary form, so two structurally identical mols
  cache-hit.

This makes `@st.cache_data` safe for molecules with no user-visible change.
`st.cache_mol` is at most a thin discoverable alias to `cache_data` with this
serializer guaranteed on — **not** a second caching implementation.

### Phase 3–5 (summarized; specced in detail when scheduled)

- **`st.smarts_input`** = `st.text_input` + `mol_utils.to_query` validation state +
  an inline `st.molecule` preview highlighting the match.
- **`st.mol_card`** = a bordered container composing `st.molecule` with `st.metric`
  and RO5/Lipinski badges computed from `rdkit.Chem.Descriptors` (a small
  `descriptor_utils` helper, still no RDKit drawing outside `mol_utils`).
- **`st.chem_draw`** = a Ketcher-based editor. Adopt
  [`streamlit-ketcher`](https://github.com/streamlit/streamlit-ketcher) rather than
  reimplementing the editor; convert its molfile/SMILES output to a `Mol` via the
  Mol-core so it round-trips like every other element.
- **`st.mol_viewer`** = a 3Dmol.js/WebGL viewer widget returning click events; 2D
  fallback reuses `mol_to_svg`. Isolated inside `st.fragment` so rotating/switching
  conformers does not rerun descriptor computation.
- **`st.chem_space`** = fingerprints (Morgan/RDKit via Mol-core) → UMAP/t-SNE →
  existing scatter selection events; lasso selection is returned as selected indices
  that downstream `st.chem_dataframe`/`st.mol_card` consume.
- **Cross-widget highlight binding** = a shared "active substructure" value in
  session state; each element passes it to `mol_utils.get_substructure_match` at
  render. No element reaches into another — they all read one piece of state.

### Async model (`st.async_progress`)

Heavy operations run in a background worker; the UI polls progress and updates a
native `st.progress`/`st.status` inside an `st.fragment` so only that zone reruns.
This generalizes existing background-work + status primitives rather than adding a
bespoke threading API. "Partial rerun zones for molecules" is `st.fragment` and needs
docs, not new code.

## Dependencies

- **`rdkit`** becomes a hard runtime dependency of `lib/` (see `lib/pyproject.toml`).
  RDKit uses calendar-based versioning (`YYYY.MM`) where a major bump is a scheduled
  release, not a break, so the upper bound is intentionally uncapped (same rationale
  as `packaging`). Lower bound `2023.3` is the first release exposing the
  `rdMolDraw2D` highlight-drawing API.
- Phases 4–5 add frontend viewers (Ketcher via `streamlit-ketcher`; 3Dmol.js),
  declared only when those phases land.

## Testing

- **Python unit:** `mol_utils_test.py` (parse/match/render happy paths + invalid
  SMILES/SMARTS + no-match) and `molecule_test.py` (proto marshalling, caption,
  highlight changes output, no-match no-op, width/height config, canvas pinning).
- **Frontend unit:** `Molecule.test.tsx` (renders SVG, strips `<script>`, caption
  presence/absence, empty-svg → renders nothing).
- **E2E:** `st_molecule_test.py` (all structures render an `<svg>`, captions show,
  visual snapshot, top-level class).

## Alternatives considered

1. **A widget per feature, each importing RDKit drawing.** Rejected: duplicates the
   drawing/matching code (churn), and every rendering change becomes shotgun surgery
   across N elements.
2. **`st.chem_dataframe` as a brand-new data grid.** Rejected: would fork selection,
   search, and mini-chart logic from `st.dataframe`. A `MoleculeColumn` reuses all of
   it.
3. **A parallel `st.cache_mol` cache.** Rejected: duplicates cache storage/TTL/hashing.
   A type serializer on the existing cache is smaller and makes *all* caches
   Mol-safe.
4. **Render molecules to SVG in the browser with RDKit-JS.** Rejected for the base 2D
   case: ships a large WASM/JS dependency and re-implements what server-side RDKit
   already does well. Reserved for the interactive editor/3D viewer (Phases 4–5),
   where client-side interactivity actually requires it.
5. **Send `Mol.ToBinary()` to the frontend and draw there.** Rejected: pushes RDKit
   into the browser bundle; the proto carrying a finished SVG keeps the frontend thin.
