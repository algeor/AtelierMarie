## ADDED Requirements

### Requirement: Product form manages multiple images
The admin product create/edit form SHALL let admins upload up to 6 images, reorder them, delete individual images, and choose which image is primary. The form SHALL reflect the current gallery state and enforce the 6-image cap in the UI.

#### Scenario: Upload multiple images
- **WHEN** an admin uploads several images in the product form
- **THEN** each appears in the form's image manager, the first becoming primary

#### Scenario: Reorder and set primary
- **WHEN** an admin drags images to reorder and marks one as primary
- **THEN** the new order and primary selection are saved via the image-management endpoints

#### Scenario: Delete an image
- **WHEN** an admin removes an image in the form
- **THEN** the image is deleted and, if it was primary, another becomes primary

#### Scenario: Cap enforced in UI
- **WHEN** a product already has 6 images
- **THEN** the upload control is disabled or shows a "maximum reached" message
