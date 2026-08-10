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

"""Tests for ``st.r_group_decomposition``."""

from __future__ import annotations

import pytest
from rdkit.Chem import Mol

import streamlit as st
from streamlit.errors import StreamlitAPIException
from streamlit.testing.v1 import AppTest

_SVG_DATA_URI_PREFIX = "data:image/svg+xml;base64,"


def _rgd_app() -> None:
    import streamlit as st

    st.r_group_decomposition(
        "c1ccccc1",
        ["c1ccccc1O", "c1ccccc1N", "CCO"],
        labels=["Phenol", "Aniline", "Ethanol"],
    )


def _rgd_no_match_app() -> None:
    import streamlit as st

    st.r_group_decomposition("P", ["CCO", "CCN"])


def test_returns_mol_valued_decomposition() -> None:
    """The returned table holds Mol fragments for each matched molecule."""
    table = st.r_group_decomposition("c1ccccc1", ["c1ccccc1O", "c1ccccc1N"])

    assert list(table.index) == [0, 1]
    assert "Core" in table.columns
    assert "R1" in table.columns
    # Fragment cells are RDKit Mol objects, not strings.
    assert all(isinstance(cell, Mol) for cell in table["Core"])


def test_unmatched_molecules_are_dropped_and_index_preserved() -> None:
    """Molecules without the core are excluded; the index tracks input positions."""
    table = st.r_group_decomposition("c1ccccc1", ["c1ccccc1O", "CCO", "c1ccccc1N"])

    # Ethanol (position 1) does not contain benzene, so it is absent; the
    # aromatic molecules keep their original 0 and 2 positions.
    assert list(table.index) == [0, 2]


def test_labels_appear_as_leading_column() -> None:
    """A provided label sequence becomes a leading column aligned to matches."""
    table = st.r_group_decomposition(
        "c1ccccc1",
        ["c1ccccc1O", "CCO", "c1ccccc1N"],
        labels=["Phenol", "Ethanol", "Aniline"],
        label_column="Name",
    )

    assert list(table["Name"]) == ["Phenol", "Aniline"]


def test_renders_dataframe_with_image_columns() -> None:
    """The decomposition renders a dataframe whose fragment cells are SVG URIs."""
    at = AppTest.from_function(_rgd_app).run()

    assert not at.exception
    rendered = at.dataframe[0].value
    assert all(str(cell).startswith(_SVG_DATA_URI_PREFIX) for cell in rendered["Core"])
    # The label column is passed through as text, not rendered as an image.
    assert list(rendered["Molecule"]) == ["Phenol", "Aniline"]


def test_no_match_shows_info_and_returns_empty() -> None:
    """When nothing matches the core, an info message shows and the table is empty."""
    at = AppTest.from_function(_rgd_no_match_app).run()

    assert not at.exception
    assert len(at.dataframe) == 0
    assert "No molecules matched" in at.info[0].value


def test_display_false_suppresses_rendering() -> None:
    """``display=False`` returns the table without rendering a dataframe."""
    table = st.r_group_decomposition("c1ccccc1", ["c1ccccc1O"], display=False)
    assert len(table) == 1


def test_empty_mols_raises() -> None:
    """An empty molecule collection raises a StreamlitAPIException."""
    with pytest.raises(StreamlitAPIException, match="at least one molecule"):
        st.r_group_decomposition("c1ccccc1", [])


def test_labels_length_mismatch_raises() -> None:
    """A ``labels`` sequence of the wrong length raises a clear error."""
    with pytest.raises(StreamlitAPIException, match="labels has 1 values"):
        st.r_group_decomposition("c1ccccc1", ["c1ccccc1O", "c1ccccc1N"], labels=["x"])


def test_invalid_core_raises() -> None:
    """An unparseable core surfaces the underlying parse error."""
    with pytest.raises(StreamlitAPIException, match="Could not parse molecule"):
        st.r_group_decomposition("not-a-core", ["c1ccccc1O"])
