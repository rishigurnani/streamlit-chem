# Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022-2026)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# ChemLit demo — showcases the native `st.molecule` element.
#
# Run it with the helper script:  ./demo_molecule.sh
# ...or directly:                 uv run streamlit run demo_molecule.py

import pandas as pd
from rdkit import Chem
from rdkit.Chem import Descriptors

import streamlit as st

st.title("🧪 ChemLit — `st.molecule` demo")
st.caption(
    "A native RDKit-rendered 2D structure element. No iframe, no custom "
    "component — molecules go straight from Python to the browser as SVG."
)

# --- 1. From a SMILES string --------------------------------------------------
st.header("1. From a SMILES string")
st.code('st.molecule("c1ccccc1O", caption="Phenol")', language="python")
st.molecule("c1ccccc1O", caption="Phenol")

# --- 2. From an RDKit Mol object ---------------------------------------------
st.header("2. From an `rdkit.Chem.Mol` object")
st.code('st.molecule(Chem.MolFromSmiles("CCO"), caption="Ethanol")', language="python")
st.molecule(Chem.MolFromSmiles("CCO"), caption="Ethanol")

# --- 3. Interactive: draw your own -------------------------------------------
st.header("3. Interactive — type a SMILES")
smiles = st.text_input("SMILES", value="CC(=O)Oc1ccccc1C(=O)O")
highlight = st.text_input(
    "Highlight substructure (SMARTS/SMILES, optional)", value="c1ccccc1"
)
mol = Chem.MolFromSmiles(smiles) if smiles else None
if mol is None:
    st.error("Invalid SMILES — try again.")
else:
    left, right = st.columns([2, 1])
    with left:
        st.molecule(
            mol,
            caption=smiles,
            highlight_substructure=highlight or None,
        )
    with right:
        st.metric("Mol. weight", f"{Descriptors.MolWt(mol):.1f}")
        st.metric("LogP", f"{Descriptors.MolLogP(mol):.2f}")
        st.metric("H-bond donors", Descriptors.NumHDonors(mol))
        st.metric("H-bond acceptors", Descriptors.NumHAcceptors(mol))

# --- 4. Fixed pixel width -----------------------------------------------------
st.header("4. Fixed pixel width")
st.code(
    'st.molecule("CN1C=NC2=C1C(=O)N(C(=O)N2C)C", caption="Caffeine", width=200)',
    language="python",
)
st.molecule("CN1C=NC2=C1C(=O)N(C(=O)N2C)C", caption="Caffeine", width=200)

# --- 5. Phase 2: interactive chemical dataframe -------------------------------
st.header("5. `st.chem_dataframe` — structures in a table")
st.caption(
    "A chemistry-aware wrapper around `st.dataframe`: the molecule column is "
    "rendered as 2D structures, everything else behaves like a normal dataframe."
)
library = pd.DataFrame(
    {
        "Name": ["Aspirin", "Caffeine", "Phenol", "Ibuprofen"],
        "Mol": [
            "CC(=O)Oc1ccccc1C(=O)O",
            "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
            "c1ccccc1O",
            "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
        ],
    }
)
# Descriptors for the non-molecule columns.
library["MW"] = [
    round(Descriptors.MolWt(Chem.MolFromSmiles(s)), 1) for s in library["Mol"]
]
library["LogP"] = [
    round(Descriptors.MolLogP(Chem.MolFromSmiles(s)), 2) for s in library["Mol"]
]
st.chem_dataframe(
    library,
    mol_column="Mol",
    highlight_substructure="c1ccccc1",
    hide_index=True,
)

# --- 6. Phase 2: chemical-aware caching ---------------------------------------
st.header("6. `@st.cache_data` with RDKit molecules")
st.caption(
    "`@st.cache_data` now accepts RDKit `Mol` arguments. The cache key is the "
    "**input molecule's structure** (via `Mol.ToBinary()`) — *not* the Python "
    "object identity, and *not* the fingerprint the function returns. So two "
    "**different** molecules serialize to different bytes and get **different** "
    "cache entries: a collision in the low-bit fingerprint *output* can never "
    "cause a wrong cache hit. (Caveat: `ToBinary()` captures the graph, stereo, "
    "and conformers, but not extra `Mol` properties set via `SetProp`.)"
)


@st.cache_data
def morgan_fingerprint(mol: Chem.Mol) -> str:
    """Cached on the molecule's binary identity; body runs only on a cache miss."""
    from rdkit.Chem import AllChem

    return AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=64).ToBitString()


st.code(
    "@st.cache_data\n"
    "def morgan_fingerprint(mol):  # mol is an rdkit.Chem.Mol\n"
    "    ...\n\n"
    "# Two *distinct* Mol objects with the same structure -> one cached result\n"
    'a = morgan_fingerprint(Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O"))\n'
    'b = morgan_fingerprint(Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O"))',
    language="python",
)
fp_a = morgan_fingerprint(Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O"))
fp_b = morgan_fingerprint(Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O"))
st.write("Fingerprint:", fp_a)
st.write(
    "Two distinct `Mol` objects with the same structure hit the same cache entry:",
    fp_a == fp_b,
)

# --- 7. Phase 3: validated SMARTS input ---------------------------------------
st.header("7. `st.smarts_input` — validated substructure query")
st.caption(
    "A chemistry-aware `st.text_input`: it validates the SMARTS/SMILES pattern "
    "with RDKit as you type and previews the match on an example molecule. "
    "Try breaking it (e.g. `c1cc`) to see the inline validation."
)
query = st.smarts_input(
    "Substructure query",
    value="c1ccccc1",
    preview="CC(=O)Oc1ccccc1C(=O)O",
)
st.write("Validated query:", query)

# --- 8. Phase 3: molecule summary card ----------------------------------------
st.header("8. `st.mol_card` — compact summary card")
st.caption(
    "Composes `st.molecule` with physicochemical `st.metric`s and a Lipinski "
    "rule-of-five badge inside a bordered container."
)
st.mol_card(
    "CC(=O)Oc1ccccc1C(=O)O",
    title="Aspirin",
    metrics=["MW", "LogP", "TPSA", "HBD", "HBA"],
    highlight_substructure="c1ccccc1",
)

# --- 9. Phase 4: interactive 2D editor ----------------------------------------
st.header("9. `st.chem_draw` — interactive 2D editor")
st.caption(
    "Wraps the Ketcher editor and returns the drawn structure directly as an "
    "RDKit `Mol`. Edit the molecule and click Apply to update the properties."
)
drawn = st.chem_draw("c1ccccc1O")
if drawn is not None:
    left, right = st.columns([1, 1])
    with left:
        st.molecule(drawn, caption="Your structure", width=250)
    with right:
        st.metric("Molecular weight", f"{Descriptors.MolWt(drawn):.1f}")
        st.metric("LogP", f"{Descriptors.MolLogP(drawn):.2f}")
else:
    st.info("Draw a molecule to see its properties.")

st.divider()

st.header("10. `st.mol_viewer` — interactive 3D viewer")
st.caption(
    "Renders a WebGL 3D structure (3Dmol.js) from a server-side RDKit conformer. "
    "Click atoms to select them — the selection flows straight back into Python."
)


# The 3D embedding is expensive, so cache the MOL block per SMILES. mol_viewer
# accepts the cached MOL block directly, skipping re-embedding on every rerun.
@st.cache_data
def caffeine_molblock() -> str:
    from streamlit.elements.lib.mol_utils import to_molblock_3d

    return to_molblock_3d("CN1C=NC2=C1C(=O)N(C(=O)N2C)C")


st.code(
    'event = st.mol_viewer("CN1C=NC2=C1C(=O)N(C(=O)N2C)C", style="ball_and_stick")',
    language="python",
)
event = st.mol_viewer(
    caffeine_molblock(),
    style="ball_and_stick",
    surface="vdw",
    generate_3d=False,
    height=420,
)
selected_atoms = event.selection.atoms
if selected_atoms:
    st.success(f"Selected atom indices: {selected_atoms}")
else:
    st.info("Click an atom in the 3D view to select it.")

st.divider()

# --- 11. Phase 5: chemical-space map ------------------------------------------
st.header("11. `st.chem_space` — map & lasso-select a library")
st.caption(
    "Turns a molecule library into a 2D map (fingerprints → PCA/t-SNE/UMAP). "
    "Box- or lasso-select points and the picked molecules flow straight back "
    "into Python — here they populate a `st.chem_dataframe` below the plot."
)
space_library = pd.DataFrame(
    {
        "Name": [
            "Phenol",
            "Aniline",
            "Toluene",
            "Benzoic acid",
            "Aspirin",
            "Ibuprofen",
            "Ethanol",
            "Propanol",
            "Butylamine",
            "Acetic acid",
            "Caffeine",
            "Paracetamol",
        ],
        "Mol": [
            "c1ccccc1O",
            "c1ccccc1N",
            "Cc1ccccc1",
            "OC(=O)c1ccccc1",
            "CC(=O)Oc1ccccc1C(=O)O",
            "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
            "CCO",
            "CCCO",
            "CCCCN",
            "CC(=O)O",
            "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
            "CC(=O)Nc1ccc(O)cc1",
        ],
    }
)
# A stand-in activity value to color the points by (e.g. a measured pIC50).
space_library["pIC50"] = [6.1, 5.4, 5.0, 6.3, 7.2, 7.8, 3.9, 4.1, 4.4, 3.6, 6.7, 6.9]
st.code(
    'event = st.chem_space(df["Mol"], color_by=df["pIC50"], labels=df["Name"])',
    language="python",
)
space_event = st.chem_space(
    space_library["Mol"].tolist(),
    color_by=space_library["pIC50"].tolist(),
    color_label="pIC50",
    labels=space_library["Name"].tolist(),
    height=440,
    key="chem_space_demo",
)
picked = space_event.selection.point_indices
if picked:
    st.write(f"**{len(picked)}** molecule(s) selected:")
    st.chem_dataframe(
        space_library.iloc[picked],
        mol_column="Mol",
        hide_index=True,
    )
else:
    st.info("Box- or lasso-select points in the map to list the molecules here.")

st.divider()

# --- 12. Phase 5: R-group decomposition ---------------------------------------
st.header("12. `st.r_group_decomposition` — R-groups around a scaffold")
st.caption(
    "Breaks a series apart around a shared core: one row per molecule, one "
    "column of rendered structures per R-group position. Returns the "
    "decomposition as a `Mol`-valued DataFrame for further SAR analysis."
)
st.code(
    'st.r_group_decomposition("c1ccccc1", mols, labels=names)',
    language="python",
)
st.r_group_decomposition(
    "c1ccccc1",
    ["c1ccccc1O", "Cc1ccccc1", "Clc1ccccc1", "Nc1ccccc1", "OCc1ccccc1"],
    labels=["Phenol", "Toluene", "Chlorobenzene", "Aniline", "Benzyl alcohol"],
    label_column="Compound",
)

st.divider()

# --- 13. Phase 5: cross-widget highlight binding ------------------------------
st.header("13. Cross-widget substructure highlight binding")
st.caption(
    "One shared query drives the highlight in *every* structure element — no "
    "element reaches into another; they all read the same value. Edit the query "
    "and watch both the molecule and the card update together."
)
shared_query = st.smarts_input(
    "Shared highlight query",
    value="c1ccccc1",
    key="shared_highlight",
)
bind_left, bind_right = st.columns(2)
with bind_left:
    st.molecule(
        "CC(=O)Oc1ccccc1C(=O)O",
        caption="Aspirin",
        highlight_substructure=shared_query,
    )
with bind_right:
    st.mol_card(
        "Cc1ccc(cc1)S(=O)(=O)N",
        title="p-Toluenesulfonamide",
        metrics=["MW", "LogP", "TPSA"],
        highlight_substructure=shared_query,
    )
