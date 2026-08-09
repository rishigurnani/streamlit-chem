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
