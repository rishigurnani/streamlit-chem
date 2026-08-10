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

"""Tests for the ``st.mol_viewer`` widget: proto marshalling and selection state."""

from __future__ import annotations

import pytest
from parameterized import parameterized
from rdkit import Chem

import streamlit as st
from streamlit.elements.mol_viewer import (
    MolViewerSelectionSerde,
    MolViewerSelectionState,
    MolViewerState,
)
from streamlit.errors import StreamlitAPIException
from tests.delta_generator_test_case import DeltaGeneratorTestCase


class MolViewerProtoTest(DeltaGeneratorTestCase):
    """Test ability to marshall mol_viewer protos."""

    def test_defaults_from_smiles(self):
        """A SMILES string embeds a 3D MOL block with default styling."""
        st.mol_viewer("c1ccccc1O")

        proto = self.get_delta_from_queue().new_element.mol_viewer
        assert "V2000" in proto.molblock
        assert proto.style == "stick"
        assert proto.surface == ""
        assert proto.surface_opacity == 0.0
        assert proto.background == ""
        assert proto.spin is False
        assert list(proto.selection_mode) == ["atom"]
        assert proto.id != ""

    def test_accepts_mol_object(self):
        """An RDKit Mol object is embedded into the MOL block."""
        st.mol_viewer(Chem.MolFromSmiles("CCO"))

        proto = self.get_delta_from_queue().new_element.mol_viewer
        assert "V2000" in proto.molblock

    def test_style_surface_and_options_forwarded(self):
        """Style, surface, spin, and background reach the proto."""
        st.mol_viewer(
            "CCO",
            style="ball_and_stick",
            surface="sas",
            spin=True,
            background="#101010",
        )

        proto = self.get_delta_from_queue().new_element.mol_viewer
        assert proto.style == "ball_and_stick"
        assert proto.surface == "sas"
        assert proto.surface_opacity > 0.0
        assert proto.spin is True
        assert proto.background == "#101010"

    def test_selection_mode_iterable_is_sorted_and_deduped(self):
        """An iterable of modes is validated and stored de-duplicated."""
        st.mol_viewer("CCO", selection_mode=["bond", "atom", "bond"])

        proto = self.get_delta_from_queue().new_element.mol_viewer
        assert list(proto.selection_mode) == ["atom", "bond"]

    def test_empty_selection_mode_disables_selection(self):
        """An empty selection_mode leaves the proto with no clickable modes."""
        st.mol_viewer("CCO", selection_mode=())

        proto = self.get_delta_from_queue().new_element.mol_viewer
        assert list(proto.selection_mode) == []

    @parameterized.expand([("invalid_style",), ("wireframe",)])
    def test_invalid_style_raises(self, style: str):
        """An unsupported style raises a StreamlitAPIException."""
        with pytest.raises(StreamlitAPIException, match="Invalid style"):
            st.mol_viewer("CCO", style=style)  # type: ignore[arg-type]

    def test_invalid_surface_raises(self):
        """An unsupported surface raises a StreamlitAPIException."""
        with pytest.raises(StreamlitAPIException, match="Invalid surface"):
            st.mol_viewer("CCO", surface="bubble")  # type: ignore[arg-type]

    def test_invalid_selection_mode_raises(self):
        """A selection_mode outside {atom, bond} raises a StreamlitAPIException."""
        with pytest.raises(StreamlitAPIException, match="Invalid selection_mode"):
            st.mol_viewer("CCO", selection_mode=["residue"])  # type: ignore[list-item]

    @parameterized.expand([(0,), (-10,)])
    def test_invalid_height_raises(self, height: int):
        """A non-positive height raises a StreamlitAPIException."""
        with pytest.raises(StreamlitAPIException, match="Invalid height"):
            st.mol_viewer("CCO", height=height)

    def test_default_return_value_is_empty_state(self):
        """Without interaction the widget returns an empty selection state."""
        state = st.mol_viewer("CCO", key="viewer")

        assert isinstance(state, MolViewerState)
        assert state.selection.atoms == []
        assert state.selection.bonds == []


def test_selection_serde_roundtrip_empty():
    """Deserializing ``None`` yields an empty, typed selection state."""
    state = MolViewerSelectionSerde().deserialize(None)

    assert isinstance(state.selection, MolViewerSelectionState)
    assert state.selection.atoms == []
    assert state.selection.bonds == []


def test_selection_serde_parses_clicked_atoms_and_bonds():
    """A JSON selection payload deserializes into atoms/bonds (attr + item access)."""
    serde = MolViewerSelectionSerde()
    state = serde.deserialize('{"selection": {"atoms": [1, 4], "bonds": [2]}}')

    # Attribute access.
    assert state.selection.atoms == [1, 4]
    assert state.selection.bonds == [2]
    # Item access.
    assert state["selection"]["atoms"] == [1, 4]
    # Round-trips back to a JSON string carrying the same selection.
    assert '"atoms": [1, 4]' in serde.serialize(state)
