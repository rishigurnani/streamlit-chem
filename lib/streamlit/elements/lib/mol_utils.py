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

"""Shared cheminformatics helpers backing streamlit-chem's native chemical elements.

This module is the single home for RDKit interop: coercing user input into an
``rdkit.Chem.Mol``, computing substructure matches, and rendering a molecule to
a 2D SVG. Every chemical element is expected to build on these primitives
(``st.molecule`` today; ``st.chem_dataframe``, ``st.smarts_input`` and
``st.mol_card`` next), so the parsing, matching, and drawing behavior stays
consistent across the whole streamlit-chem surface and lives in exactly one place.
"""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any, Final, Literal, TypeAlias, Union

from streamlit.errors import StreamlitAPIException

if TYPE_CHECKING:
    from collections.abc import Iterable

    import numpy as np
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


def _looks_like_molblock(text: str) -> bool:
    """Return whether ``text`` looks like a MOL block rather than a SMILES string.

    A MOL/SDF block carries a version tag (``V2000``/``V3000``) on its counts
    line; a SMILES string never does. This lets a single string argument accept
    either format without a separate parameter.
    """
    return "V2000" in text or "V3000" in text


def to_mol(data: MoleculeData) -> Mol:
    """Coerce ``data`` into an ``rdkit.Chem.Mol``.

    Accepts a live ``Mol`` (returned as-is), a SMILES string, or a MOL block
    (auto-detected). Raises ``StreamlitAPIException`` for unparseable input or
    unsupported types.
    """
    from rdkit import Chem

    if isinstance(data, str):
        if _looks_like_molblock(data):
            # Keep explicit hydrogens so a 3D MOL block round-trips faithfully.
            mol = Chem.MolFromMolBlock(data, removeHs=False)
            if mol is None:
                raise StreamlitAPIException(
                    "Could not parse molecule from the provided MOL block. "
                    "Provide a valid MOL block, SMILES string, or "
                    "`rdkit.Chem.Mol` object."
                )
            return mol
        mol = Chem.MolFromSmiles(data)
        if mol is None:
            raise StreamlitAPIException(
                f"Could not parse molecule from SMILES string: {data!r}. "
                "Provide a valid SMILES string, MOL block, or "
                "`rdkit.Chem.Mol` object."
            )
        return mol
    if _is_mol(data):
        return data
    raise StreamlitAPIException(
        "Molecule must be a SMILES string, MOL block, or `rdkit.Chem.Mol` "
        f"object, but got {type(data).__name__}."
    )


def to_smiles(data: MoleculeData) -> str:
    """Return the canonical SMILES string for ``data`` (a SMILES string or Mol)."""
    from rdkit import Chem

    return Chem.MolToSmiles(to_mol(data))


def to_molblock_3d(data: MoleculeData, *, generate_3d: bool = True) -> str:
    """Return a 3D MOL block for ``data`` (a SMILES string or Mol).

    When ``generate_3d`` is ``True`` (default), a 3D conformer is embedded with
    RDKit's ETKDG algorithm and refined with the MMFF force field (falling back
    to UFF when MMFF parameters are unavailable), so a bare SMILES string or a
    flat 2D molecule becomes a viewable 3D structure. When ``generate_3d`` is
    ``False``, an existing conformer is serialized as-is without re-embedding.

    Embedding is expensive, so callers that render the same molecule repeatedly
    should wrap this in ``@st.cache_data``; it is a pure function of the input.
    """
    from rdkit import Chem
    from rdkit.Chem import AllChem

    # RDKit attaches the embedding/optimization helpers to AllChem dynamically,
    # so they aren't visible to static type checkers; treat it as untyped here.
    all_chem: Any = AllChem

    mol = to_mol(data)

    # Serialize an existing conformer untouched when the caller opts out of
    # embedding. With no conformer there is nothing 3D to show, so we still fall
    # through to embedding below.
    if not generate_3d and mol.GetNumConformers() > 0:
        return Chem.MolToMolBlock(mol)

    # Explicit hydrogens give the force field a complete molecule to optimize;
    # they are the standard input for a chemically sensible 3D embedding.
    mol_with_hs = Chem.AddHs(mol)
    # Pin the embedding's random seed so the same molecule always yields the same
    # coordinates. Streamlit reruns must be deterministic (a widget's identity is
    # derived from its serialized value), and a fixed seed also makes the output
    # cacheable and reproducible.
    embed_params = all_chem.ETKDG()
    embed_params.randomSeed = 0xC0FFEE
    if all_chem.EmbedMolecule(mol_with_hs, embed_params) != 0:
        raise StreamlitAPIException(
            "Could not generate a 3D conformer for the molecule. "
            "Some structures cannot be embedded in 3D by RDKit."
        )
    # MMFF covers most drug-like molecules; UFF is the broader fallback for
    # elements or valences MMFF lacks parameters for.
    if all_chem.MMFFOptimizeMolecule(mol_with_hs) == -1:
        all_chem.UFFOptimizeMolecule(mol_with_hs)
    return Chem.MolToMolBlock(mol_with_hs)


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


# Physicochemical descriptors streamlit-chem exposes, mapped to their RDKit
# implementations lazily so importing this module never imports RDKit.
SUPPORTED_DESCRIPTORS: Final = ("MW", "LogP", "TPSA", "HBD", "HBA", "RotB")


def compute_descriptors(mol: Mol, names: Iterable[str]) -> dict[str, float]:
    """Compute the named physicochemical descriptors for ``mol``.

    Supported names are the entries of :data:`SUPPORTED_DESCRIPTORS` (``"MW"``,
    ``"LogP"``, ``"TPSA"``, ``"HBD"``, ``"HBA"``, ``"RotB"``). Raises
    ``StreamlitAPIException`` for an unknown descriptor name.
    """
    from rdkit.Chem import Descriptors

    # RDKit registers descriptor functions on the Descriptors module dynamically,
    # so they aren't visible to static type checkers; treat it as untyped here.
    descriptors: Any = Descriptors
    functions = {
        "MW": descriptors.MolWt,
        "LogP": descriptors.MolLogP,
        "TPSA": descriptors.TPSA,
        "HBD": descriptors.NumHDonors,
        "HBA": descriptors.NumHAcceptors,
        "RotB": descriptors.NumRotatableBonds,
    }
    values: dict[str, float] = {}
    for name in names:
        if name not in functions:
            raise StreamlitAPIException(
                f"Unknown molecular descriptor {name!r}. "
                f"Supported descriptors: {', '.join(SUPPORTED_DESCRIPTORS)}."
            )
        values[name] = float(functions[name](mol))
    return values


# Lipinski "rule of five" thresholds; a drug-like molecule breaches at most one.
_LIPINSKI_RULES: Final = (
    ("MW", 500.0, "MW > 500"),
    ("LogP", 5.0, "LogP > 5"),
    ("HBD", 5.0, "HBD > 5"),
    ("HBA", 10.0, "HBA > 10"),
)


def lipinski_violations(mol: Mol) -> list[str]:
    """Return the Lipinski rule-of-five violations for ``mol``.

    Each element describes a breached threshold. An empty list means the
    molecule passes all four rules; the rule of five tolerates at most one
    violation for drug-likeness.
    """
    values = compute_descriptors(mol, [name for name, _, _ in _LIPINSKI_RULES])
    return [
        message
        for name, threshold, message in _LIPINSKI_RULES
        if values[name] > threshold
    ]


# Fingerprint families streamlit-chem exposes for structure-similarity work (e.g. the
# chemical-space projection behind ``st.chem_space``).
FingerprintType: TypeAlias = Literal["morgan", "rdkit"]


def compute_fingerprints(
    mols: Iterable[Mol],
    *,
    fingerprint: FingerprintType = "morgan",
    radius: int = 2,
    n_bits: int = 2048,
) -> np.ndarray:
    """Compute binary structural fingerprints for ``mols`` as a NumPy matrix.

    Returns an ``(n_mols, n_bits)`` ``uint8`` array where each row is one
    molecule's fingerprint. ``fingerprint`` selects the family: ``"morgan"``
    (ECFP-like circular fingerprints, using ``radius``) or ``"rdkit"`` (the
    RDKit path-based fingerprint, which ignores ``radius``). Raises
    ``StreamlitAPIException`` for an unknown fingerprint type.
    """
    import numpy as np
    from rdkit import DataStructs
    from rdkit.Chem import rdFingerprintGenerator

    if fingerprint == "morgan":
        generator = rdFingerprintGenerator.GetMorganGenerator(
            radius=radius, fpSize=n_bits
        )
    elif fingerprint == "rdkit":
        generator = rdFingerprintGenerator.GetRDKitFPGenerator(fpSize=n_bits)
    else:
        raise StreamlitAPIException(
            f"Unknown fingerprint type {fingerprint!r}. "
            "Supported fingerprints: 'morgan', 'rdkit'."
        )

    rows: list[np.ndarray] = []
    for mol in mols:
        row = np.zeros((n_bits,), dtype=np.uint8)
        DataStructs.ConvertToNumpyArray(generator.GetFingerprint(mol), row)
        rows.append(row)

    if not rows:
        return np.empty((0, n_bits), dtype=np.uint8)
    return np.vstack(rows)


def decompose_r_groups(
    mols: Iterable[Mol], core: Mol
) -> tuple[list[dict[str, Mol]], list[int]]:
    """Decompose ``mols`` around a shared ``core`` into R-group fragments.

    Returns ``(rows, unmatched)``. ``rows`` has one entry per molecule that
    matches the core, in input order, each a mapping like
    ``{"Core": Mol, "R1": Mol, "R2": Mol, ...}`` whose keys are consistent
    across rows. ``unmatched`` holds the input indices that did not match the
    core (these contribute no row). Wraps RDKit's ``RGroupDecompose``.
    """
    from rdkit.Chem import rdRGroupDecomposition

    # ``asSmiles=False`` returns fragments as ``Mol`` objects so callers can
    # render or analyze them with the rest of the Mol-core, rather than
    # re-parsing SMILES.
    rows, unmatched = rdRGroupDecomposition.RGroupDecompose(
        [core], list(mols), asSmiles=False
    )
    return rows, list(unmatched)
