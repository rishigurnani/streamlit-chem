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

"""Tests for ``st.chem_dataframe``."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import streamlit as st
from streamlit.errors import StreamlitAPIException
from streamlit.testing.v1 import AppTest

_SVG_DATA_URI_PREFIX = "data:image/svg+xml;base64,"


def _chem_dataframe_app() -> None:
    import pandas as pd

    import streamlit as st

    df = pd.DataFrame(
        {
            "Name": ["Phenol", "Ethanol"],
            "Mol": ["c1ccccc1O", "CCO"],
        }
    )
    st.chem_dataframe(df, mol_column="Mol")


def _chem_dataframe_missing_cell_app() -> None:
    import pandas as pd

    import streamlit as st

    df = pd.DataFrame({"Mol": ["CCO", None]})
    st.chem_dataframe(df, mol_column="Mol")


def _chem_dataframe_highlight_app() -> None:
    import pandas as pd

    import streamlit as st

    df = pd.DataFrame({"Mol": ["c1ccccc1O"]})
    st.chem_dataframe(df, mol_column="Mol")
    st.chem_dataframe(df, mol_column="Mol", highlight_substructure="c1ccccc1")


def test_renders_mol_column_as_image_data_uris() -> None:
    """The molecule column becomes SVG data URIs while other columns are untouched."""
    at = AppTest.from_function(_chem_dataframe_app).run()

    assert not at.exception
    rendered = at.dataframe[0].value
    assert all(str(cell).startswith(_SVG_DATA_URI_PREFIX) for cell in rendered["Mol"])
    # Non-molecule columns pass through unchanged.
    assert list(rendered["Name"]) == ["Phenol", "Ethanol"]


def test_missing_cell_renders_empty_string() -> None:
    """A ``None``/``NaN`` molecule cell renders as an empty string, not an error."""
    at = AppTest.from_function(_chem_dataframe_missing_cell_app).run()

    assert not at.exception
    rendered = at.dataframe[0].value
    assert str(rendered["Mol"].iloc[0]).startswith(_SVG_DATA_URI_PREFIX)
    assert rendered["Mol"].iloc[1] == ""


def test_highlight_changes_rendered_output() -> None:
    """Highlighting a substructure produces different data URIs than no highlight."""
    at = AppTest.from_function(_chem_dataframe_highlight_app).run()

    assert not at.exception
    without_highlight = at.dataframe[0].value["Mol"].iloc[0]
    with_highlight = at.dataframe[1].value["Mol"].iloc[0]
    assert without_highlight != with_highlight


def test_non_dataframe_raises() -> None:
    """A non-DataFrame input raises a StreamlitAPIException."""
    with pytest.raises(StreamlitAPIException, match="requires a pandas DataFrame"):
        st.chem_dataframe([1, 2, 3])  # type: ignore[arg-type]


def test_missing_mol_column_raises() -> None:
    """A missing molecule column raises a StreamlitAPIException."""
    with pytest.raises(StreamlitAPIException, match="was not found"):
        st.chem_dataframe(pd.DataFrame({"A": [1]}), mol_column="Mol")


@pytest.mark.parametrize("bad_smiles", ["not-a-molecule", "C(C"])
def test_invalid_smiles_cell_raises(bad_smiles: str) -> None:
    """An unparseable SMILES cell surfaces the underlying parse error."""
    with pytest.raises(StreamlitAPIException):
        st.chem_dataframe(pd.DataFrame({"Mol": [bad_smiles]}), mol_column="Mol")


def test_numpy_nan_cell_is_treated_as_missing() -> None:
    """A ``np.nan`` cell is treated as missing rather than raising a parse error."""
    # Should not raise even though the column dtype is float with NaN.
    st.chem_dataframe(pd.DataFrame({"Mol": [np.nan]}), mol_column="Mol")
