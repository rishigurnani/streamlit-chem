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

from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import assert_type

# Type-checking tests for st.mol_viewer. The viewer is always a widget, so it
# always returns MolViewerState regardless of the input form.
if TYPE_CHECKING:
    from streamlit.elements.mol_viewer import MolViewerMixin, MolViewerSelectionState
    from streamlit.typing import MolViewerState

    mol_viewer = MolViewerMixin().mol_viewer

    assert_type(mol_viewer("c1ccccc1O"), MolViewerState)
    assert_type(
        mol_viewer("CCO", style="ball_and_stick", surface="vdw"), MolViewerState
    )

    state = mol_viewer("CCO")
    assert_type(state.selection, MolViewerSelectionState)
    assert_type(state["selection"], MolViewerSelectionState)
    assert_type(state.selection.atoms, list[int])
    assert_type(state.selection["atoms"], list[int])
    assert_type(state.selection.bonds, list[int])
    assert_type(state.selection["bonds"], list[int])
