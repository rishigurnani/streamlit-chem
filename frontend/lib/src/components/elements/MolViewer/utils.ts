/**
 * Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022-2026)
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { SurfaceType } from "3dmol"

/** The selection payload exchanged with the Python `MolViewerState`. */
export interface MolViewerSelection {
  atoms: number[]
  bonds: number[]
}

export interface MolViewerWidgetState {
  selection: MolViewerSelection
}

/** A 3Dmol atom-style spec keyed by representation name. */
type AtomStyleSpec = Record<string, Record<string, unknown>>

/**
 * Map a Streamlit `style` string onto a 3Dmol atom-style spec.
 *
 * "ball_and_stick" is 3Dmol's stick + sphere combination with reduced radii;
 * the others map one-to-one onto a single 3Dmol representation.
 */
export function getStyleSpec(style: string): AtomStyleSpec {
  switch (style) {
    case "sphere":
      return { sphere: {} }
    case "line":
      return { line: {} }
    case "cartoon":
      return { cartoon: {} }
    case "ball_and_stick":
      // These are 3Dmol geometry parameters (bond radius / atom scale in
      // angstrom-space), not CSS/theme values, so the theme-value rule doesn't apply.
      // eslint-disable-next-line streamlit-custom/no-hardcoded-theme-values
      return { stick: { radius: 0.15 }, sphere: { scale: 0.25 } }
    case "stick":
    default:
      return { stick: {} }
  }
}

/**
 * Map a Streamlit `surface` string onto a 3Dmol {@link SurfaceType}, or
 * `undefined` when no surface should be drawn.
 */
export function getSurfaceType(surface: string): SurfaceType | undefined {
  switch (surface) {
    case "vdw":
      return SurfaceType.VDW
    case "sas":
      return SurfaceType.SAS
    case "ms":
      return SurfaceType.MS
    default:
      return undefined
  }
}

/** The empty selection used before any atom or bond is clicked. */
export function emptySelectionState(): MolViewerWidgetState {
  return { selection: { atoms: [], bonds: [] } }
}

/**
 * Parse the widget's stored JSON selection, falling back to an empty selection
 * for missing or malformed values.
 */
export function parseSelectionState(
  raw: string | undefined
): MolViewerWidgetState {
  if (!raw) {
    return emptySelectionState()
  }
  try {
    const parsed = JSON.parse(raw) as Partial<MolViewerWidgetState>
    return {
      selection: {
        atoms: parsed.selection?.atoms ?? [],
        bonds: parsed.selection?.bonds ?? [],
      },
    }
  } catch {
    return emptySelectionState()
  }
}

/**
 * Toggle `index` within `values`: append it when absent, remove it when
 * present. Clicking a selected atom or bond again deselects it.
 */
export function toggleIndex(values: number[], index: number): number[] {
  return values.includes(index)
    ? values.filter(value => value !== index)
    : [...values, index]
}
