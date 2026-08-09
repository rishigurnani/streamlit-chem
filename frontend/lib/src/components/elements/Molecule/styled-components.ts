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

import styled from "@emotion/styled"

export const StyledMolecule = styled.figure({
  margin: 0,
  // The RDKit SVG has intrinsic pixel dimensions; keep it responsive by
  // never letting it overflow its container.
  "& svg": {
    maxWidth: "100%",
    height: "auto",
  },
})

export const StyledMoleculeCaption = styled.figcaption(({ theme }) => ({
  marginTop: theme.spacing.sm,
  textAlign: "center",
  color: theme.colors.fadedText60,
  fontSize: theme.fontSizes.sm,
}))
