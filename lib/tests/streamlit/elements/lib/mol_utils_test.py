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

"""Unit tests for the shared cheminformatics helpers in ``mol_utils``."""

from __future__ import annotations

import pytest
from rdkit import Chem
from rdkit.Chem import AllChem

from streamlit.elements.lib import mol_utils
from streamlit.errors import StreamlitAPIException

# Aspirin: an acetyl group on a benzene ring bearing a carboxylic acid.
_ASPIRIN_SMILES = "CC(=O)Oc1ccccc1C(=O)O"


def test_to_mol_parses_smiles() -> None:
    """A SMILES string is parsed into an equivalent RDKit Mol."""
    mol = mol_utils.to_mol("c1ccccc1O")
    assert Chem.MolToSmiles(mol) == Chem.CanonSmiles("c1ccccc1O")


def test_to_mol_passes_through_existing_mol() -> None:
    """An existing Mol is returned unchanged (same object identity)."""
    original = Chem.MolFromSmiles("CCO")
    assert mol_utils.to_mol(original) is original


def test_to_mol_raises_on_invalid_smiles() -> None:
    """An unparseable SMILES string raises a StreamlitAPIException."""
    with pytest.raises(StreamlitAPIException, match="Could not parse molecule"):
        mol_utils.to_mol("this-is-not-smiles")


def test_to_mol_parses_molblock() -> None:
    """A MOL block string is auto-detected and parsed back into the same molecule."""
    molblock = mol_utils.to_molblock_3d("CCO")
    mol = mol_utils.to_mol(molblock)
    # The embedded MOL block keeps explicit hydrogens; strip them to compare the
    # heavy-atom skeleton against the original SMILES.
    assert Chem.MolToSmiles(Chem.RemoveHs(mol)) == Chem.CanonSmiles("CCO")


def test_to_mol_raises_on_invalid_molblock() -> None:
    """A string that looks like a MOL block but is malformed raises clearly."""
    with pytest.raises(StreamlitAPIException, match="MOL block"):
        mol_utils.to_mol("not really\na V2000 mol block\nM  END\n")


def test_to_mol_raises_on_unsupported_type() -> None:
    """A non-string, non-Mol input raises a StreamlitAPIException."""
    with pytest.raises(StreamlitAPIException, match="must be a SMILES string"):
        mol_utils.to_mol(42)  # type: ignore[arg-type]


def test_to_query_parses_smarts() -> None:
    """A SMARTS string is parsed into a query Mol usable for matching."""
    query = mol_utils.to_query("c1ccccc1")
    assert Chem.MolFromSmiles("c1ccccc1").HasSubstructMatch(query)


def test_to_query_raises_on_invalid_smarts() -> None:
    """An unparseable SMARTS string raises a StreamlitAPIException."""
    with pytest.raises(StreamlitAPIException, match="Could not parse substructure"):
        mol_utils.to_query("[[[")


def test_get_substructure_match_returns_atoms_and_bonds() -> None:
    """A matching query yields the matched atom indices and the bonds between them."""
    mol = mol_utils.to_mol(_ASPIRIN_SMILES)
    atom_ids, bond_ids = mol_utils.get_substructure_match(mol, "c1ccccc1")

    # A benzene ring has six atoms and six bonds fully inside the match.
    assert len(atom_ids) == 6
    assert len(bond_ids) == 6
    # Every reported bond must connect two matched atoms.
    matched = set(atom_ids)
    for bond_id in bond_ids:
        bond = mol.GetBondWithIdx(bond_id)
        assert bond.GetBeginAtomIdx() in matched
        assert bond.GetEndAtomIdx() in matched


def test_get_substructure_match_returns_empty_when_no_match() -> None:
    """A non-matching query yields empty atom and bond lists rather than raising."""
    mol = mol_utils.to_mol("CCO")
    assert mol_utils.get_substructure_match(mol, "c1ccccc1") == ([], [])


def test_mol_to_svg_returns_svg_markup() -> None:
    """Rendering returns a self-contained SVG document."""
    svg = mol_utils.mol_to_svg(mol_utils.to_mol("CCO"))
    assert "<svg" in svg
    assert "</svg>" in svg


def test_mol_to_svg_respects_explicit_canvas_size() -> None:
    """Explicit width/height are forwarded to the RDKit canvas dimensions."""
    svg = mol_utils.mol_to_svg(mol_utils.to_mol("CCO"), width=123, height=234)
    assert "width='123px'" in svg
    assert "height='234px'" in svg


def test_mol_to_svg_highlights_do_not_break_rendering() -> None:
    """Passing highlight atoms/bonds still produces valid SVG markup."""
    mol = mol_utils.to_mol(_ASPIRIN_SMILES)
    atom_ids, bond_ids = mol_utils.get_substructure_match(mol, "c1ccccc1")
    svg = mol_utils.mol_to_svg(mol, highlight_atoms=atom_ids, highlight_bonds=bond_ids)
    assert "<svg" in svg


def test_mol_to_svg_data_uri_is_base64_svg() -> None:
    """The data-URI helper wraps the SVG markup as a base64 image URI."""
    import base64

    uri = mol_utils.mol_to_svg_data_uri(mol_utils.to_mol("CCO"))
    prefix = "data:image/svg+xml;base64,"
    assert uri.startswith(prefix)

    decoded = base64.b64decode(uri[len(prefix) :]).decode("utf-8")
    assert "<svg" in decoded


def test_compute_descriptors_returns_requested_values() -> None:
    """Requested descriptors are computed and returned keyed by name."""
    values = mol_utils.compute_descriptors(
        mol_utils.to_mol(_ASPIRIN_SMILES), ["MW", "HBD", "HBA"]
    )
    assert set(values) == {"MW", "HBD", "HBA"}
    assert values["MW"] == pytest.approx(180.16, abs=0.1)
    assert values["HBD"] == 1
    assert values["HBA"] == 3


def test_compute_descriptors_raises_on_unknown_name() -> None:
    """An unknown descriptor name raises a StreamlitAPIException."""
    with pytest.raises(StreamlitAPIException, match="Unknown molecular descriptor"):
        mol_utils.compute_descriptors(mol_utils.to_mol("CCO"), ["NotADescriptor"])


def test_lipinski_violations_passes_for_drug_like_molecule() -> None:
    """A drug-like molecule (aspirin) has no rule-of-five violations."""
    assert mol_utils.lipinski_violations(mol_utils.to_mol(_ASPIRIN_SMILES)) == []


def test_lipinski_violations_flags_breached_rules() -> None:
    """A large polyol breaches the MW, HBD, and HBA rules."""
    violations = mol_utils.lipinski_violations(
        mol_utils.to_mol("OCC(O)C(O)C(O)C(O)CO" * 3)
    )
    assert "MW > 500" in violations
    assert "HBD > 5" in violations
    assert "HBA > 10" in violations
    # A rule that is not breached must not be reported.
    assert "LogP > 5" not in violations


def _molblock_z_coords(molblock: str) -> list[float]:
    """Return the z-coordinate of every atom in a V2000 MOL block."""
    lines = molblock.splitlines()
    # The counts line (index 3) starts with the atom count in its first 3 chars;
    # atom lines follow, each holding x/y/z in the first three fixed columns.
    atom_count = int(lines[3][:3])
    return [float(lines[4 + i].split()[2]) for i in range(atom_count)]


def test_to_molblock_3d_embeds_conformer_from_smiles() -> None:
    """A SMILES string is embedded into a MOL block with non-flat 3D coords."""
    molblock = mol_utils.to_molblock_3d("c1ccccc1O")
    assert "V2000" in molblock
    # A genuine 3D embedding must have at least one atom off the z=0 plane.
    assert any(abs(z) > 1e-6 for z in _molblock_z_coords(molblock))


def test_to_molblock_3d_adds_hydrogens() -> None:
    """Embedding adds explicit hydrogens, so methane yields five atoms."""
    molblock = mol_utils.to_molblock_3d("C")
    assert int(molblock.splitlines()[3][:3]) == 5


def test_to_molblock_3d_without_generate_uses_existing_conformer() -> None:
    """With ``generate_3d=False`` an existing conformer is serialized as-is."""
    mol = Chem.AddHs(Chem.MolFromSmiles("CCO"))
    AllChem.EmbedMolecule(mol, AllChem.ETKDG())
    expected = mol.GetConformer().GetAtomPosition(0).z

    molblock = mol_utils.to_molblock_3d(mol, generate_3d=False)
    # MOL block coordinates are written to 4 decimal places.
    assert _molblock_z_coords(molblock)[0] == pytest.approx(expected, abs=1e-4)


def test_to_molblock_3d_without_conformer_still_embeds() -> None:
    """``generate_3d=False`` with no conformer falls through to embedding."""
    molblock = mol_utils.to_molblock_3d("CCO", generate_3d=False)
    assert any(abs(z) > 1e-6 for z in _molblock_z_coords(molblock))


def test_compute_fingerprints_shape_and_dtype() -> None:
    """Fingerprints stack into an (n_mols, n_bits) uint8 matrix."""
    import numpy as np

    mols = [Chem.MolFromSmiles(s) for s in ["c1ccccc1O", "c1ccccc1N", "CCO"]]
    fps = mol_utils.compute_fingerprints(mols, n_bits=128)
    assert fps.shape == (3, 128)
    assert fps.dtype == np.uint8
    # Fingerprints are binary bit vectors, never counts.
    assert set(np.unique(fps)).issubset({0, 1})


def test_compute_fingerprints_distinguishes_structures() -> None:
    """Different molecules yield different fingerprints."""
    import numpy as np

    phenol, ethanol = Chem.MolFromSmiles("c1ccccc1O"), Chem.MolFromSmiles("CCO")
    fps = mol_utils.compute_fingerprints([phenol, ethanol], n_bits=256)
    assert not np.array_equal(fps[0], fps[1])


def test_compute_fingerprints_rdkit_family() -> None:
    """The RDKit path-based fingerprint is supported alongside Morgan."""
    mols = [Chem.MolFromSmiles("c1ccccc1O")]
    fps = mol_utils.compute_fingerprints(mols, fingerprint="rdkit", n_bits=64)
    assert fps.shape == (1, 64)


def test_compute_fingerprints_empty_input() -> None:
    """No molecules yields an empty (0, n_bits) matrix rather than an error."""
    fps = mol_utils.compute_fingerprints([], n_bits=32)
    assert fps.shape == (0, 32)


def test_compute_fingerprints_rejects_unknown_family() -> None:
    """An unknown fingerprint type raises a clear StreamlitAPIException."""
    with pytest.raises(StreamlitAPIException, match="Unknown fingerprint type"):
        mol_utils.compute_fingerprints(
            [Chem.MolFromSmiles("CCO")],
            fingerprint="ecfp",  # type: ignore[arg-type]
        )


def test_decompose_r_groups_splits_around_core() -> None:
    """Matching molecules are decomposed into consistent Core/R# fragments."""
    mols = [Chem.MolFromSmiles(s) for s in ["c1ccccc1O", "c1ccccc1N"]]
    core = Chem.MolFromSmiles("c1ccccc1")
    rows, unmatched = mol_utils.decompose_r_groups(mols, core)

    assert unmatched == []
    assert len(rows) == 2
    # Every row shares the same fragment columns (a Core plus one R-group).
    assert set(rows[0]) == {"Core", "R1"} == set(rows[1])
    # The R-group of phenol carries the oxygen substituent.
    assert "O" in Chem.MolToSmiles(rows[0]["R1"])


def test_decompose_r_groups_reports_unmatched() -> None:
    """A molecule without the core is reported by index and contributes no row."""
    mols = [Chem.MolFromSmiles(s) for s in ["c1ccccc1O", "CCO"]]
    core = Chem.MolFromSmiles("c1ccccc1")
    rows, unmatched = mol_utils.decompose_r_groups(mols, core)

    assert unmatched == [1]
    assert len(rows) == 1
