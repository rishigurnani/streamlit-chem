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

import { memo, ReactElement, useMemo } from "react"

import dompurify from "dompurify"

import { Molecule as MoleculeProto } from "@streamlit/protobuf"

import { StyledMolecule, StyledMoleculeCaption } from "./styled-components"

/**
 * DOMPurify options for the RDKit-generated 2D structure. The molecule is a
 * self-contained SVG document, so we sanitize with the SVG profile (no HTML,
 * no scripts) before rendering.
 */
const SANITIZE_SVG_OPTIONS = {
  USE_PROFILES: { svg: true, svgFilters: true },
}

interface MoleculeProps {
  element: MoleculeProto
}

/**
 * A native 2D molecular structure rendered server-side by RDKit.
 */
function Molecule({ element }: Readonly<MoleculeProps>): ReactElement | null {
  const { svg, caption } = element

  const sanitizedSvg = useMemo(
    () => dompurify.sanitize(svg, SANITIZE_SVG_OPTIONS),
    [svg]
  )

  if (!sanitizedSvg) {
    return null
  }

  return (
    <StyledMolecule className="stMolecule" data-testid="stMolecule">
      <div
        // Note: This is an expected usage of dangerouslySetInnerHTML for the
        // sanitized, script-free SVG produced by RDKit.
        // eslint-disable-next-line @eslint-react/dom-no-dangerously-set-innerhtml
        dangerouslySetInnerHTML={{ __html: sanitizedSvg }}
      />
      {caption && (
        <StyledMoleculeCaption data-testid="stMoleculeCaption">
          {caption}
        </StyledMoleculeCaption>
      )}
    </StyledMolecule>
  )
}

export default memo(Molecule)
