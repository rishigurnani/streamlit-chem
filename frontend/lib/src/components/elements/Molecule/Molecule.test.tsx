/**
 * Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022-2026)
 * Copyright (c) 2026 Rishi Gurnani
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
import { describe, expect, it } from "vitest"

import { Molecule as MoleculeProto } from "@streamlit/protobuf"

import { render } from "~lib/test_util"

import Molecule from "./Molecule"

function makeProto(partial: Partial<MoleculeProto>): MoleculeProto {
  return {
    svg: "",
    caption: "",
    toJSON: () => ({}),
    ...partial,
  }
}

describe("Molecule element", () => {
  it("renders the sanitized SVG inside the molecule container", () => {
    const element = makeProto({
      svg: "<svg><rect width='10' height='10'></rect></svg>",
    })

    render(<Molecule element={element} />)

    const container = screen.getByTestId("stMolecule")
    expect(container).toBeVisible()
    expect(container.querySelector("svg")).toBeInTheDocument()
    expect(container.querySelector("rect")).toBeInTheDocument()
  })

  it("strips script tags from the SVG for safety", () => {
    const element = makeProto({
      svg: "<svg><script>window.__pwned = true</script><rect></rect></svg>",
    })

    render(<Molecule element={element} />)

    const container = screen.getByTestId("stMolecule")
    expect(container.querySelector("rect")).toBeInTheDocument()
    expect(container.querySelector("script")).not.toBeInTheDocument()
  })

  it("renders a caption when provided", () => {
    const element = makeProto({
      svg: "<svg><rect></rect></svg>",
      caption: "Aspirin",
    })

    render(<Molecule element={element} />)

    expect(screen.getByText("Aspirin")).toBeVisible()
  })

  it("does not render a caption element when caption is empty", () => {
    const element = makeProto({ svg: "<svg><rect></rect></svg>" })

    render(<Molecule element={element} />)

    expect(screen.queryByTestId("stMoleculeCaption")).not.toBeInTheDocument()
  })

  it("renders nothing when the SVG is empty", () => {
    const element = makeProto({ svg: "" })

    const { container } = render(<Molecule element={element} />)

    expect(screen.queryByTestId("stMolecule")).not.toBeInTheDocument()
    expect(container).toBeEmptyDOMElement()
  })
})
