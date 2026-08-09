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

"""Tests for the ``st.molecule`` element proto marshalling."""

from __future__ import annotations

import pytest
from parameterized import parameterized
from rdkit import Chem

import streamlit as st
from streamlit.errors import StreamlitAPIException
from tests.delta_generator_test_case import DeltaGeneratorTestCase


class MoleculeTest(DeltaGeneratorTestCase):
    """Test ability to marshall molecule protos."""

    def test_molecule_from_smiles(self):
        """A SMILES string renders to an SVG carried by the proto."""
        st.molecule("c1ccccc1O")

        proto = self.get_delta_from_queue().new_element.molecule
        assert "<svg" in proto.svg
        assert proto.caption == ""

    def test_molecule_from_mol_object(self):
        """An RDKit Mol object renders to an SVG carried by the proto."""
        st.molecule(Chem.MolFromSmiles("CCO"))

        proto = self.get_delta_from_queue().new_element.molecule
        assert "<svg" in proto.svg

    def test_molecule_caption(self):
        """The caption argument is forwarded onto the proto."""
        st.molecule("CCO", caption="Ethanol")

        proto = self.get_delta_from_queue().new_element.molecule
        assert proto.caption == "Ethanol"

    def test_molecule_highlight_substructure_changes_output(self):
        """Highlighting a matched substructure alters the rendered SVG."""
        st.molecule("CC(=O)Oc1ccccc1C(=O)O")
        without_highlight = self.get_delta_from_queue().new_element.molecule.svg

        st.molecule("CC(=O)Oc1ccccc1C(=O)O", highlight_substructure="c1ccccc1")
        with_highlight = self.get_delta_from_queue().new_element.molecule.svg

        assert with_highlight != without_highlight

    def test_molecule_highlight_without_match_is_noop(self):
        """A non-matching highlight query renders the same as no highlight."""
        st.molecule("CCO")
        without_highlight = self.get_delta_from_queue().new_element.molecule.svg

        st.molecule("CCO", highlight_substructure="c1ccccc1")
        with_missing_highlight = self.get_delta_from_queue().new_element.molecule.svg

        assert without_highlight == with_missing_highlight

    def test_molecule_invalid_smiles_raises(self):
        """An unparseable SMILES string raises a StreamlitAPIException."""
        with pytest.raises(StreamlitAPIException):
            st.molecule("not-a-molecule")

    @parameterized.expand(
        [
            ("content", "use_content", True),
            ("stretch", "use_stretch", True),
            (400, "pixel_width", 400),
        ]
    )
    def test_width_parameter(self, width_value, expected_field, expected_value):
        """The width argument is reflected in the element's width config."""
        st.molecule("CCO", width=width_value)

        delta = self.get_delta_from_queue()
        assert getattr(delta.new_element.width_config, expected_field) == expected_value

    @parameterized.expand(
        [
            ("content", "use_content", True),
            ("stretch", "use_stretch", True),
            (300, "pixel_height", 300),
        ]
    )
    def test_height_parameter(self, height_value, expected_field, expected_value):
        """The height argument is reflected in the element's height config."""
        st.molecule("CCO", height=height_value)

        delta = self.get_delta_from_queue()
        assert (
            getattr(delta.new_element.height_config, expected_field) == expected_value
        )

    def test_integer_width_sets_render_canvas(self):
        """An integer width pins the RDKit canvas width, not just the layout."""
        st.molecule("CCO", width=321)

        proto = self.get_delta_from_queue().new_element.molecule
        assert "width='321px'" in proto.svg
