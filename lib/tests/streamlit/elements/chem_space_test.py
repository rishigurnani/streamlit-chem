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

"""Tests for ``st.chem_space``."""

from __future__ import annotations

import numpy as np
import pytest

import streamlit as st
from streamlit.elements.chem_space import _build_figure, _reduce_to_2d
from streamlit.elements.lib import mol_utils
from streamlit.errors import StreamlitAPIException
from streamlit.testing.v1 import AppTest

_MOLS = ["c1ccccc1O", "c1ccccc1N", "c1ccccc1C", "CCO", "CCN"]


def _chem_space_app() -> None:
    import streamlit as st

    mols = ["c1ccccc1O", "c1ccccc1N", "c1ccccc1C", "CCO", "CCN"]
    event = st.chem_space(
        mols, color_by=[6.1, 5.4, 7.2, 4.0, 4.3], labels=list("abcde")
    )
    st.write(event.selection.point_indices)


def _chem_space_ignore_app() -> None:
    import streamlit as st

    st.chem_space(["c1ccccc1O", "CCO"], on_select="ignore")


def test_renders_plotly_chart_and_returns_empty_selection() -> None:
    """A chem space renders a Plotly chart whose default selection is empty."""
    at = AppTest.from_function(_chem_space_app).run()

    assert not at.exception
    assert len(at.get("plotly_chart")) == 1
    # With no user interaction the returned selection has no points.
    assert at.json[0].value == "[]"


def test_ignore_mode_still_renders() -> None:
    """``on_select='ignore'`` renders a static chart without error."""
    at = AppTest.from_function(_chem_space_ignore_app).run()

    assert not at.exception
    assert len(at.get("plotly_chart")) == 1


def test_empty_mols_raises() -> None:
    """An empty molecule collection raises a StreamlitAPIException."""
    with pytest.raises(StreamlitAPIException, match="at least one molecule"):
        st.chem_space([])


def test_color_by_length_mismatch_raises() -> None:
    """A ``color_by`` of the wrong length raises a clear error."""
    with pytest.raises(StreamlitAPIException, match="color_by has 2 values"):
        st.chem_space(_MOLS, color_by=[1.0, 2.0])


def test_labels_length_mismatch_raises() -> None:
    """A ``labels`` sequence of the wrong length raises a clear error."""
    with pytest.raises(StreamlitAPIException, match="labels has 1 values"):
        st.chem_space(_MOLS, labels=["only-one"])


def test_unknown_method_raises() -> None:
    """An unsupported reduction method raises a StreamlitAPIException."""
    with pytest.raises(StreamlitAPIException, match="Unknown method"):
        st.chem_space(_MOLS, method="isomap")  # type: ignore[arg-type]


def test_invalid_smiles_raises() -> None:
    """An unparseable molecule surfaces the underlying parse error."""
    with pytest.raises(StreamlitAPIException, match="Could not parse molecule"):
        st.chem_space(["not-a-molecule"])


@pytest.mark.parametrize(
    ("method", "package"),
    [("tsne", "scikit-learn"), ("umap", "umap-learn")],
)
def test_optional_method_without_package_raises_helpfully(
    method: str, package: str
) -> None:
    """A projection method whose optional package is absent explains how to install it.

    scikit-learn and umap-learn are not installed in the test environment, so
    requesting those methods surfaces an actionable StreamlitAPIException.
    """
    try:
        __import__({"tsne": "sklearn", "umap": "umap"}[method])
        pytest.skip(f"{package} is installed; the missing-package path is unreachable.")
    except ImportError:
        pass

    features = mol_utils.compute_fingerprints(
        [mol_utils.to_mol(s) for s in _MOLS], n_bits=64
    )
    with pytest.raises(StreamlitAPIException, match=package):
        _reduce_to_2d(features, method)  # type: ignore[arg-type]


@pytest.mark.parametrize("n_mols", [1, 3, 10])
def test_reduce_to_2d_pca_shape(n_mols: int) -> None:
    """PCA always projects to two columns, even for a single molecule."""
    mols = [mol_utils.to_mol("CCO") for _ in range(n_mols)]
    features = mol_utils.compute_fingerprints(mols, n_bits=128)
    coords = _reduce_to_2d(features, "pca")
    assert coords.shape == (n_mols, 2)


def test_reduce_to_2d_single_molecule_is_origin() -> None:
    """A single molecule has no variance, so PCA places it at the origin."""
    features = mol_utils.compute_fingerprints([mol_utils.to_mol("CCO")], n_bits=64)
    coords = _reduce_to_2d(features, "pca")
    assert np.allclose(coords, 0.0)


def test_build_figure_single_trace_with_all_points() -> None:
    """The figure holds one trace so point indices map 1:1 to input molecules."""
    coords = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 0.5]])
    figure = _build_figure(
        coords,
        color_by=[1.0, 2.0, 3.0],
        color_label="pIC50",
        labels=["a", "b", "c"],
        method="pca",
        height=400,
    )
    assert len(figure.data) == 1
    assert len(figure.data[0].x) == 3
    # The color scale is driven by the provided per-molecule values.
    assert tuple(figure.data[0].marker.color) == (1.0, 2.0, 3.0)


def test_build_figure_without_color_has_no_colorbar() -> None:
    """Without ``color_by`` the markers carry no color array."""
    coords = np.array([[0.0, 0.0], [1.0, 1.0]])
    figure = _build_figure(
        coords,
        color_by=None,
        color_label="Value",
        labels=None,
        method="pca",
        height=400,
    )
    assert figure.data[0].marker.color is None
