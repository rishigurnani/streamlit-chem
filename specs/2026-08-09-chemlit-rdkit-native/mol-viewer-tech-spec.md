# Tech Spec — `st.mol_viewer` (interactive 3D molecule viewer)

Status: **DRAFT — for review** · Phase 4b of ChemLit · Author: Rishi Gurnani

This spec covers the **native, event-emitting** 3D viewer (the option-2 path): a
hardware-accelerated WebGL viewer whose atom/bond/pose clicks flow back into the
Python script. It is the first ChemLit element that ships a new frontend
dependency and a bidirectional (widget) round-trip, so it is scoped and reviewed
separately from Phases 1–3.

---

## 1. Motivation & user stories

Phases 1–3 are display + 2D. Drug-discovery work also needs 3D: conformers,
protein-ligand poses, surfaces — and, critically, **the 3D view driving the rest
of the app**. The value of option 2 over a static embed is exactly this
bidirectionality.

- *As a user*, I generate a 3D conformer from a `Mol` and rotate/zoom it.
- *As a user*, I click an atom and my script reacts (`st.toast`, annotate, filter).
- *As a user*, I lasso/click a pose and a downstream `st.chem_dataframe` filters to it.
- *As a user*, I overlay a surface (SAS/vdW) on a stick model.

The clickable-atom → rerun behavior is the whole reason to build the native
component instead of a `components.v1.html` embed.

---

## 2. Public API

```python
selection = st.mol_viewer(
    data,                       # str (SMILES/MOLBLOCK) | rdkit.Chem.Mol
    *,
    style="stick",              # "stick" | "sphere" | "line" | "cartoon" | "ball_and_stick"
    surface=None,               # None | "vdw" | "sas" | "ms"  (+ opacity via dict, see below)
    generate_3d=True,           # embed a 3D conformer if the input has none
    spin=False,                 # auto-rotate
    background=None,            # None (theme-aware) | CSS color
    height=480,                 # px
    on_select=None,             # callback, fired on selection change
    selection_mode=("atom",),   # subset of {"atom", "bond"}; () disables selection
    key=None,
) -> MolViewerState
```

### Return value — `MolViewerState`

Mirrors the established selection-state pattern (`st.dataframe`, `st.plotly_chart`)
so we reuse existing infrastructure and users get a familiar shape. It is a
`ReadOnlyAttributeDictionary` supporting both attribute and item access:

```python
selection.selection.atoms   # list[int]  — clicked atom indices
selection.selection.bonds   # list[int]  — clicked bond indices
selection["selection"]["atoms"]
```

**Decision:** use selection-state (not a bare `on_atom_click(atom_id)` callback).
Rationale: it is the idiomatic Streamlit event pattern, reuses the selection
serialization/`on_select` plumbing, and generalizes to bonds/poses without new
signatures. The original DX sketch's `on_atom_click=lambda ...` is expressible as
`on_select=` reading `selection.selection.atoms[-1]`.

---

## 3. Architecture

ChemLit's rule holds: **one Mol-core, thin elements.** The only new chem logic is
3D embedding; everything else is the widget + frontend viewer.

### 3.1 Mol-core addition (`elements/lib/mol_utils.py`)

```python
def to_molblock_3d(data: MoleculeData, *, generate_3d: bool = True) -> str:
    """Return a 3D MOL block. Embeds a conformer (ETKDG + MMFF) when needed."""
```

- Reuses `to_mol`. `AddHs` → `EmbedMolecule(ETKDG)` → `MMFFOptimizeMolecule`
  (fallback to UFF) → `MolToMolBlock`. If the input already has a 3D conformer and
  `generate_3d=False`, serialize as-is.
- Embedding is expensive → **must be cacheable**. It composes with Phase 2's
  `Mol` cache hashing: `to_molblock_3d` is a pure function of the Mol's binary, so
  wrapping it in `@st.cache_data` (or an internal `@st.cache_resource`) is trivial
  and documented in the demo.

### 3.2 Protobuf (`proto/streamlit/proto/MolViewer.proto`, `Element.proto` field 68)

```proto
message MolViewer {
  string molblock = 1;          // server-generated 3D MOL block
  string style = 2;             // stick | sphere | line | cartoon | ball_and_stick
  string surface = 3;           // "" | vdw | sas | ms
  double surface_opacity = 4;   // 0..1
  string background = 5;        // "" => theme-aware
  bool spin = 6;
  repeated string selection_mode = 7;  // atom, bond
  string id = 8;                // widget id
  string form_id = 9;
  bool disabled = 10;
}
```

Selection travels back in `WidgetStates` as a JSON string
(`{"atoms": [...], "bonds": [...]}`), exactly like dataframe/plotly selection.

### 3.3 Backend widget (`elements/mol_viewer.py`, `MolViewerMixin`)

- Registers a widget via `register_widget` (this is what makes it bidirectional —
  unlike `st.molecule`, which is a pure display element).
- Value serializer/deserializer converts the JSON selection ↔ `MolViewerState`.
  Reuse the `dataframe`/`plotly_chart` selection helpers where possible rather
  than hand-rolling.
- `on_select` wired through the standard widget callback machinery.
- Builds the proto via `to_molblock_3d(data, generate_3d=...)`.

### 3.4 Frontend (`frontend/lib/src/components/elements/MolViewer/`)

- **New npm dependency: `3dmol`** (3Dmol.js, BSD-3-Clause, WebGL). Bundled via
  Vite (no CDN — consistent with the fork's no-iframe/no-external-JS stance).
- `MolViewer.tsx`: `$3Dmol.createViewer(ref)`, `addModel(molblock, "sdf")`,
  `setStyle` from `style`, `addSurface` when set, `setBackgroundColor`
  (theme-aware default via emotion theme), `spin`, `render()`.
- **Events:** `viewer.setClickable({}, true, cb)`; the callback maps the picked
  atom/bond to indices and calls the widget manager
  (`widgetMgr.setStringValue(element, json, {fromUi: true})`) → triggers a rerun
  with the new selection. Gate on `selection_mode`.
- Registered in `ElementNodeRenderer.tsx`; wrapped with the fullscreen wrapper;
  sizes via `useCalculatedDimensions`; disposes the GL context on unmount.

---

## 4. Testing

- **Python unit** (`mol_viewer_test.py`, `mol_utils_test.py`): `to_molblock_3d`
  produces a MOL block with 3D coords (non-zero z); proto marshalling of
  style/surface/background/spin; selection deserialization → `MolViewerState`
  (attribute + item access, per the typing-test guidance); invalid `style`/`surface`
  raises `StreamlitAPIException`; completeness guards (`element_mocks` WIDGET list,
  public-API, api-reference doc).
- **Typing test** (`mol_viewer_types.py`): `assert_type` on the returned state.
- **Vitest** (`MolViewer.test.tsx`): renders with a mocked `$3Dmol`; a simulated
  atom-click calls the widget manager with the expected JSON.
- **E2E** (`st_mol_viewer.py` + `_test.py`): renders; **note:** WebGL snapshots are
  flaky/unavailable in headless CI, so assert DOM/canvas presence and (if feasible)
  a click updating a companion `st.write`, rather than pixel snapshots.

---

## 5. Dependencies, size, licensing

- `3dmol` npm: ~1–2 MB minified; lazy-loaded (`React.lazy`) so it's only fetched
  when a viewer is on the page. **Confirm exact version + BSD-3 license at
  implementation.**
- No new Python runtime dependency — 3D embedding is RDKit, already a hard dep.

---

## 6. Risks & open questions (please weigh in)

1. **Bundle size / build.** Adds a WebGL lib + a real frontend rebuild. In this
   environment the frontend builds under Node 23 today, but this is the heaviest
   surface we've touched. Acceptable?
2. **Event model.** Do you want selection-state (`MolViewerState`, recommended) or
   the literal `on_atom_click(atom_id)` callback from the original sketch? (I
   recommend selection-state; the callback is a thin shim on top.)
3. **Selection scope.** Atoms + bonds now; **poses/residues and lasso-select**
   deferred to the SAR phase (Phase 5). OK to defer?
4. **Protein-ligand / multi-model.** Out of scope for v1 (single small molecule).
   Confirm.
5. **E2E depth.** Given headless WebGL limits, is DOM-presence + interaction
   coverage (no pixel snapshot) acceptable for the 3D view?
6. **Surface performance.** Surfaces on large molecules are slow; cap or warn?

---

## 7. Phasing within 4b

1. Mol-core `to_molblock_3d` + unit tests (no UI) — lands independently, testable now.
2. Proto + backend display-only viewer (no events) behind the same API.
3. Frontend component + `3dmol` dependency + render.
4. Bidirectional selection (the option-2 payoff) + `on_select`.
5. Demo section 10 + e2e.

Steps 1–2 are low-risk and reuse existing patterns; step 3–4 are the genuinely new
surface and where review matters most.
