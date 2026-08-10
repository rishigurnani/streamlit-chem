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

from e2e_playwright.shared.app_utils import check_top_level_class

# One stMolViewer element per st.mol_viewer call in st_mol_viewer.py.
ST_MOL_VIEWER_ELEMENTS = 2


def test_mol_viewer_renders_webgl_canvas(app: Page):
    """Each st.mol_viewer call mounts a viewer with a WebGL canvas.

    WebGL pixel output is unreliable in headless CI, so we assert the viewer and
    its canvas are present rather than snapshotting the rendered molecule.
    """
    viewers = app.get_by_test_id("stMolViewer")
    expect(viewers).to_have_count(ST_MOL_VIEWER_ELEMENTS)
    for i in range(ST_MOL_VIEWER_ELEMENTS):
        expect(viewers.nth(i).locator("canvas")).to_be_attached()


def test_mol_viewer_selection_starts_empty(app: Page):
    """Before any interaction, the selection state exposes no selected atoms."""
    expect(app.get_by_test_id("stText")).to_have_text("selected atoms: []")


def test_check_top_level_class(app: Page):
    """The viewer element carries the expected top-level CSS class."""
    check_top_level_class(app, "stMolViewer")
