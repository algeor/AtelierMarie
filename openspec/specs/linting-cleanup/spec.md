## ADDED Requirements

### Requirement: Zero ruff violations
The Python codebase SHALL pass `ruff check .` with zero errors and `ruff format --check .` with zero reformats needed.

#### Scenario: CI lint check
- **WHEN** `ruff check .` is run on the codebase
- **THEN** it SHALL report "All checks passed!" with exit code 0

#### Scenario: CI format check
- **WHEN** `ruff format --check .` is run on the codebase
- **THEN** it SHALL report 0 files would be reformatted

### Requirement: Line length within 100 characters
All Python source lines SHALL be at most 100 characters, enforced by ruff rule E501.

#### Scenario: Long string in config
- **WHEN** a configuration value or docstring exceeds 100 characters
- **THEN** it SHALL be wrapped across multiple lines or extracted to a variable

### Requirement: Sorted import blocks
All Python modules SHALL have import blocks sorted per ruff rule I001 (isort-compatible ordering).

#### Scenario: cart_service.py imports
- **WHEN** `app/services/cart_service.py` imports are checked
- **THEN** they SHALL be sorted: stdlib → third-party → local, alphabetical within groups
