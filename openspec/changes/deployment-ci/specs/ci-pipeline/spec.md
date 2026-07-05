## ADDED Requirements

### Requirement: Run linting on every push and PR
The CI pipeline SHALL run `ruff check .` on every push to any branch and every pull request.

#### Scenario: Linting passes
- **WHEN** a developer pushes code that passes all ruff rules
- **THEN** the CI lint job succeeds with exit code 0

#### Scenario: Linting fails
- **WHEN** a developer pushes code with linting violations
- **THEN** the CI lint job fails, blocking merge if branch protection is enabled

### Requirement: Run tests on every push and PR
The CI pipeline SHALL run `pytest tests/ -v` on every push to any branch and every pull request.

#### Scenario: All tests pass
- **WHEN** a developer pushes code and all pytest tests pass
- **THEN** the CI test job succeeds with exit code 0

#### Scenario: Test failure blocks deploy
- **WHEN** a test fails on a push to main
- **THEN** the deploy job does not execute (depends on test job success)

### Requirement: Deploy to production on merge to main
The CI pipeline SHALL automatically deploy to the production VPS when code is merged to the main branch and all tests pass.

#### Scenario: Successful deploy after merge
- **WHEN** a PR is merged to main and CI tests pass
- **THEN** the deploy job SSHs into the VPS and executes the deploy script

#### Scenario: Deploy skipped on non-main branch
- **WHEN** a developer pushes to a feature branch
- **THEN** only lint and test jobs run; the deploy job is skipped

### Requirement: Deploy completes within 60 seconds
The deploy script SHALL complete (git pull + pip install + restart) in under 60 seconds under normal conditions.

#### Scenario: Normal deploy timing
- **WHEN** the deploy script runs with no new pip dependencies
- **THEN** it completes in under 30 seconds (git pull + restart only)

#### Scenario: Deploy with new dependencies
- **WHEN** the deploy script runs with new entries in requirements.txt
- **THEN** it completes in under 60 seconds (includes pip install)

### Requirement: CI uses GitHub Secrets for VPS access
The CI pipeline SHALL use GitHub Secrets (not hardcoded values) for VPS_HOST, VPS_USER, and VPS_SSH_KEY.

#### Scenario: Secrets configured correctly
- **WHEN** the deploy job runs with valid GitHub Secrets
- **THEN** SSH connection succeeds and deploy script executes

#### Scenario: Missing secrets
- **WHEN** the deploy job runs but secrets are not configured
- **THEN** the deploy job fails with a clear error (SSH connection refused)
