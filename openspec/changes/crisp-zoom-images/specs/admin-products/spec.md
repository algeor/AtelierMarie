## ADDED Requirements

### Requirement: Large image upload soft-warning and hard block
The admin image upload UI SHALL check a selected file's size on the client before uploading and apply a tiered response: files under 15MB upload without prompting; files from 15MB up to and including 25MB trigger a confirmation dialog warning that the image is large before proceeding; files over 25MB are blocked client-side with an inline error and never uploaded. These client checks are UX only — the backend independently enforces the 25MB hard limit.

#### Scenario: Small file uploads silently
- **WHEN** the admin selects an image smaller than 15MB
- **THEN** the upload proceeds without any warning dialog

#### Scenario: Large file triggers confirmation
- **WHEN** the admin selects an image between 15MB and 25MB (inclusive)
- **THEN** a confirmation dialog appears warning the image is large and stating its size, with Cancel and "Add anyway" actions
- **AND** the upload proceeds only if the admin confirms; cancelling aborts the upload

#### Scenario: Oversized file blocked before upload
- **WHEN** the admin selects an image larger than 25MB
- **THEN** an inline error states the 25MB maximum and no upload request is made
