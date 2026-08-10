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

import streamlit as st

# A viewer with the default atom-selection widget behavior. The companion text
# echoes the selection state so tests can observe the round-trip.
event = st.mol_viewer("c1ccccc1O", key="viewer")
st.text(f"selected atoms: {event.selection.atoms}")

# A styled viewer with a surface and selection disabled (pure display).
st.mol_viewer(
    "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
    style="ball_and_stick",
    surface="vdw",
    selection_mode=(),
)
