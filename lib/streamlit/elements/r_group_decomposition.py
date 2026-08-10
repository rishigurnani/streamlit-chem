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

"""Streamlit support for R-group decomposition tables.

``st.r_group_decomposition`` breaks a molecule series apart around a shared
scaffold and lays the fragments out in a grid: one row per molecule, one column
per R-group position, every cell a rendered 2D structure. It composes the
Mol-core (``mol_utils.decompose_r_groups`` for the chemistry,
``mol_utils.mol_to_svg_data_uri`` for the pictures) with ``st.dataframe`` image
columns, and returns the decomposition as a ``Mol``-valued DataFrame for further
SAR analysis.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, cast

from streamlit.elements.lib import mol_utils
from streamlit.elements.lib.column_types import ImageColumn
from streamlit.errors import StreamlitAPIException
from streamlit.runtime.metrics_util import gather_metrics

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    import pandas as pd
    from rdkit.Chem import Mol

    from streamlit.delta_generator import DeltaGenerator
    from streamlit.elements.lib.mol_utils import MoleculeData, SubstructureQuery


class RGroupDecompositionMixin:
    @gather_metrics("r_group_decomposition")
    def r_group_decomposition(
        self,
        core: SubstructureQuery,
        mols: Iterable[MoleculeData],
        *,  # keyword-only arguments:
        labels: Sequence[str] | None = None,
        label_column: str = "Molecule",
        mol_image_width: int = 150,
        mol_image_height: int = 100,
        display: bool = True,
    ) -> pd.DataFrame:
        """Decompose a molecule series around a shared core and show the R-groups.

        Each molecule that matches ``core`` becomes a row; the core and every
        R-group position (``R1``, ``R2``, ...) become columns of rendered 2D
        structures. This is a thin composition over ``st.dataframe`` (via image
        columns) and the RDKit Mol-core.

        Parameters
        ----------
        core : str or rdkit.Chem.Mol
            The shared scaffold to decompose around, as a SMILES/SMARTS string
            or an ``rdkit.Chem.Mol`` object. Molecules that do not contain the
            core are skipped.

        mols : Iterable of str or rdkit.Chem.Mol
            The molecule series to decompose, as SMILES strings or
            ``rdkit.Chem.Mol`` objects.

        labels : Sequence of str or None
            An optional per-molecule label (e.g. a compound name) shown in a
            leading column. Must be the same length as ``mols``. If this is
            ``None`` (default), no label column is shown.

        label_column : str
            The header for the label column when ``labels`` is provided.
            Defaults to ``"Molecule"``.

        mol_image_width : int
            The pixel width of each rendered fragment. Defaults to ``150``.

        mol_image_height : int
            The pixel height of each rendered fragment. Defaults to ``100``.

        display : bool
            Whether to render the decomposition as a dataframe. If this is
            ``False``, the table is not shown and only the DataFrame is
            returned. Defaults to ``True``.

        Returns
        -------
        pandas.DataFrame
            The decomposition, with one row per matched molecule (indexed by its
            position in ``mols``) and ``rdkit.Chem.Mol`` values in the ``Core``
            and ``R#`` columns. The optional label column holds the matching
            entries from ``labels``. Empty when no molecule matches the core.

        Examples
        --------
        >>> import streamlit as st
        >>>
        >>> mols = ["c1ccccc1O", "c1ccccc1N", "c1ccccc1CC"]
        >>> table = st.r_group_decomposition(
        ...     "c1ccccc1", mols, labels=["Phenol", "Aniline", "Ethylbenzene"]
        ... )
        >>> st.write("Decomposed", len(table), "molecules")

        """

        core_mol = mol_utils.to_mol(core)
        mol_list = [mol_utils.to_mol(mol) for mol in mols]
        if not mol_list:
            raise StreamlitAPIException(
                "st.r_group_decomposition requires at least one molecule, but got "
                "an empty collection."
            )
        if labels is not None and len(labels) != len(mol_list):
            raise StreamlitAPIException(
                f"labels has {len(labels)} values but there are {len(mol_list)} "
                "molecules; they must be the same length."
            )

        rows, unmatched = mol_utils.decompose_r_groups(mol_list, core_mol)
        # RGroupDecompose reports the indices that did not match; the remaining
        # positions align, in order, with the rows it returned.
        unmatched_set = set(unmatched)
        matched_indices = [i for i in range(len(mol_list)) if i not in unmatched_set]

        table = _build_dataframe(rows, matched_indices, labels, label_column)
        if display:
            self._render(table, label_column, mol_image_width, mol_image_height)
        return table

    def _render(
        self,
        table: pd.DataFrame,
        label_column: str,
        mol_image_width: int,
        mol_image_height: int,
    ) -> None:
        """Render the decomposition table with each fragment column as an image."""
        if table.empty:
            self.dg.info(
                "No molecules matched the provided core, so there is nothing to "
                "decompose."
            )
            return

        rendered = table.copy()
        column_config: dict[Any, Any] = {}
        for column in table.columns:
            if column == label_column:
                continue
            rendered[column] = [
                _render_fragment(value, mol_image_width, mol_image_height)
                for value in table[column]
            ]
            column_config[column] = ImageColumn(label=column)
        self.dg.dataframe(rendered, column_config=column_config)

    @property
    def dg(self) -> DeltaGenerator:
        """The associated DeltaGenerator."""
        return cast("DeltaGenerator", self)


def _render_fragment(value: object, width: int, height: int) -> str:
    """Render one R-group fragment to an SVG data URI.

    RDKit fills empty R-group positions with an explicit-hydrogen ``Mol`` rather
    than leaving them blank, so every cell normally renders; the missing-value
    guard is defensive against a ``None``/``NaN`` slipping through.
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""  # pragma: no cover - defensive
    return mol_utils.mol_to_svg_data_uri(cast("Mol", value), width=width, height=height)


def _build_dataframe(
    rows: list[dict[str, Mol]],
    matched_indices: list[int],
    labels: Sequence[str] | None,
    label_column: str,
) -> pd.DataFrame:
    """Assemble the decomposition rows into a Mol-valued DataFrame."""
    import pandas as pd

    if not rows:
        return pd.DataFrame()

    records: list[dict[str, object]] = []
    for original_index, fragments in zip(matched_indices, rows, strict=True):
        record: dict[str, object] = {}
        if labels is not None:
            record[label_column] = labels[original_index]
        record.update(fragments)
        records.append(record)
    return pd.DataFrame(records, index=matched_indices)
