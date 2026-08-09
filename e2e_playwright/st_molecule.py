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

from rdkit import Chem

import streamlit as st

# Render a molecule from a SMILES string.
st.molecule("c1ccccc1O", caption="Phenol")

# Render a molecule from an RDKit Mol object.
st.molecule(Chem.MolFromSmiles("CCO"), caption="Ethanol")

# Render a molecule with a highlighted substructure.
st.molecule(
    "CC(=O)Oc1ccccc1C(=O)O",
    caption="Aspirin (aromatic ring highlighted)",
    highlight_substructure="c1ccccc1",
)

# Render a molecule with a fixed pixel width.
st.molecule("CN1C=NC2=C1C(=O)N(C(=O)N2C)C", caption="Caffeine", width=200)
