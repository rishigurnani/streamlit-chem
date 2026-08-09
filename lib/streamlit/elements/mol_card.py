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

"""Streamlit support for compact molecule summary cards."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, cast

from streamlit.elements.lib import mol_utils
from streamlit.runtime.metrics_util import gather_metrics

if TYPE_CHECKING:
    from collections.abc import Sequence

    from streamlit.delta_generator import DeltaGenerator
    from streamlit.elements.lib.layout_utils import Width
    from streamlit.elements.lib.mol_utils import MoleculeData, SubstructureQuery

# Per-descriptor display formats: integer counts vs. decimal-valued properties.
_DESCRIPTOR_FORMATS: Final = {
    "MW": "{:.1f}",
    "LogP": "{:.2f}",
    "TPSA": "{:.1f}",
    "HBD": "{:.0f}",
    "HBA": "{:.0f}",
    "RotB": "{:.0f}",
}
_DEFAULT_METRICS: Final = ("MW", "LogP", "TPSA", "HBD", "HBA")


class MolCardMixin:
    @gather_metrics("mol_card")
    def mol_card(
        self,
        data: MoleculeData,
        *,  # keyword-only arguments:
        title: str | None = None,
        metrics: Sequence[str] = _DEFAULT_METRICS,
        show_ro5: bool = True,
        highlight_substructure: SubstructureQuery | None = None,
        mol_image_width: int = 250,
        mol_image_height: int = 180,
        width: Width = "content",
    ) -> DeltaGenerator:
        """Display a compact summary card for a single molecule.

        The card composes ``st.molecule`` with physicochemical ``st.metric``
        values and a Lipinski rule-of-five badge inside a bordered container.

        Parameters
        ----------
        data : str or rdkit.Chem.Mol
            The molecule to summarize, as a SMILES string or an
            ``rdkit.Chem.Mol`` object.

        title : str or None
            An optional caption shown beneath the structure, such as a compound
            name.

        metrics : sequence of str
            The physicochemical descriptors to display as metrics. Supported
            values are ``"MW"``, ``"LogP"``, ``"TPSA"``, ``"HBD"``, ``"HBA"``,
            and ``"RotB"``. Defaults to ``("MW", "LogP", "TPSA", "HBD", "HBA")``.
            Pass an empty sequence to hide the metric row.

        show_ro5 : bool
            Whether to show a Lipinski rule-of-five badge (green when the
            molecule passes with at most one violation, red otherwise). The
            specific violations are available in the badge's tooltip. Defaults to
            ``True``.

        highlight_substructure : str, rdkit.Chem.Mol, or None
            An optional substructure to highlight in the structure. This can be a
            SMARTS/SMILES string or an ``rdkit.Chem.Mol`` object.

        mol_image_width : int
            The pixel width of the rendered structure. Defaults to ``250``.

        mol_image_height : int
            The pixel height of the rendered structure. Defaults to ``180``.

        width : "content", "stretch", or int
            The width of the card container, forwarded to ``st.container``.
            Defaults to ``"content"``.

        Returns
        -------
        DeltaGenerator
            The card container, so you can add more content to it.

        Examples
        --------
        >>> import streamlit as st
        >>>
        >>> st.mol_card(
        ...     "CC(=O)Oc1ccccc1C(=O)O",
        ...     title="Aspirin",
        ...     metrics=["MW", "LogP", "TPSA", "HBD", "HBA"],
        ... )

        """
        mol = mol_utils.to_mol(data)
        metric_names = list(metrics)
        values = mol_utils.compute_descriptors(mol, metric_names)

        card = self.dg.container(border=True, width=width)
        card.molecule(
            mol,
            caption=title,
            highlight_substructure=highlight_substructure,
            width=mol_image_width,
            height=mol_image_height,
        )

        if metric_names:
            # A horizontal flex row lets each metric size to its content (and
            # wrap) rather than forcing equal, narrow columns that truncate the
            # values in a content-width card.
            metric_row = card.container(horizontal=True)
            for name in metric_names:
                value_format = _DESCRIPTOR_FORMATS.get(name, "{:.2f}")
                metric_row.metric(
                    name, value_format.format(values[name]), width="content"
                )

        if show_ro5:
            violations = mol_utils.lipinski_violations(mol)
            if len(violations) <= 1:
                card.badge(
                    "Rule of 5: Pass",
                    color="green",
                    icon=":material/check_circle:",
                )
            else:
                card.badge(
                    f"Rule of 5: {len(violations)} violations",
                    color="red",
                    icon=":material/cancel:",
                    help="; ".join(violations),
                )
        return card

    @property
    def dg(self) -> DeltaGenerator:
        """The associated DeltaGenerator."""
        return cast("DeltaGenerator", self)
