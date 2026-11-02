# Make sure

- The Druks GitHub App has access to it.
- Your local Druks backend is running your modified code.
- GitHub webhooks can reach that backend.
- Your agent harness is c

## Development setup

### Installing dependencies

This repo currently ships no package manifest or lockfile, so there are no dependencies to install. When a toolchain is added, run its install command (for example `npm install` or `pip install -r requirements.txt`) from the repo root before working on changes.

### Running tests

No test suite is configured yet. Once a harness is in place, run its default command (for example `npm test` or `pytest`) from the repo root to execute the suite.
