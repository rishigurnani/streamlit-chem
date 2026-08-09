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

"""Streamlit support for rendering RDKit molecules as native 2D structures."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from streamlit.elements.lib import mol_utils
from streamlit.elements.lib.layout_utils import create_layout_config
from streamlit.proto.Molecule_pb2 import Molecule as MoleculeProto
from streamlit.runtime.metrics_util import gather_metrics

if TYPE_CHECKING:
    from streamlit.delta_generator import DeltaGenerator
    from streamlit.elements.lib.layout_utils import Height, Width
    from streamlit.elements.lib.mol_utils import MoleculeData, SubstructureQuery


class MoleculeMixin:
    @gather_metrics("molecule")
    def molecule(
        self,
        data: MoleculeData,
        *,  # keyword-only arguments:
        caption: str | None = None,
        highlight_substructure: SubstructureQuery | None = None,
        width: Width = "content",
        height: Height = "content",
    ) -> DeltaGenerator:
        """Display a molecule as a native 2D chemical structure.

        The structure is rendered server-side with RDKit and sent to the browser
        as a self-contained SVG, so no third-party JavaScript viewer or iframe is
        involved.

        Parameters
        ----------
        data : str or rdkit.Chem.Mol
            The molecule to display. This can be one of the following:

            - A SMILES string (e.g. ``"c1ccccc1O"`` for phenol).
            - An ``rdkit.Chem.Mol`` object.

        caption : str or None
            An optional caption shown beneath the structure, such as a compound
            name or identifier.

        highlight_substructure : str, rdkit.Chem.Mol, or None
            An optional substructure to highlight within the molecule. This can
            be a SMARTS/SMILES string or an ``rdkit.Chem.Mol`` object. The first
            match is highlighted; if there is no match, nothing is highlighted.

        width : "content", "stretch", or int
            The width of the molecule element. This can be one of the following:

            - ``"content"`` (default): The width of the element matches the
              width of its content, but doesn't exceed the width of the parent
              container.
            - ``"stretch"``: The width of the element matches the width of the
              parent container.
            - An integer specifying the width in pixels: The element has a fixed
              width. The structure is also rendered on a canvas of this pixel
              width.

        height : "content", "stretch", or int
            The height of the molecule element. This can be one of the following:

            - ``"content"`` (default): The height of the element matches the
              height of its content.
            - ``"stretch"``: The height of the element matches the height of its
              content or the height of the parent container, whichever is larger.
            - An integer specifying the height in pixels: The element has a fixed
              height. The structure is also rendered on a canvas of this pixel
              height.

        Returns
        -------
        DeltaGenerator
            The container that holds the rendered molecule.

        Examples
        --------
        >>> import streamlit as st
        >>>
        >>> st.molecule("CC(=O)Oc1ccccc1C(=O)O", caption="Aspirin")

        Highlight a substructure by passing a SMARTS/SMILES query:

        >>> import streamlit as st
        >>>
        >>> st.molecule(
        ...     "CC(=O)Oc1ccccc1C(=O)O",
        ...     caption="Aspirin",
        ...     highlight_substructure="c1ccccc1",
        ... )

        """
        mol = mol_utils.to_mol(data)

        highlight_atoms: list[int] = []
        highlight_bonds: list[int] = []
        if highlight_substructure is not None:
            highlight_atoms, highlight_bonds = mol_utils.get_substructure_match(
                mol, highlight_substructure
            )

        molecule_proto = MoleculeProto()
        molecule_proto.svg = mol_utils.mol_to_svg(
            mol,
            width=width if isinstance(width, int) else None,
            height=height if isinstance(height, int) else None,
            highlight_atoms=highlight_atoms,
            highlight_bonds=highlight_bonds,
        )
        if caption is not None:
            molecule_proto.caption = caption

        layout_config = create_layout_config(
            width=width,
            height=height,
            allow_content_width=True,
            allow_content_height=True,
        )

        return self.dg._enqueue("molecule", molecule_proto, layout_config=layout_config)

    @property
    def dg(self) -> DeltaGenerator:
        """The associated DeltaGenerator."""
        return cast("DeltaGenerator", self)
