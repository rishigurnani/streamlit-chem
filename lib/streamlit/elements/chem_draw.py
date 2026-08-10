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

"""Streamlit support for an interactive 2D molecule editor (powered by Ketcher)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, Literal, cast, overload

from streamlit.elements.lib import mol_utils
from streamlit.errors import StreamlitAPIException
from streamlit.runtime.metrics_util import gather_metrics

if TYPE_CHECKING:
    from rdkit.Chem import Mol

    from streamlit.delta_generator import DeltaGenerator
    from streamlit.elements.lib.mol_utils import MoleculeData

_KETCHER_INSTALL_HINT: Final = (
    "`st.chem_draw` requires the `streamlit-ketcher` package, which provides the "
    "Ketcher editor. Install it with `pip install streamlit-ketcher`."
)


class ChemDrawMixin:
    @overload
    def chem_draw(
        self,
        value: MoleculeData | None = None,
        *,
        height: int = 400,
        return_type: Literal["mol"] = "mol",
        key: str | None = None,
    ) -> Mol | None: ...

    @overload
    def chem_draw(
        self,
        value: MoleculeData | None = None,
        *,
        height: int = 400,
        return_type: Literal["smiles"],
        key: str | None = None,
    ) -> str | None: ...

    @gather_metrics("chem_draw")
    def chem_draw(
        self,
        value: MoleculeData | None = None,
        *,
        height: int = 400,
        return_type: Literal["mol", "smiles"] = "mol",
        key: str | None = None,
    ) -> Mol | str | None:
        """Display an interactive 2D structure editor and return the drawn molecule.

        This wraps the `Ketcher <https://lifescience.opensource.epam.com/ketcher/>`_
        editor and hands the drawn structure straight back to Python as an
        ``rdkit.Chem.Mol`` (or a SMILES string), so no manual SMILES round-tripping
        is needed.

        .. Important::
            You must install ``streamlit-ketcher`` to use this command:

            .. code-block:: shell

               pip install streamlit-ketcher

        Parameters
        ----------
        value : str, rdkit.Chem.Mol, or None
            The molecule the editor starts with, as a SMILES string or an
            ``rdkit.Chem.Mol`` object. If this is ``None`` (default), the editor
            starts empty.

        height : int
            The height of the editor in pixels. Defaults to ``400``.

        return_type : "mol" or "smiles"
            The type to return the drawn molecule as. If this is ``"mol"``
            (default), an ``rdkit.Chem.Mol`` is returned. If this is
            ``"smiles"``, the canonical SMILES string is returned.

        key : str or None
            An optional key that uniquely identifies this widget. If this is
            ``None``, the widget is re-mounted (and loses its drawn state)
            whenever its arguments change.

        Returns
        -------
        rdkit.Chem.Mol, str, or None
            The drawn molecule as the requested ``return_type``, or ``None`` while
            the editor is empty.

        Examples
        --------
        >>> import streamlit as st
        >>> from rdkit.Chem import Descriptors
        >>>
        >>> mol = st.chem_draw("c1ccccc1O")
        >>> if mol is not None:
        ...     st.metric("Molecular weight", f"{Descriptors.MolWt(mol):.1f}")

        """
        try:
            from streamlit_ketcher import st_ketcher
        except ImportError as error:  # pragma: no cover - optional dependency
            raise StreamlitAPIException(_KETCHER_INSTALL_HINT) from error

        if return_type not in {"mol", "smiles"}:
            raise StreamlitAPIException(
                f"Invalid return_type {return_type!r} for st.chem_draw. "
                "Use 'mol' or 'smiles'."
            )

        # Ketcher exchanges structures as SMILES, so seed it with a SMILES string.
        initial_smiles = "" if value is None else mol_utils.to_smiles(value)

        edited_smiles: str = st_ketcher(initial_smiles, height=height, key=key)
        if not edited_smiles:
            return None
        if return_type == "smiles":
            return edited_smiles
        return mol_utils.to_mol(edited_smiles)

    @property
    def dg(self) -> DeltaGenerator:
        """The associated DeltaGenerator."""
        return cast("DeltaGenerator", self)
