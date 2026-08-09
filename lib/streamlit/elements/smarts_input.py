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

"""Streamlit support for validated SMARTS/SMILES substructure query input."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from streamlit.elements.lib import mol_utils
from streamlit.errors import StreamlitAPIException
from streamlit.runtime.metrics_util import gather_metrics

if TYPE_CHECKING:
    from streamlit.delta_generator import DeltaGenerator
    from streamlit.elements.lib.mol_utils import MoleculeData
    from streamlit.elements.lib.utils import Key, LabelVisibility


class SmartsInputMixin:
    @gather_metrics("smarts_input")
    def smarts_input(
        self,
        label: str,
        value: str = "",
        *,  # keyword-only arguments:
        key: Key | None = None,
        help: str | None = None,
        placeholder: str | None = "e.g. c1ccccc1 (benzene ring)",
        preview: MoleculeData | None = None,
        disabled: bool = False,
        label_visibility: LabelVisibility = "visible",
    ) -> str | None:
        """Display a text input for a SMARTS/SMILES substructure query.

        This is a chemistry-aware wrapper around ``st.text_input`` that validates
        the entered pattern with RDKit as the user types. It returns the query
        only when it parses as valid SMARTS, so downstream code never has to
        re-validate.

        Parameters
        ----------
        label : str
            A short label explaining what the query is for. This supports the
            same Markdown as ``st.text_input``.

        value : str
            The query shown when the input first renders. Defaults to an empty
            string.

        key : str, int, or None
            An optional key that uniquely identifies this widget, forwarded to
            the underlying ``st.text_input``.

        help : str or None
            An optional tooltip shown next to the label.

        placeholder : str or None
            Placeholder text shown while the input is empty. Defaults to a
            benzene-ring example.

        preview : str, rdkit.Chem.Mol, or None
            An optional molecule (SMILES string or ``rdkit.Chem.Mol``) to render
            beneath the input with the current query highlighted. This gives a
            live view of what the query matches. If this is ``None`` (default),
            no preview is shown.

        disabled : bool
            Whether to disable the input. Defaults to ``False``.

        label_visibility : "visible", "hidden", or "collapsed"
            The visibility of the label. Defaults to ``"visible"``.

        Returns
        -------
        str or None
            The entered query when it is a valid SMARTS pattern, or ``None`` when
            the input is empty or the pattern cannot be parsed. When the pattern
            is invalid, an inline validation message is shown below the input.

        Examples
        --------
        >>> import streamlit as st
        >>>
        >>> query = st.smarts_input(
        ...     "Substructure query",
        ...     value="c1ccccc1",
        ...     preview="CC(=O)Oc1ccccc1C(=O)O",
        ... )
        >>> if query:
        ...     st.write("Valid query:", query)

        """
        raw = self.dg.text_input(
            label,
            value=value,
            key=key,
            help=help,
            placeholder=placeholder,
            disabled=disabled,
            label_visibility=label_visibility,
        )
        if not raw:
            return None

        try:
            mol_utils.to_query(raw)
        except StreamlitAPIException as error:
            # Inline, low-key validation feedback rather than a blocking error.
            self.dg.caption(f":red[:material/error: {error}]")
            return None

        if preview is not None:
            self.dg.molecule(preview, highlight_substructure=raw, caption="Preview")
        return raw

    @property
    def dg(self) -> DeltaGenerator:
        """The associated DeltaGenerator."""
        return cast("DeltaGenerator", self)
