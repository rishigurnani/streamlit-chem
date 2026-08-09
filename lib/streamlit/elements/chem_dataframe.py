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

"""Streamlit support for interactive dataframes with rendered molecular structures."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, cast

from streamlit.elements.lib import mol_utils
from streamlit.elements.lib.column_types import ImageColumn
from streamlit.errors import StreamlitAPIException
from streamlit.runtime.metrics_util import gather_metrics

if TYPE_CHECKING:
    import pandas as pd

    from streamlit.delta_generator import DeltaGenerator
    from streamlit.elements.arrow import DataframeState
    from streamlit.elements.lib.column_config_utils import ColumnConfigMappingInput
    from streamlit.elements.lib.mol_utils import MoleculeData, SubstructureQuery


def _render_cell(
    value: object,
    highlight_substructure: SubstructureQuery | None,
    width: int,
    height: int,
) -> str:
    """Render a single molecule cell to an SVG data URI (empty string if missing)."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""

    mol = mol_utils.to_mol(cast("MoleculeData", value))
    highlight_atoms: list[int] = []
    highlight_bonds: list[int] = []
    if highlight_substructure is not None:
        highlight_atoms, highlight_bonds = mol_utils.get_substructure_match(
            mol, highlight_substructure
        )
    return mol_utils.mol_to_svg_data_uri(
        mol,
        width=width,
        height=height,
        highlight_atoms=highlight_atoms,
        highlight_bonds=highlight_bonds,
    )


class ChemDataFrameMixin:
    @gather_metrics("chem_dataframe")
    def chem_dataframe(
        self,
        data: pd.DataFrame,
        *,  # keyword-only arguments:
        mol_column: str = "Mol",
        highlight_substructure: SubstructureQuery | None = None,
        mol_image_width: int = 150,
        mol_image_height: int = 100,
        column_config: ColumnConfigMappingInput | None = None,
        **kwargs: Any,
    ) -> DeltaGenerator | DataframeState:
        """Display an interactive dataframe with auto-rendered 2D molecular structures.

        This is a thin, chemistry-aware wrapper around ``st.dataframe``. The
        molecule column is rendered server-side with RDKit and shown as inline 2D
        structures via an image column; every other column, along with sorting,
        searching, and row selection, behaves exactly like ``st.dataframe``.

        Parameters
        ----------
        data : pandas.DataFrame
            The dataframe to display. It must contain ``mol_column``.

        mol_column : str
            The name of the column holding the molecules to render. Cells may be
            SMILES strings or ``rdkit.Chem.Mol`` objects. Missing values (``None``
            or ``NaN``) render as empty cells. Defaults to ``"Mol"``.

        highlight_substructure : str, rdkit.Chem.Mol, or None
            An optional substructure to highlight in every rendered structure. This
            can be a SMARTS/SMILES string or an ``rdkit.Chem.Mol`` object. Cells
            without a match are drawn without highlighting.

        mol_image_width : int
            The pixel width of each rendered structure. Defaults to ``150``.

        mol_image_height : int
            The pixel height of each rendered structure. Defaults to ``100``.

        column_config : dict or None
            Column configuration forwarded to ``st.dataframe``, letting you
            configure the non-molecule columns. If you don't configure
            ``mol_column`` yourself, it is configured as an image column
            automatically.

        **kwargs : Any
            Additional keyword arguments forwarded verbatim to ``st.dataframe``
            (e.g. ``hide_index``, ``on_select``, ``selection_mode``, ``key``,
            ``use_container_width``, ``width``, ``height``).

        Returns
        -------
        element or dict
            Whatever ``st.dataframe`` returns for the given arguments: a
            placeholder container by default, or the selection state when
            ``on_select`` is used.

        Examples
        --------
        >>> import pandas as pd
        >>> import streamlit as st
        >>>
        >>> df = pd.DataFrame(
        ...     {
        ...         "Name": ["Aspirin", "Caffeine"],
        ...         "Mol": ["CC(=O)Oc1ccccc1C(=O)O", "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"],
        ...     }
        ... )
        >>> st.chem_dataframe(df, mol_column="Mol", highlight_substructure="c1ccccc1")

        """
        import pandas as pd

        if not isinstance(data, pd.DataFrame):
            raise StreamlitAPIException(
                "st.chem_dataframe requires a pandas DataFrame, but got "
                f"{type(data).__name__}."
            )
        if mol_column not in data.columns:
            raise StreamlitAPIException(
                f"Molecule column {mol_column!r} was not found in the dataframe. "
                f"Available columns: {list(data.columns)}."
            )

        rendered = data.copy()
        rendered[mol_column] = [
            _render_cell(
                value, highlight_substructure, mol_image_width, mol_image_height
            )
            for value in data[mol_column]
        ]

        # Default the molecule column to an image column, but let an explicit
        # user-provided config for that column win.
        merged_config: dict[Any, Any] = dict(column_config) if column_config else {}
        merged_config.setdefault(mol_column, ImageColumn(label=mol_column))

        # The dataframe() overloads can't be resolved through **kwargs, so the
        # return type degrades to Any; restore it with an explicit cast.
        result = self.dg.dataframe(rendered, column_config=merged_config, **kwargs)
        return cast("DeltaGenerator | DataframeState", result)

    @property
    def dg(self) -> DeltaGenerator:
        """The associated DeltaGenerator."""
        return cast("DeltaGenerator", self)
