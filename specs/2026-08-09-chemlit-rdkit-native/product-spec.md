---
author: rgurnani96
created: 2026-08-09
---

# streamlit-chem — An RDKit-native fork of Streamlit

## Summary

streamlit-chem extends Streamlit with first-class cheminformatics: native chemical UI
primitives that pass `rdkit.Chem.Mol` objects directly to and from Python, a
chemical-aware reactive state/caching layer, and out-of-the-box Structure-Activity
Relationship (SAR) analytics. This spec covers the full feature set and the
generalized primitives it is built on. The first shipped slice is
[`st.molecule`](#stmolecule-shipped-first-slice) plus the shared
[Mol-core](#the-mol-core-one-module-many-widgets); everything else layers on top of
that core without duplicating parsing, matching, or rendering logic.

## Problem

Integrating RDKit with Streamlit today means stitching together custom iframe
components, wrestling with pickling of C++-backed `Mol` objects across sessions,
and paying for full-script reruns on every interaction — which is fatal for heavy
property calculations, fingerprinting, and conformer generation on large libraries.
There is no native chemical column type, no chemical-aware cache, and no built-in
SAR tooling. Every drug-discovery team rebuilds the same plumbing.

We want the Streamlit script-to-app DX with RDKit as a native engine, so that a
chemist writes `st.molecule(mol)` and it just works — no iframe, no pickling
foot-guns, no recomputation of descriptors when someone merely rotates a 3D viewer.

## Design principle: don't build 15 widgets, build one core + thin layers

The headline feature list looks like ~15 independent components. It is not. Most of
them are the **same three operations** — coerce input to a `Mol`, match a
substructure, render a `Mol` to 2D — wearing different UI. To prevent code churn and
shotgun surgery, streamlit-chem is organized around a single shared core and a small number
of thin composition layers.

### The Mol-core (one module, many widgets)

`streamlit/elements/lib/mol_utils.py` is the **only** place that imports RDKit for
drawing/matching. It exposes:

- `to_mol(data)` — coerce a SMILES string or `Mol` into a `Mol` (validates, raises
  `StreamlitAPIException` on bad input).
- `to_query(query)` / `get_substructure_match(mol, query)` — coerce a SMARTS/SMILES
  or `Mol` query and return the matched `(atom_ids, bond_ids)` of the first match.
- `mol_to_svg(mol, *, width, height, highlight_atoms, highlight_bonds)` — render a
  self-contained 2D SVG server-side.

Every chemical element consumes these; none re-implements them. Adding a new
chemical element is "compose the core + a proto + a thin React viewer", never "copy
the RDKit drawing code again".

### How the requested features collapse onto existing Streamlit primitives

| Requested feature | Built as | Reuses |
| --- | --- | --- |
| `st.molecule` (foundational 2D render) | New display element | Mol-core |
| `st.chem_dataframe` | **New `column_config` column type** (`MoleculeColumn`), not a new widget | Mol-core render + existing `st.dataframe` selection/search |
| `st.smarts_input` | `st.text_input` + live validation + highlight preview | Mol-core `to_query` + render |
| `st.mol_card` | Composition of `st.molecule` + `st.metric`/badges | Mol-core + descriptor helpers |
| `st.chem_draw` | Editor widget wrapping Ketcher | **Borrow from [`streamlit-ketcher`](https://github.com/streamlit/streamlit-ketcher)** + Mol-core for round-tripping to `Mol` |
| `st.mol_viewer` (2D/3D) | New widget wrapping a WebGL viewer (3Dmol.js) | Mol-core for 2D + conformer helpers |
| "Partial rerun zones for molecules" | **Already exists** as `st.fragment` | — (documentation, not code) |
| `st.cache_mol` | **Pluggable serializer on the existing cache** via `Mol.ToBinary()`/`Mol(bytes)` | `runtime/caching` + `hashing` |
| `st.async_progress` / async pipeline | Generalize existing background-work + `st.status`/`st.progress` | `runtime/fragment`, threading |
| `st.chem_space` | New element wrapping the existing scatter selection + fingerprint→UMAP/t-SNE | `st.plotly_chart`/vega selection events, Mol-core fingerprints |
| R-group decomposition / MMP matrix | Composition on top of `st.chem_dataframe` + Mol-core | `MoleculeColumn` + RDKit `rdRGroupDecomposition` |
| "Substructure highlight binding" across widgets | A shared **highlight query in session state** consumed by every element's render call | Mol-core match; standard widget state |

The two most important generalizations:

1. **`st.chem_dataframe` is not a widget — it is a column type.** Streamlit already
   has `st.column_config` with pluggable column types and a dataframe that does
   selection, search, and mini-charts. A `MoleculeColumn` that renders each cell's
   `Mol` via the Mol-core gets auto-rendered structures, SMARTS column search, and
   row selection **for free**, with zero changes to the dataframe widget itself. This
   avoids a second parallel data-grid and the shotgun surgery of duplicating grid
   features.

2. **`st.cache_mol` is not a second cache — it is a serializer registration.** RDKit
   `Mol` objects wrap C++ pointers that pickle badly. Instead of a parallel caching
   API, we register a type-specific serializer (`Mol.ToBinary()` ⇄ `Chem.Mol(bytes)`)
   in the existing cache/hashing machinery, so `@st.cache_data` transparently and
   safely stores molecules. `st.cache_mol` becomes at most a thin, discoverable alias.

## Proposal

### API surface (full target)

```python
import streamlit_chem as st  # streamlit-chem is import-compatible with streamlit

# 1. Native chemical UI
st.molecule(mol_or_smiles, *, caption=None, highlight_substructure=None,
            width="content", height="content")            # 2D structure (shipped)
query = st.chem_draw(label, default="c1ccccc1O")          # editor -> Mol
smarts = st.smarts_input(label)                           # validated SMARTS
sel = st.chem_dataframe(df, mol_column="Mol",             # dataframe + MoleculeColumn
                        highlight_substructure=query,
                        column_config={"Mol": st.column_config.MoleculeColumn()})
st.mol_card(mol, metrics=["MW", "LogP", "TPSA", "HBD", "HBA"])
click = st.mol_viewer(mol, generate_3d=True, style="stick", surface=True)

# 2. Chemical-aware reactive state
@st.cache_data                 # Mol serialized via ToBinary under the hood
def fingerprints(mols): ...
with st.async_progress("Generating conformers"):  # background work, live progress
    ensemble = generate_conformers(mol, n=1000)

# 3. SAR / chemical space
pts = st.chem_space(mols, method="umap", color_by="pIC50")  # lasso -> selection
rgroups = st.r_group_decomposition(core=scaffold, mols=mols)
```

### `st.molecule` (shipped first slice)

Display a molecule as a native 2D structure, rendered server-side by RDKit and
delivered to the browser as a sanitized, self-contained SVG (no iframe, no
third-party JS).

- **`data`** (`str | rdkit.Chem.Mol`, required): a SMILES string or a `Mol`.
- **`caption`** (`str | None`): text shown beneath the structure (e.g. a name).
- **`highlight_substructure`** (`str | rdkit.Chem.Mol | None`): SMARTS/SMILES or
  `Mol`; the first match is highlighted. No match → nothing highlighted (not an
  error).
- **`width` / `height`** (`"content" | "stretch" | int`): standard layout sizing;
  an integer also pins the RDKit render canvas.

**Behavior & edge cases**

- Invalid SMILES / unparseable SMARTS → `StreamlitAPIException` with a clear message.
- Unsupported input type → `StreamlitAPIException`.
- The SVG is sanitized on the frontend with DOMPurify (SVG profile, no scripts).

**Example**

```python
import streamlit as st

st.molecule("CC(=O)Oc1ccccc1C(=O)O", caption="Aspirin",
            highlight_substructure="c1ccccc1")
```

## Rollout / phasing

1. **Phase 1 (this PR):** Mol-core + `st.molecule` (backend, proto, frontend, unit +
   e2e tests). Establishes the architecture.
2. **Phase 2:** `MoleculeColumn` for `st.column_config` (unlocks `st.chem_dataframe`)
   and `Mol` cache serialization (unlocks safe `@st.cache_data`/`st.cache_mol`).
3. **Phase 3:** `st.smarts_input`, `st.mol_card` (pure compositions of Phase 1–2).
4. **Phase 4:** `st.chem_draw` (adopt `streamlit-ketcher`), `st.mol_viewer` (3Dmol.js).
5. **Phase 5:** SAR tools — `st.chem_space`, R-group decomposition, cross-widget
   substructure highlight binding.

## Checklist

| Item                         | ✅ or comment          |
|------------------------------|------------------------|
| Works on SiS, Cloud, etc?    | ✅ Server-side SVG render; no iframe. RDKit must be present in the runtime image. |
| No breaking API changes      | ✅ Purely additive (`st.molecule`, new column type, cache serializer). |
| No new dependencies          | ❌ Adds `rdkit` as a hard dependency (the whole point of the fork). Phases 4–5 add JS viewers (Ketcher, 3Dmol.js). |
| Metrics collected            | ✅ `@gather_metrics("molecule")`; each new command instrumented likewise. |
| Any security/legal impact?   | ✅ SVG sanitized via DOMPurify. RDKit is BSD-3; Ketcher/3Dmol.js licenses to be confirmed in Phase 4. |
| Any docs changes needed?     | ✅ New API reference pages per command; migration note on the `streamlit_chem` import alias. |
