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

from playwright.sync_api import Page, expect

from e2e_playwright.conftest import ImageCompareFunction
from e2e_playwright.shared.app_utils import check_top_level_class

# One stMolecule element per st.molecule call in st_molecule.py.
ST_MOLECULE_ELEMENTS = 4


def test_molecule_renders_all_structures(app: Page):
    """Each st.molecule call renders a structure as an inline SVG."""
    molecules = app.get_by_test_id("stMolecule")
    expect(molecules).to_have_count(ST_MOLECULE_ELEMENTS)
    # Every molecule element embeds a rendered SVG structure.
    for i in range(ST_MOLECULE_ELEMENTS):
        expect(molecules.nth(i).locator("svg")).to_be_visible()


def test_molecule_shows_captions(app: Page):
    """Captions passed to st.molecule are displayed beneath the structure."""
    expect(app.get_by_test_id("stMoleculeCaption").nth(0)).to_have_text("Phenol")
    expect(app.get_by_test_id("stMoleculeCaption").nth(1)).to_have_text("Ethanol")


def test_molecule_snapshot(themed_app: Page, assert_snapshot: ImageCompareFunction):
    """Visual snapshot of the first rendered molecule structure."""
    first_molecule = themed_app.get_by_test_id("stMolecule").nth(0)
    expect(first_molecule.locator("svg")).to_be_visible()
    assert_snapshot(first_molecule, name="st_molecule-phenol")


def test_check_top_level_class(app: Page):
    """The molecule element carries the expected top-level CSS class."""
    check_top_level_class(app, "stMolecule")
