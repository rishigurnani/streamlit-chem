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

"""Tests for the ``st.smarts_input`` composition widget."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest


def _valid_app() -> None:
    import streamlit as st

    st.session_state["result"] = st.smarts_input(
        "Query", value="c1ccccc1", preview="c1ccccc1O"
    )


def _empty_app() -> None:
    import streamlit as st

    st.session_state["result"] = st.smarts_input("Query", value="")


def _invalid_app() -> None:
    import streamlit as st

    st.session_state["result"] = st.smarts_input("Query", value="[[[bad")


def test_valid_query_returns_string_and_renders_preview() -> None:
    """A valid SMARTS query is returned and a preview structure is rendered."""
    at = AppTest.from_function(_valid_app).run()

    assert not at.exception
    assert at.session_state["result"] == "c1ccccc1"
    # The preview renders exactly one molecule element.
    assert len(at.get("molecule")) == 1
    # A valid query produces no validation caption.
    assert not any("parse" in caption.value.lower() for caption in at.caption)


def test_empty_query_returns_none_without_warning() -> None:
    """An empty input returns None and shows neither a caption nor a preview."""
    at = AppTest.from_function(_empty_app).run()

    assert not at.exception
    assert at.session_state["result"] is None
    assert len(at.caption) == 0
    assert len(at.get("molecule")) == 0


def test_invalid_query_returns_none_and_warns() -> None:
    """An unparseable query returns None, warns inline, and renders no preview."""
    at = AppTest.from_function(_invalid_app).run()

    assert not at.exception
    assert at.session_state["result"] is None
    assert any("parse" in caption.value.lower() for caption in at.caption)
    assert len(at.get("molecule")) == 0
