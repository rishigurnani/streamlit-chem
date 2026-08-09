# Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022-2026)
# Copyright (c) 2026 Rishi Gurnani
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
