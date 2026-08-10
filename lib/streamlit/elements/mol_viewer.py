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

"""Streamlit support for an interactive 3D molecule viewer (powered by 3Dmol.js).

Unlike ``st.molecule`` (a pure 2D display element), ``st.mol_viewer`` is a
*widget*: atom and bond clicks in the WebGL viewer flow back into the Python
script as a selection state, so the 3D view can drive the rest of the app. The
only new cheminformatics logic lives in ``mol_utils.to_molblock_3d``; this
module is the thin widget layer on top of it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final, Literal, TypeAlias, cast, overload

from streamlit.elements.lib.form_utils import current_form_id
from streamlit.elements.lib.layout_utils import LayoutConfig
from streamlit.elements.lib.mol_utils import to_molblock_3d
from streamlit.elements.lib.policies import check_widget_policies
from streamlit.elements.lib.utils import (
    Key,
    compute_and_register_element_id,
    to_key,
)
from streamlit.errors import StreamlitAPIException
from streamlit.proto.MolViewer_pb2 import MolViewer as MolViewerProto
from streamlit.runtime.metrics_util import gather_metrics
from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx
from streamlit.runtime.state import WidgetCallback, register_widget
from streamlit.util import ReadOnlyAttributeDictionary

if TYPE_CHECKING:
    from collections.abc import Iterable

    from streamlit.delta_generator import DeltaGenerator
    from streamlit.elements.lib.mol_utils import MoleculeData

MolViewerStyle: TypeAlias = Literal[
    "stick", "sphere", "line", "cartoon", "ball_and_stick"
]
_STYLES: Final[frozenset[str]] = frozenset(
    {"stick", "sphere", "line", "cartoon", "ball_and_stick"}
)

MolViewerSurface: TypeAlias = Literal["vdw", "sas", "ms"]
_SURFACES: Final[frozenset[str]] = frozenset({"vdw", "sas", "ms"})

SelectionMode: TypeAlias = Literal["atom", "bond"]
_SELECTION_MODES: Final[frozenset[str]] = frozenset({"atom", "bond"})

# Opacity used when a surface is drawn. Not yet user-configurable (see the
# tech spec's "surface opacity" note); a translucent shell reads well over a
# stick model without hiding it.
_SURFACE_OPACITY: Final = 0.85


class MolViewerSelectionState(ReadOnlyAttributeDictionary):
    """The schema for the 3D molecule viewer's selection state.

    The selection state is stored in a read-only dictionary-like object that
    supports both key and attribute notation. Selection states cannot be
    programmatically changed or set through Session State.

    Attributes
    ----------
    atoms : list[int]
        The indices of the atoms the user has clicked, in click order.

    bonds : list[int]
        The indices of the bonds the user has clicked, in click order.

    """

    atoms: list[int]
    bonds: list[int]

    @overload
    def __getitem__(self, key: Literal["atoms"]) -> list[int]: ...

    @overload
    def __getitem__(self, key: Literal["bonds"]) -> list[int]: ...

    @overload
    def __getitem__(self, key: Any) -> Any: ...

    def __getitem__(self, key: Any) -> Any:
        return super().__getitem__(key)


class MolViewerState(ReadOnlyAttributeDictionary):
    """The schema for the 3D molecule viewer's event state.

    The event state is stored in a read-only dictionary-like object that
    supports both key and attribute notation. Event states cannot be
    programmatically changed or set through Session State.

    Attributes
    ----------
    selection : dict
        The state of the ``on_select`` event. This attribute returns a
        dictionary-like object that supports both key and attribute notation.
        The attributes are described by ``MolViewerSelectionState``.

    """

    selection: MolViewerSelectionState

    # ReadOnlyAttributeDictionary routes attribute access through __getitem__,
    # so overriding it is enough to keep `selection` typed. Use dict.__getitem__
    # for the selection key so the read-only base class does not re-wrap the
    # already-typed nested instance.
    @overload
    def __getitem__(self, key: Literal["selection"]) -> MolViewerSelectionState: ...

    @overload
    def __getitem__(self, key: Any) -> Any: ...

    def __getitem__(self, key: Any) -> Any:
        if key == "selection":
            item = dict.__getitem__(self, key)
            if not isinstance(item, MolViewerSelectionState):
                item = MolViewerSelectionState(item)
                # Cache so repeated bracket/attribute access stays identity-stable.
                dict.__setitem__(self, key, item)
            return item
        return super().__getitem__(key)


@dataclass
class MolViewerSelectionSerde:
    """Serialize and deserialize the 3D molecule viewer selection state."""

    def deserialize(self, ui_value: str | None) -> MolViewerState:
        empty_state = MolViewerState(
            {"selection": MolViewerSelectionState({"atoms": [], "bonds": []})}
        )
        if ui_value is None:
            return empty_state

        parsed = json.loads(ui_value)
        if "selection" not in parsed:  # pragma: no cover - defensive
            return empty_state

        parsed["selection"] = MolViewerSelectionState(parsed["selection"])
        return MolViewerState(parsed)

    def serialize(self, state: MolViewerState) -> str:
        return json.dumps(state, default=str)


def _parse_selection_mode(
    selection_mode: SelectionMode | Iterable[SelectionMode],
) -> list[str]:
    """Validate ``selection_mode`` and return it as a de-duplicated list of strings."""
    modes = {selection_mode} if isinstance(selection_mode, str) else set(selection_mode)
    if not modes.issubset(_SELECTION_MODES):
        raise StreamlitAPIException(
            f"Invalid selection_mode: {selection_mode!r}. "
            f"Valid options are {sorted(_SELECTION_MODES)}."
        )
    return sorted(modes)


class MolViewerMixin:
    @gather_metrics("mol_viewer")
    def mol_viewer(
        self,
        data: MoleculeData,
        *,
        style: MolViewerStyle = "stick",
        surface: MolViewerSurface | None = None,
        generate_3d: bool = True,
        spin: bool = False,
        background: str | None = None,
        height: int = 480,
        on_select: WidgetCallback | None = None,
        selection_mode: SelectionMode | Iterable[SelectionMode] = ("atom",),
        key: Key | None = None,
    ) -> MolViewerState:
        """Display an interactive 3D molecule viewer and return its selection.

        The molecule is embedded in 3D server-side with RDKit and rendered in
        the browser with `3Dmol.js <https://3dmol.csb.pitt.edu/>`_ (a WebGL
        viewer). Atom and bond clicks flow back into your script as a selection
        state, so the 3D view can drive the rest of your app.

        Parameters
        ----------
        data : str or rdkit.Chem.Mol
            The molecule to display, as a SMILES string, a MOL block, or an
            ``rdkit.Chem.Mol`` object.

        style : "stick", "sphere", "line", "cartoon", or "ball_and_stick"
            The representation style of the molecule. Defaults to ``"stick"``.

            - ``"stick"`` (default): Bonds as sticks; good for small molecules.
            - ``"sphere"``: Space-filling (CPK) spheres.
            - ``"line"``: Thin wireframe lines.
            - ``"cartoon"``: Ribbon/cartoon, intended for macromolecules.
            - ``"ball_and_stick"``: Atoms as balls joined by stick bonds.

        surface : "vdw", "sas", "ms", or None
            An optional molecular surface to overlay on the model. This can be
            one of the following:

            - ``None`` (default): No surface is drawn.
            - ``"vdw"``: The van der Waals surface.
            - ``"sas"``: The solvent-accessible surface.
            - ``"ms"``: The solvent-excluded molecular surface.

        generate_3d : bool
            Whether to embed a fresh 3D conformer with RDKit when the input has
            none. If this is ``True`` (default), a SMILES string or flat 2D
            molecule is embedded and energy-minimized. If this is ``False``, an
            existing 3D conformer is used as-is (a conformer is still generated
            when the input has none).

        spin : bool
            Whether the viewer auto-rotates the molecule. Defaults to ``False``.

        background : str or None
            The background color of the viewer as a CSS color string. If this is
            ``None`` (default), the background matches the app's theme.

        height : int
            The height of the viewer in pixels. Defaults to ``480``.

        on_select : callable or None
            An optional callback that runs when the user changes the selection.
            The callback runs before the rest of your script reruns.

        selection_mode : "atom", "bond", or an Iterable of these
            Which parts of the molecule the user can select. This can be one of
            the following:

            - ``"atom"`` (default): Atoms are clickable.
            - ``"bond"``: Bonds are clickable.
            - An ``Iterable`` of the above: Both kinds are clickable.
            - An empty ``Iterable``: Selection is disabled.

        key : str, int, or None
            An optional string or integer to use as a stable identity for the
            widget. If this is ``None`` (default), the identity is computed from
            the widget's arguments. The selection state is read-only and, when
            ``key`` is set, is also mirrored to Session State under that key.

        Returns
        -------
        MolViewerState
            A dictionary-like object with a ``selection`` attribute holding the
            clicked ``atoms`` and ``bonds``, described by the
            ``MolViewerSelectionState`` class.

        Examples
        --------
        >>> import streamlit as st
        >>>
        >>> event = st.mol_viewer("CC(=O)Oc1ccccc1C(=O)O", style="ball_and_stick")
        >>> if event.selection.atoms:
        ...     st.write("Clicked atoms:", event.selection.atoms)

        """
        if style not in _STYLES:
            raise StreamlitAPIException(
                f"Invalid style {style!r} for st.mol_viewer. "
                f"Valid options are {sorted(_STYLES)}."
            )
        if surface is not None and surface not in _SURFACES:
            raise StreamlitAPIException(
                f"Invalid surface {surface!r} for st.mol_viewer. "
                f"Valid options are {sorted(_SURFACES)} or None."
            )
        if not isinstance(height, int) or height <= 0:
            raise StreamlitAPIException(
                f"Invalid height {height!r} for st.mol_viewer. "
                "Provide a positive integer number of pixels."
            )

        parsed_modes = _parse_selection_mode(selection_mode)
        key = to_key(key)

        check_widget_policies(
            self.dg,
            key,
            on_change=on_select,
            default_value=None,
            writes_allowed=False,
            enable_check_callback_rules=on_select is not None,
        )

        proto = MolViewerProto()
        proto.molblock = to_molblock_3d(data, generate_3d=generate_3d)
        proto.style = style
        proto.surface = surface or ""
        proto.surface_opacity = _SURFACE_OPACITY if surface is not None else 0.0
        proto.background = background or ""
        proto.spin = spin
        proto.selection_mode.extend(parsed_modes)
        proto.form_id = current_form_id(self.dg)

        ctx = get_script_run_ctx()
        proto.id = compute_and_register_element_id(
            "mol_viewer",
            user_key=key,
            key_as_main_identity=False,
            dg=self.dg,
            molblock=proto.molblock,
            style=style,
            surface=proto.surface,
            background=proto.background,
            spin=spin,
            selection_mode=parsed_modes,
        )

        serde = MolViewerSelectionSerde()
        widget_state = register_widget(
            proto.id,
            on_change_handler=on_select,
            deserializer=serde.deserialize,
            serializer=serde.serialize,
            ctx=ctx,
            value_type="string_value",
        )

        self.dg._enqueue(
            "mol_viewer",
            proto,
            layout_config=LayoutConfig(width="stretch", height=height),
        )
        return widget_state.value

    @property
    def dg(self) -> DeltaGenerator:
        """The associated DeltaGenerator."""
        return cast("DeltaGenerator", self)
