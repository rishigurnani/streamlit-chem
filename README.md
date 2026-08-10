# 🧪 streamlit-chem

[![GitHub][github_badge]][github_link] [![PyPI][pypi_badge]][pypi_link]

> Native, RDKit-powered chemistry for Streamlit. Render, edit, and analyze molecules with first-class `st.*` commands — no iframes, no custom components, and no pickling foot-guns.

It leverages [RDKit](https://www.rdkit.org/) as its cheminformatics engine. Structures are rendered server-side to sanitized SVG, so molecules travel straight from Python to the browser — there is no browser-side RDKit to ship.

## Installation

```shell
pip install streamlit-chem
```

`streamlit-chem` is import-compatible with Streamlit: install it and every chemical command below is available on the `st.*` namespace alongside the full Streamlit API.

## Getting started

```python
import streamlit as st

st.molecule(
    "CC(=O)Oc1ccccc1C(=O)O",
    caption="Aspirin",
    highlight_substructure="c1ccccc1",
)
```

Pass a SMILES string or an `rdkit.Chem.Mol` — both just work.

## Chemical elements

| Command | Description |
| --- | --- |
| `st.molecule` | Render a molecule as a native 2D structure, with optional substructure highlighting. |
| `st.chem_dataframe` | A chemistry-aware `st.dataframe`: a molecule column renders as 2D structures, everything else behaves like a normal dataframe. |
| `st.smarts_input` | A `st.text_input` that validates a SMARTS/SMILES substructure query with RDKit as you type. |
| `st.mol_card` | A compact summary card: structure + physicochemical metrics + a Lipinski rule-of-five badge. |
| `st.chem_draw` | An interactive 2D editor (Ketcher) that returns the drawn structure as an `rdkit.Chem.Mol`. |
| `st.mol_viewer` | An interactive 3D viewer (3Dmol.js) from a server-side RDKit conformer, returning atom/bond clicks. |
| `st.chem_space` | Project a molecule library to a 2D map (fingerprints → PCA/t-SNE/UMAP) and lasso-select points. |
| `st.r_group_decomposition` | Decompose a series around a shared core into a table of rendered core and R-group structures. |

Molecules are also safe to cache — `@st.cache_data` serializes `rdkit.Chem.Mol` objects transparently.

## Demo

A gallery showcasing every element lives in [`demo_molecule.py`](demo_molecule.py):

```shell
streamlit run demo_molecule.py
```

[github_badge]: https://badgen.net/badge/icon/GitHub?icon=github&color=black&label
[github_link]: https://github.com/rishigurnani/streamlit-chem
[pypi_badge]: https://img.shields.io/pypi/v/streamlit-chem?logo=pypi&logoColor=white&color=black&label=PyPI
[pypi_link]: https://pypi.org/project/streamlit-chem
