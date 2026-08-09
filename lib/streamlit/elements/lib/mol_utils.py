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

"""Shared cheminformatics helpers backing ChemLit's native chemical elements.

This module is the single home for RDKit interop: coercing user input into an
``rdkit.Chem.Mol``, computing substructure matches, and rendering a molecule to
a 2D SVG. Every chemical element is expected to build on these primitives
(``st.molecule`` today; ``st.chem_dataframe``, ``st.smarts_input`` and
``st.mol_card`` next), so the parsing, matching, and drawing behavior stays
consistent across the whole ChemLit surface and lives in exactly one place.
"""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Final, TypeAlias, Union

from streamlit.errors import StreamlitAPIException

if TYPE_CHECKING:
    from rdkit.Chem import Mol

# A molecule the user hands us: either a live RDKit Mol or a SMILES string.
MoleculeData: TypeAlias = Union["Mol", str]

# A substructure query: either a live RDKit Mol or a SMARTS/SMILES pattern.
SubstructureQuery: TypeAlias = Union["Mol", str]

# Default pixel canvas for 2D rendering when the caller doesn't pin an explicit
# integer size. Chosen to look balanced for a single small-molecule structure.
_DEFAULT_RENDER_WIDTH: Final = 450
_DEFAULT_RENDER_HEIGHT: Final = 350


def _is_mol(obj: object) -> bool:
    """Return whether ``obj`` is an ``rdkit.Chem.Mol`` without importing RDKit eagerly."""
    from rdkit.Chem import Mol

    return isinstance(obj, Mol)


def to_mol(data: MoleculeData) -> Mol:
    """Coerce ``data`` into an ``rdkit.Chem.Mol``.

    Accepts a live ``Mol`` (returned as-is) or a SMILES string (parsed).
    Raises ``StreamlitAPIException`` for unparseable SMILES or unsupported types.
    """
    from rdkit import Chem

    if isinstance(data, str):
        mol = Chem.MolFromSmiles(data)
        if mol is None:
            raise StreamlitAPIException(
                f"Could not parse molecule from SMILES string: {data!r}. "
                "Provide a valid SMILES string or an `rdkit.Chem.Mol` object."
            )
        return mol
    if _is_mol(data):
        return data
    raise StreamlitAPIException(
        "Molecule must be a SMILES string or an `rdkit.Chem.Mol` object, "
        f"but got {type(data).__name__}."
    )


def to_query(query: SubstructureQuery) -> Mol:
    """Coerce ``query`` into a query ``Mol`` for substructure matching.

    A string is parsed as SMARTS (which also accepts SMILES-style patterns).
    Raises ``StreamlitAPIException`` for unparseable patterns or unsupported types.
    """
    from rdkit import Chem

    if isinstance(query, str):
        query_mol = Chem.MolFromSmarts(query)
        if query_mol is None:
            raise StreamlitAPIException(
                f"Could not parse substructure query from SMARTS string: {query!r}. "
                "Provide a valid SMARTS/SMILES string or an `rdkit.Chem.Mol` object."
            )
        return query_mol
    if _is_mol(query):
        return query
    raise StreamlitAPIException(
        "Substructure query must be a SMARTS/SMILES string or an "
        f"`rdkit.Chem.Mol` object, but got {type(query).__name__}."
    )


def get_substructure_match(
    mol: Mol, query: SubstructureQuery
) -> tuple[list[int], list[int]]:
    """Return the atom and bond indices of the first substructure match.

    The result is ``([atom_ids], [bond_ids])`` for the first match of ``query``
    in ``mol``, or ``([], [])`` when there is no match. Bonds are included when
    both of their atoms are part of the match, so callers can highlight a whole
    matched fragment (atoms and the bonds between them) uniformly.
    """
    query_mol = to_query(query)
    atom_ids = list(mol.GetSubstructMatch(query_mol))
    if not atom_ids:
        return [], []

    matched_atoms = set(atom_ids)
    bond_ids = [
        bond.GetIdx()
        for bond in mol.GetBonds()
        if bond.GetBeginAtomIdx() in matched_atoms
        and bond.GetEndAtomIdx() in matched_atoms
    ]
    return atom_ids, bond_ids


def mol_to_svg(
    mol: Mol,
    *,
    width: int | None = None,
    height: int | None = None,
    highlight_atoms: list[int] | None = None,
    highlight_bonds: list[int] | None = None,
) -> str:
    """Render ``mol`` to a self-contained 2D SVG string via RDKit.

    ``width``/``height`` set the pixel canvas (defaulting to a balanced size for
    a single structure). ``highlight_atoms``/``highlight_bonds`` are drawn with
    RDKit's default highlight color, typically the output of
    :func:`get_substructure_match`.
    """
    from rdkit.Chem.Draw import rdMolDraw2D

    drawer = rdMolDraw2D.MolDraw2DSVG(
        width or _DEFAULT_RENDER_WIDTH, height or _DEFAULT_RENDER_HEIGHT
    )
    rdMolDraw2D.PrepareAndDrawMolecule(
        drawer,
        mol,
        highlightAtoms=highlight_atoms or [],
        highlightBonds=highlight_bonds or [],
    )
    drawer.FinishDrawing()
    return drawer.GetDrawingText()


def mol_to_svg_data_uri(
    mol: Mol,
    *,
    width: int | None = None,
    height: int | None = None,
    highlight_atoms: list[int] | None = None,
    highlight_bonds: list[int] | None = None,
) -> str:
    """Render ``mol`` to a base64-encoded ``data:image/svg+xml`` URI.

    This is the embeddable form of a structure for image cells such as the
    ``st.column_config.ImageColumn`` cells backing :func:`st.chem_dataframe`.
    Takes the same drawing arguments as :func:`mol_to_svg`.
    """
    svg = mol_to_svg(
        mol,
        width=width,
        height=height,
        highlight_atoms=highlight_atoms,
        highlight_bonds=highlight_bonds,
    )
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"
