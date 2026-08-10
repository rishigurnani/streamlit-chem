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

import { screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { MolViewer as MolViewerProto } from "@streamlit/protobuf"

import { render } from "~lib/test_util"
import { WidgetStateManager } from "~lib/WidgetStateManager"

import MolViewer from "./MolViewer"
import {
  getStyleSpec,
  getSurfaceType,
  parseSelectionState,
  toggleIndex,
} from "./utils"

/** A clicked-atom callback captured from the mocked 3Dmol viewer. */
type ClickCallback = (atom: { index?: number; serial?: number }) => void

let capturedClickCallback: ClickCallback | undefined

const mockViewer = {
  addModel: vi.fn(),
  setStyle: vi.fn(),
  addSurface: vi.fn(),
  setClickable: vi.fn((_sel: unknown, _on: boolean, cb: ClickCallback) => {
    capturedClickCallback = cb
  }),
  spin: vi.fn(),
  zoomTo: vi.fn(),
  render: vi.fn(),
  resize: vi.fn(),
  clear: vi.fn(),
  getStringValue: vi.fn(),
}

const mockCreateViewer = vi.fn((..._args: unknown[]) => mockViewer)

vi.mock("3dmol", () => ({
  createViewer: (...args: unknown[]) => mockCreateViewer(...args),
  SurfaceType: { VDW: 1, MS: 2, SAS: 3, SES: 4 },
}))

function makeProto(partial: Partial<MolViewerProto> = {}): MolViewerProto {
  return new MolViewerProto({
    molblock: "MOCK_MOLBLOCK",
    style: "stick",
    surface: "",
    surfaceOpacity: 0,
    background: "",
    spin: false,
    selectionMode: ["atom"],
    id: "mol_viewer_1",
    formId: "",
    disabled: false,
    ...partial,
  })
}

function createWidgetManager(): WidgetStateManager {
  const mgr = new WidgetStateManager({
    sendRerunBackMsg: vi.fn(),
    formsDataChanged: vi.fn(),
  })
  mgr.setStringValue = vi.fn()
  mgr.getStringValue = vi.fn().mockReturnValue(undefined)
  return mgr
}

describe("MolViewer element", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    capturedClickCallback = undefined
  })

  it("creates a 3Dmol viewer and loads the served MOL block", () => {
    const widgetMgr = createWidgetManager()

    render(
      <MolViewer
        element={makeProto()}
        widgetMgr={widgetMgr}
        disabled={false}
      />
    )

    expect(screen.getByTestId("stMolViewer")).toBeVisible()
    expect(mockCreateViewer).toHaveBeenCalledOnce()
    expect(mockViewer.addModel).toHaveBeenCalledWith("MOCK_MOLBLOCK", "sdf")
    expect(mockViewer.setStyle).toHaveBeenCalledWith({}, { stick: {} })
    expect(mockViewer.render).toHaveBeenCalled()
  })

  it("draws a surface when one is requested", () => {
    const widgetMgr = createWidgetManager()

    render(
      <MolViewer
        element={makeProto({ surface: "vdw", surfaceOpacity: 0.85 })}
        widgetMgr={widgetMgr}
        disabled={false}
      />
    )

    expect(mockViewer.addSurface).toHaveBeenCalledWith(1, { opacity: 0.85 })
  })

  it("writes the clicked atom into widget state", () => {
    const widgetMgr = createWidgetManager()

    render(
      <MolViewer
        element={makeProto()}
        widgetMgr={widgetMgr}
        disabled={false}
        fragmentId="frag-1"
      />
    )

    expect(mockViewer.setClickable).toHaveBeenCalledOnce()
    // Simulate the user clicking atom index 3 in the 3D scene.
    capturedClickCallback?.({ index: 3 })

    expect(widgetMgr.setStringValue).toHaveBeenCalledWith(
      expect.anything(),
      JSON.stringify({ selection: { atoms: [3], bonds: [] } }),
      { fromUi: true },
      "frag-1"
    )
  })

  it("does not enable clicking when selection is disabled", () => {
    const widgetMgr = createWidgetManager()

    render(
      <MolViewer
        element={makeProto({ selectionMode: [] })}
        widgetMgr={widgetMgr}
        disabled={false}
      />
    )

    expect(mockViewer.setClickable).not.toHaveBeenCalled()
  })

  it("does not enable clicking when the widget is disabled", () => {
    const widgetMgr = createWidgetManager()

    render(
      <MolViewer element={makeProto()} widgetMgr={widgetMgr} disabled={true} />
    )

    expect(mockViewer.setClickable).not.toHaveBeenCalled()
  })
})

describe("MolViewer utils", () => {
  it("maps ball_and_stick onto a combined stick + sphere spec", () => {
    expect(getStyleSpec("ball_and_stick")).toEqual({
      stick: { radius: 0.15 },
      sphere: { scale: 0.25 },
    })
  })

  it("defaults an unknown style to stick", () => {
    expect(getStyleSpec("wireframe")).toEqual({ stick: {} })
  })

  it("maps surface names to 3Dmol surface types and undefined otherwise", () => {
    expect(getSurfaceType("sas")).toBe(getSurfaceType("sas"))
    expect(getSurfaceType("")).toBeUndefined()
  })

  it("toggles an index off when it is already selected", () => {
    expect(toggleIndex([1, 2, 3], 2)).toEqual([1, 3])
    expect(toggleIndex([1, 2], 5)).toEqual([1, 2, 5])
  })

  it("falls back to an empty selection for malformed JSON", () => {
    expect(parseSelectionState("not json")).toEqual({
      selection: { atoms: [], bonds: [] },
    })
  })
})
