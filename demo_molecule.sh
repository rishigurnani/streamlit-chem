#!/usr/bin/env bash
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

# ChemLit demo runner.
#
#   ./demo_molecule.sh          # render the demo molecules to an HTML gallery
#                               # (pure Python — works without a frontend build)
#   ./demo_molecule.sh --app    # launch the full live Streamlit app (needs Node 24)
#
set -euo pipefail
cd "$(dirname "$0")"

# --- choose a Python runner ---------------------------------------------------
# Prefer `uv run` (project policy); otherwise fall back to whatever Python env is
# currently active (e.g. an activated conda/venv like `streamlit-dev`).
if command -v uv >/dev/null 2>&1; then
  RUN=(uv run python)
elif command -v python >/dev/null 2>&1; then
  RUN=(python)
elif command -v python3 >/dev/null 2>&1; then
  RUN=(python3)
else
  echo "error: no Python found (tried uv, python, python3)."
  exit 1
fi

# --- full live app ------------------------------------------------------------
if [[ "${1:-}" == "--app" ]]; then
  echo "Starting the live ChemLit app (backend + Vite frontend, hot-reload)..."
  echo "The URL will be printed below; press Ctrl-C to stop."
  echo "(Requires Node 24 + frontend deps installed via 'make frontend-init'.)"
  exec make debug demo_molecule.py
fi

# --- static render (default) --------------------------------------------------
# Renders the four demo molecules through the *shipped* code path
# (streamlit.elements.lib.mol_utils — exactly what st.molecule calls) and writes
# a self-contained HTML gallery, then opens it.
OUT="$(pwd)/demo_molecule_gallery.html"

# Fail early with a clear message if the active env is missing dependencies.
if ! "${RUN[@]}" -c "import rdkit, streamlit" >/dev/null 2>&1; then
  echo "error: the active Python env can't import rdkit and/or streamlit."
  echo "Install them into your env, e.g.:  pip install rdkit"
  echo "(Streamlit should already be present in this repo's dev env.)"
  exit 1
fi

"${RUN[@]}" - "$OUT" <<'PY'
import sys
from rdkit import Chem
from streamlit.elements.lib import mol_utils

# (data, caption, highlight_substructure, width_px)
DEMOS = [
    ("c1ccccc1O", "Phenol (from SMILES)", None, None),
    (Chem.MolFromSmiles("CCO"), "Ethanol (from RDKit Mol)", None, None),
    ("CC(=O)Oc1ccccc1C(=O)O", "Aspirin — aromatic ring highlighted", "c1ccccc1", None),
    ("CN1C=NC2=C1C(=O)N(C(=O)N2C)C", "Caffeine (width=200)", None, 200),
]

cards = []
for data, caption, highlight, width in DEMOS:
    mol = mol_utils.to_mol(data)
    atoms, bonds = (
        mol_utils.get_substructure_match(mol, highlight) if highlight else ([], [])
    )
    svg = mol_utils.mol_to_svg(
        mol, width=width, height=None, highlight_atoms=atoms, highlight_bonds=bonds
    )
    cards.append(
        '<figure style="margin:0;text-align:center;background:#fff;'
        'border:1px solid #e0e0e0;border-radius:8px;padding:12px">'
        f"{svg}"
        '<figcaption style="color:#555;font-size:0.85rem;margin-top:6px">'
        f"{caption}</figcaption></figure>"
    )

html = (
    "<!doctype html><meta charset='utf-8'><title>ChemLit — st.molecule demo</title>"
    # Mirror the real element's responsive rule so wide structures scale to fit
    # their card instead of overflowing/clipping.
    "<style>figure svg{max-width:100%;height:auto}</style>"
    "<body style=\"font-family:system-ui,sans-serif;margin:32px;background:#fafafa\">"
    "<h1>🧪 ChemLit — <code>st.molecule</code></h1>"
    "<p style='color:#555'>These are the exact RDKit-rendered SVGs the element "
    "sends to the browser. For the interactive app, run "
    "<code>./demo_molecule.sh --app</code>.</p>"
    "<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));"
    "gap:20px'>" + "".join(cards) + "</div></body>"
)

out = sys.argv[1]
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Wrote gallery to {out}")
PY

echo "Opening gallery..."
open "$OUT" 2>/dev/null || echo "Open it manually: $OUT"
