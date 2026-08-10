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

import { memo, ReactElement, useEffect, useRef } from "react"

import { createViewer, GLViewer } from "3dmol"

import { MolViewer as MolViewerProto } from "@streamlit/protobuf"

import { useEmotionTheme } from "~lib/hooks/useEmotionTheme"
import { WidgetStateManager } from "~lib/WidgetStateManager"

import { StyledMolViewer } from "./styled-components"
import {
  getStyleSpec,
  getSurfaceType,
  parseSelectionState,
  toggleIndex,
} from "./utils"

/** The subset of a clicked 3Dmol atom we rely on. */
interface ClickedAtom {
  index?: number
  serial?: number
}

interface MolViewerProps {
  element: MolViewerProto
  widgetMgr: WidgetStateManager
  disabled: boolean
  fragmentId?: string
}

/**
 * An interactive 3D molecule viewer backed by 3Dmol.js (WebGL). The molecule
 * is embedded server-side by RDKit and handed to us as a MOL block; atom clicks
 * are written back into widget state so the Python script can react to them.
 */
function MolViewer({
  element,
  widgetMgr,
  disabled,
  fragmentId,
}: Readonly<MolViewerProps>): ReactElement {
  const theme = useEmotionTheme()
  const containerRef = useRef<HTMLDivElement>(null)
  const viewerRef = useRef<GLViewer | null>(null)

  const backgroundColor = element.background || theme.colors.bgColor
  const atomSelectionEnabled =
    !disabled && element.selectionMode.includes("atom")

  const { molblock, style, surface, surfaceOpacity, spin, id } = element

  useEffect(() => {
    const container = containerRef.current
    if (!container) {
      return
    }

    const viewer = createViewer(container, { backgroundColor })
    viewerRef.current = viewer
    viewer.addModel(molblock, "sdf")
    viewer.setStyle({}, getStyleSpec(style))

    const surfaceType = getSurfaceType(surface)
    if (surfaceType !== undefined) {
      viewer.addSurface(surfaceType, { opacity: surfaceOpacity })
    }

    if (atomSelectionEnabled) {
      viewer.setClickable({}, true, (atom: ClickedAtom): void => {
        // 3Dmol reports a 0-based `index`; `serial` (1-based) is the fallback.
        const atomIndex = atom.index ?? (atom.serial ?? 1) - 1
        const previous = parseSelectionState(widgetMgr.getStringValue(element))
        const nextState = {
          selection: {
            atoms: toggleIndex(previous.selection.atoms, atomIndex),
            bonds: previous.selection.bonds,
          },
        }
        widgetMgr.setStringValue(
          element,
          JSON.stringify(nextState),
          { fromUi: true },
          fragmentId
        )
      })
    }

    if (spin) {
      viewer.spin("y")
    }
    viewer.zoomTo()
    viewer.render()

    // 3Dmol measures the container once at creation; a ResizeObserver keeps the
    // canvas correct when the container is later resized (tabs, columns, etc.).
    const resizeObserver = new ResizeObserver(() => viewer.resize())
    resizeObserver.observe(container)

    return () => {
      resizeObserver.disconnect()
      viewer.clear()
      // Drop the WebGL canvas so a remount starts from a clean container.
      container.replaceChildren()
      viewerRef.current = null
    }
    // element.id changes whenever any styling/data input changes, so it is a
    // sufficient (and stable) trigger for rebuilding the viewer.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, backgroundColor, atomSelectionEnabled])

  return (
    <StyledMolViewer
      ref={containerRef}
      className="stMolViewer"
      data-testid="stMolViewer"
    />
  )
}

export default memo(MolViewer)
