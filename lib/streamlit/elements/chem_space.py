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

"""Streamlit support for interactive chemical-space maps.

``st.chem_space`` is the SAR-workhorse of ChemLit: it turns a library of
molecules into a 2D scatter plot (fingerprints -> dimensionality reduction) that
users can lasso-select. The selected point indices flow back into the script so
a downstream ``st.chem_dataframe`` or ``st.mol_card`` can show exactly the
molecules the chemist circled. All RDKit work happens in the Mol-core
(``mol_utils.compute_fingerprints``); this module is the thin composition layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, TypeAlias, cast

from streamlit.elements.lib import mol_utils
from streamlit.errors import StreamlitAPIException
from streamlit.runtime.metrics_util import gather_metrics

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    import numpy as np

    from streamlit.delta_generator import DeltaGenerator
    from streamlit.elements.lib.mol_utils import FingerprintType, MoleculeData
    from streamlit.elements.lib.utils import Key
    from streamlit.elements.plotly_chart import PlotlyState, SelectionMode
    from streamlit.runtime.state import WidgetCallback

ChemSpaceMethod: TypeAlias = Literal["pca", "tsne", "umap"]


def _reduce_to_2d(features: np.ndarray, method: ChemSpaceMethod) -> np.ndarray:
    """Project the ``(n, n_bits)`` fingerprint matrix down to ``(n, 2)`` coordinates."""
    import numpy as np

    n_samples = features.shape[0]
    if method == "pca":
        # PCA via SVD keeps ChemLit's default projection dependency-free (NumPy
        # is already a hard dependency); t-SNE and UMAP are optional extras.
        centered = features.astype(float) - features.astype(float).mean(axis=0)
        left, singular_values, _ = np.linalg.svd(centered, full_matrices=False)
        projected = left * singular_values
        # Fewer than two components exist when there are <2 molecules or no
        # variance; pad so the result is always (n, 2).
        coords = np.zeros((n_samples, 2))
        available = min(2, projected.shape[1])
        coords[:, :available] = projected[:, :available]
        return coords
    if method == "tsne":
        try:
            from sklearn.manifold import TSNE
        except ImportError as error:  # pragma: no cover - optional dep
            raise StreamlitAPIException(
                "method='tsne' requires scikit-learn. Install it with "
                "`pip install scikit-learn`, or use method='pca'."
            ) from error
        # Perplexity must stay below the sample count; clamp it for small sets.
        perplexity = min(30, max(1, n_samples - 1))
        reducer = TSNE(
            n_components=2, init="pca", random_state=0, perplexity=perplexity
        )
        # scikit-learn is untyped here, so pin the result to a NumPy array.
        return np.asarray(reducer.fit_transform(features))
    if method == "umap":
        try:
            import umap
        except ImportError as error:  # pragma: no cover - optional dep
            raise StreamlitAPIException(
                "method='umap' requires umap-learn. Install it with "
                "`pip install umap-learn`, or use method='pca'."
            ) from error
        # UMAP needs at least two points and n_neighbors < n_samples.
        n_neighbors = min(15, max(2, n_samples - 1))
        reducer = umap.UMAP(n_components=2, random_state=0, n_neighbors=n_neighbors)
        # umap-learn is untyped here, so pin the result to a NumPy array.
        return np.asarray(reducer.fit_transform(features))
    raise StreamlitAPIException(
        f"Unknown method {method!r} for st.chem_space. "
        "Supported methods: 'pca', 'tsne', 'umap'."
    )


class ChemSpaceMixin:
    @gather_metrics("chem_space")
    def chem_space(
        self,
        mols: Iterable[MoleculeData],
        *,  # keyword-only arguments:
        method: ChemSpaceMethod = "pca",
        fingerprint: FingerprintType = "morgan",
        radius: int = 2,
        n_bits: int = 2048,
        color_by: Sequence[float] | None = None,
        color_label: str = "Value",
        labels: Sequence[str] | None = None,
        height: int = 480,
        on_select: Literal["rerun", "ignore"] | WidgetCallback = "rerun",
        selection_mode: SelectionMode | Iterable[SelectionMode] = (
            "points",
            "box",
            "lasso",
        ),
        key: Key | None = None,
    ) -> PlotlyState | DeltaGenerator:
        """Display an interactive 2D map of a molecule library and return the selection.

        Each molecule is turned into a structural fingerprint and projected to
        two dimensions, then drawn as a scatter plot. Users can select points
        (click, box, or lasso); the selected indices — positions in ``mols`` —
        flow back into your script, so a downstream ``st.chem_dataframe`` or
        ``st.mol_card`` can show exactly the molecules they picked.

        This command renders with ``st.plotly_chart`` and therefore requires the
        optional ``plotly`` package.

        Parameters
        ----------
        mols : Iterable of str or rdkit.Chem.Mol
            The molecule library to project, as SMILES strings or
            ``rdkit.Chem.Mol`` objects.

        method : "pca", "tsne", or "umap"
            The dimensionality-reduction method used to place points. ``"pca"``
            (default) is dependency-free. ``"tsne"`` requires ``scikit-learn``
            and ``"umap"`` requires ``umap-learn``; both are optional installs.

        fingerprint : "morgan" or "rdkit"
            The fingerprint family used to encode structure. ``"morgan"``
            (default) is an ECFP-like circular fingerprint controlled by
            ``radius``; ``"rdkit"`` is the RDKit path-based fingerprint.

        radius : int
            The neighborhood radius for Morgan fingerprints. Ignored for the
            ``"rdkit"`` fingerprint. Defaults to ``2``.

        n_bits : int
            The fingerprint length in bits. Defaults to ``2048``.

        color_by : Sequence of float or None
            An optional per-molecule numeric value (e.g. an activity like
            pIC50) used to color the points on a continuous scale. Must be the
            same length as ``mols``. If this is ``None`` (default), all points
            share one color.

        color_label : str
            The label shown on the color scale when ``color_by`` is provided.
            Defaults to ``"Value"``.

        labels : Sequence of str or None
            An optional per-molecule label (e.g. a compound name) shown on hover.
            Must be the same length as ``mols``.

        height : int
            The height of the plot in pixels. Defaults to ``480``.

        on_select : "rerun", "ignore", or callable
            How the app responds when the user selects points. ``"rerun"``
            (default) reruns the script with the new selection. ``"ignore"``
            renders a static plot and returns a ``DeltaGenerator``. A callable
            runs as a callback before the rerun.

        selection_mode : "points", "box", "lasso", or an Iterable of these
            Which selection tools are enabled. Defaults to all three.

        key : str, int, or None
            An optional key that uniquely identifies this widget, forwarded to
            the underlying ``st.plotly_chart``.

        Returns
        -------
        PlotlyState or DeltaGenerator
            When ``on_select`` is active, a dictionary-like selection state whose
            ``selection.point_indices`` are the positions of the selected
            molecules in ``mols``. When ``on_select="ignore"``, a
            ``DeltaGenerator``.

        Examples
        --------
        >>> import streamlit as st
        >>>
        >>> mols = ["c1ccccc1O", "c1ccccc1N", "c1ccccc1C", "CCO", "CCN"]
        >>> event = st.chem_space(mols, color_by=[6.1, 5.4, 7.2, 4.0, 4.3])
        >>> st.write("Selected indices:", event.selection.point_indices)

        """
        mol_list = [mol_utils.to_mol(mol) for mol in mols]
        n_mols = len(mol_list)
        if n_mols == 0:
            raise StreamlitAPIException(
                "st.chem_space requires at least one molecule, but got an empty "
                "collection."
            )
        if color_by is not None and len(color_by) != n_mols:
            raise StreamlitAPIException(
                f"color_by has {len(color_by)} values but there are {n_mols} "
                "molecules; they must be the same length."
            )
        if labels is not None and len(labels) != n_mols:
            raise StreamlitAPIException(
                f"labels has {len(labels)} values but there are {n_mols} "
                "molecules; they must be the same length."
            )

        features = mol_utils.compute_fingerprints(
            mol_list, fingerprint=fingerprint, radius=radius, n_bits=n_bits
        )
        coords = _reduce_to_2d(features, method)

        figure = _build_figure(
            coords,
            color_by=color_by,
            color_label=color_label,
            labels=labels,
            method=method,
            height=height,
        )
        return self.dg.plotly_chart(
            figure,
            on_select=on_select,
            selection_mode=selection_mode,
            key=key,
        )

    @property
    def dg(self) -> DeltaGenerator:
        """The associated DeltaGenerator."""
        return cast("DeltaGenerator", self)


def _build_figure(
    coords: np.ndarray,
    *,
    color_by: Sequence[float] | None,
    color_label: str,
    labels: Sequence[str] | None,
    method: ChemSpaceMethod,
    height: int,
) -> Any:
    """Build the Plotly scatter figure for the projected molecule coordinates.

    A single scatter trace holds every molecule so that a selection's
    ``point_indices`` line up one-to-one with positions in the input library.
    """
    try:
        import plotly.graph_objects as go
    except ImportError as error:  # pragma: no cover - optional dep
        raise StreamlitAPIException(
            "st.chem_space requires the plotly package. Install it with "
            "`pip install plotly`."
        ) from error

    marker: dict[str, Any] = {"size": 9}
    if color_by is not None:
        marker.update(
            color=list(color_by),
            colorscale="Viridis",
            showscale=True,
            colorbar={"title": color_label},
        )

    scatter = go.Scattergl(
        x=coords[:, 0],
        y=coords[:, 1],
        mode="markers",
        marker=marker,
        text=list(labels) if labels is not None else None,
        hovertemplate=(
            "%{text}<extra></extra>" if labels is not None else "point %{pointNumber}"
        ),
    )
    figure = go.Figure(data=[scatter])
    # The projected axes carry no physical units, so hide the tick labels and
    # keep the frame minimal — the map is about relative position, not values.
    axis = {"showticklabels": False, "zeroline": False}
    figure.update_layout(
        height=height,
        margin={"l": 10, "r": 10, "t": 30, "b": 10},
        xaxis={**axis, "title": f"{method.upper()} 1"},
        yaxis={**axis, "title": f"{method.upper()} 2"},
        dragmode="lasso",
    )
    return figure
