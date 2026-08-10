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

"""Tests for the ``st.chem_draw`` editor wrapper.

The Ketcher component returns its default value when there is no user
interaction, so these tests exercise the seeding and return-type conversion
logic around it.
"""

from __future__ import annotations

from rdkit import Chem

from streamlit.testing.v1 import AppTest


def _empty_app() -> None:
    import streamlit as st

    st.session_state["result"] = st.chem_draw()


def _seeded_mol_app() -> None:
    import streamlit as st

    st.session_state["result"] = st.chem_draw("c1ccccc1O")


def _seeded_smiles_app() -> None:
    import streamlit as st

    st.session_state["result"] = st.chem_draw("c1ccccc1O", return_type="smiles")


def _invalid_return_type_app() -> None:
    import streamlit as st

    st.chem_draw("CCO", return_type="molfile")  # type: ignore[arg-type]


def test_chem_draw_empty_returns_none() -> None:
    """With no seed and no interaction, the editor yields None."""
    at = AppTest.from_function(_empty_app).run()

    assert not at.exception
    assert at.session_state["result"] is None


def test_chem_draw_returns_mol() -> None:
    """A seeded editor returns the molecule as an RDKit Mol by default."""
    at = AppTest.from_function(_seeded_mol_app).run()

    assert not at.exception
    assert Chem.MolToSmiles(at.session_state["result"]) == Chem.CanonSmiles("c1ccccc1O")


def test_chem_draw_returns_smiles_when_requested() -> None:
    """With return_type='smiles', the canonical SMILES string is returned."""
    at = AppTest.from_function(_seeded_smiles_app).run()

    assert not at.exception
    assert at.session_state["result"] == Chem.CanonSmiles("c1ccccc1O")


def test_chem_draw_invalid_return_type_raises() -> None:
    """An unsupported return_type surfaces a StreamlitAPIException."""
    at = AppTest.from_function(_invalid_return_type_app).run()

    assert at.exception
