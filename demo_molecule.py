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

# streamlit-chem demo — showcases the native streamlit-chem chemical elements.
#
# Run it with the helper script:  ./demo_molecule.sh
# ...or directly:                 uv run streamlit run demo_molecule.py

import pandas as pd
from rdkit import Chem
from rdkit.Chem import Descriptors

import streamlit as st

st.title("🧪 streamlit-chem — chemical elements demo")
st.caption(
    "Native RDKit-rendered chemistry for Streamlit. Molecules go straight from "
    "Python to the browser — no iframe, no custom component."
)

# --- 1. From a SMILES string --------------------------------------------------
st.header("1. From a SMILES string")
st.code('st.molecule("c1ccccc1O", caption="Phenol")', language="python")
st.molecule("c1ccccc1O", caption="Phenol")

# --- 2. From an RDKit Mol object ---------------------------------------------
st.header("2. From an `rdkit.Chem.Mol` object")
st.code('st.molecule(Chem.MolFromSmiles("CCO"), caption="Ethanol")', language="python")
st.molecule(Chem.MolFromSmiles("CCO"), caption="Ethanol")

# --- 3. Fixed pixel width -----------------------------------------------------
st.header("3. Fixed pixel width")
st.code(
    'st.molecule("CN1C=NC2=C1C(=O)N(C(=O)N2C)C", caption="Caffeine", width=200)',
    language="python",
)
st.molecule("CN1C=NC2=C1C(=O)N(C(=O)N2C)C", caption="Caffeine", width=200)

# --- 4. Interactive: draw your own -------------------------------------------
st.header("4. Interactive — type a SMILES")
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

# --- 5. Interactive chemical dataframe ----------------------------------------
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

# --- 6. Molecule summary card -------------------------------------------------
st.header("6. `st.mol_card` — compact summary card")
st.caption(
    "Composes `st.molecule` with physicochemical `st.metric`s and a Lipinski "
    "rule-of-five badge inside a bordered container."
)
st.mol_card(
    "CC(=O)Oc1ccccc1C(=O)O",
    title="Aspirin",
    metrics=["MW", "LogP", "TPSA", "HBD", "HBA"],
)

# --- 7. Interactive 2D editor -------------------------------------------------
st.header("7. `st.chem_draw` — build a library by drawing")
st.caption(
    "Wraps the Ketcher editor and returns the drawn structure as an RDKit "
    "`Mol`. Draw a molecule and click **Apply** in the editor — each applied "
    "structure is appended to a running library and shown with `st.chem_dataframe`."
)
if "drawn_library" not in st.session_state:
    st.session_state.drawn_library = []
    # The SMILES most recently committed via Ketcher's Apply button. Tracking it
    # separately means ordinary reruns (and Clear) don't re-append the structure
    # the editor still holds.
    st.session_state.last_applied = None

# Start empty so the first structure in the library is one you actually drew.
drawn = st.chem_draw(key="chem_draw_editor")
if drawn is not None:
    applied = Chem.MolToSmiles(drawn)
    if applied != st.session_state.last_applied:
        st.session_state.drawn_library.append(applied)
        st.session_state.last_applied = applied

if st.button(":material/delete: Clear library"):
    st.session_state.drawn_library = []

if st.session_state.drawn_library:
    drawn_df = pd.DataFrame({"Mol": st.session_state.drawn_library})
    drawn_df.insert(0, "#", range(1, len(drawn_df) + 1))
    drawn_df["MW"] = [
        round(Descriptors.MolWt(Chem.MolFromSmiles(s)), 1) for s in drawn_df["Mol"]
    ]
    st.chem_dataframe(drawn_df, mol_column="Mol", hide_index=True)
else:
    st.info("Draw a molecule and click **Apply** in the editor to add it.")

st.divider()

# --- 8. Interactive 3D viewer -------------------------------------------------
st.header("8. `st.mol_viewer` — click an atom to see its element")
st.caption(
    "Renders a WebGL 3D structure (3Dmol.js) from a server-side RDKit conformer. "
    "Click atoms and streamlit-chem reports the element (C, O, N, ...) of each one."
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
molblock = caffeine_molblock()
event = st.mol_viewer(
    molblock,
    style="ball_and_stick",
    surface="vdw",
    generate_3d=False,
    height=420,
)
# Parse the *same* MOL block the viewer rendered so atom indices line up exactly
# with the clicked atoms (the embedding adds explicit hydrogens).
viewer_mol = Chem.MolFromMolBlock(molblock, removeHs=False)
selected_atoms = event.selection.atoms
if selected_atoms:
    clicked = [
        f"atom {i} → **{viewer_mol.GetAtomWithIdx(i).GetSymbol()}**"
        for i in selected_atoms
        if i < viewer_mol.GetNumAtoms()
    ]
    st.success("Clicked: " + ",  ".join(clicked))
else:
    st.info("Click an atom in the 3D view to see its element.")

st.divider()

# --- 9. Chemical-space map ----------------------------------------------------
st.header("9. `st.chem_space` — map & lasso-select a library")
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

# --- 10. R-group decomposition ------------------------------------------------
st.header("10. `st.r_group_decomposition` — R-groups around a scaffold")
st.caption(
    "Breaks a series apart around a shared core: each row shows the whole "
    "**molecule** next to its **core** and every **R-group** position. "
    "4-aminophenol carries two substituents, so the table grows an **R2** "
    "column automatically."
)
st.code(
    'st.r_group_decomposition("c1ccccc1", mols, labels=names)',
    language="python",
)
st.r_group_decomposition(
    "c1ccccc1",
    ["Nc1ccc(O)cc1", "c1ccccc1O", "Cc1ccccc1", "Nc1ccccc1"],
    labels=["4-Aminophenol", "Phenol", "Toluene", "Aniline"],
    label_column="Compound",
)
