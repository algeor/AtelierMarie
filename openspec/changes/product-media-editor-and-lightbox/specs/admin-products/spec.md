## ADDED Requirements

### Requirement: Product image crop/rotate/zoom editor
When an admin selects an image file in the product form, the system SHALL present an interactive editor that allows cropping, rotating, and zooming/panning the image, with the crop frame locked to the storefront display aspect ratio of `4/5`. On confirmation, the framed result SHALL be exported (client-side, via canvas) to an image blob, and that blob — not the originally selected file — SHALL enter the upload flow. On cancel, the selected file SHALL be discarded and not uploaded.

The editor SHALL sit in front of the existing image-management rules without weakening them: the 6-image-per-product limit, image ordering, primary-image selection, the 15–25MB soft-warning confirmation, and the >25MB client-side block all continue to apply to the exported blob.

#### Scenario: Editor opens on image selection
- **WHEN** an admin selects a JPEG or PNG file in the product form
- **THEN** a crop/rotate/zoom editor opens with the crop frame locked to a `4/5` aspect ratio

#### Scenario: Confirmed edit uploads the framed image
- **WHEN** the admin adjusts crop/rotation/zoom and confirms
- **THEN** the framed image is exported to a blob and that blob is added to the pending upload set (the original selected file is not uploaded)

#### Scenario: Cancelled edit discards the file
- **WHEN** the admin cancels the editor
- **THEN** no image is added to the pending upload set and no upload occurs

#### Scenario: Framed output matches storefront framing
- **WHEN** the framed blob is uploaded and later displayed on the storefront card
- **THEN** the visible framing matches what the admin saw in the editor (no additional `object-cover` cropping surprises), because both use the `4/5` aspect ratio

#### Scenario: Existing image limits still apply to the exported blob
- **WHEN** adding the exported blob would exceed 6 images, or the blob exceeds 25MB
- **THEN** the existing limit/size rules reject or warn exactly as they do for a directly selected file
