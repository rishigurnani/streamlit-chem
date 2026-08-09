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

"""Tests for the ``st.mol_card`` composition element."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest


def _aspirin_card_app() -> None:
    import streamlit as st

    st.mol_card(
        "CC(=O)Oc1ccccc1C(=O)O",
        title="Aspirin",
        metrics=["MW", "LogP", "TPSA", "HBD", "HBA"],
    )


def _no_metrics_card_app() -> None:
    import streamlit as st

    st.mol_card("CCO", metrics=[], show_ro5=False)


def _violating_card_app() -> None:
    import streamlit as st

    # A large polyol breaches several Lipinski rules (MW, HBD, HBA).
    st.mol_card("OCC(O)C(O)C(O)C(O)CO" * 3, metrics=["MW"])


def test_mol_card_renders_metrics_and_structure() -> None:
    """A card shows one metric per requested descriptor plus the structure."""
    at = AppTest.from_function(_aspirin_card_app).run()

    assert not at.exception
    assert [metric.label for metric in at.metric] == [
        "MW",
        "LogP",
        "TPSA",
        "HBD",
        "HBA",
    ]
    molecular_weight = next(metric for metric in at.metric if metric.label == "MW")
    assert molecular_weight.value == "180.2"
    assert len(at.get("molecule")) == 1


def test_mol_card_passes_lipinski_shows_pass_badge() -> None:
    """A drug-like molecule shows a passing rule-of-five badge."""
    at = AppTest.from_function(_aspirin_card_app).run()

    assert not at.exception
    assert any("Rule of 5: Pass" in markdown.value for markdown in at.markdown)


def test_mol_card_without_metrics_or_badge_is_just_structure() -> None:
    """With no metrics and RO5 disabled, the card renders only the structure."""
    at = AppTest.from_function(_no_metrics_card_app).run()

    assert not at.exception
    assert len(at.metric) == 0
    assert not any("Rule of 5" in markdown.value for markdown in at.markdown)
    assert len(at.get("molecule")) == 1


def test_mol_card_flags_lipinski_violations() -> None:
    """A molecule breaching multiple rules shows a violations badge."""
    at = AppTest.from_function(_violating_card_app).run()

    assert not at.exception
    assert any("violations" in markdown.value for markdown in at.markdown)
