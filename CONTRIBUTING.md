# Contributing to GeoFeed

Thank you for your interest in contributing! All contributions are welcome — bug reports, feature suggestions, documentation improvements, and code changes.

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/geofeed.git
   cd geofeed
   ```
3. **Create a branch** for your change:
   ```bash
   git checkout -b feature/my-improvement
   ```
4. **Set up the environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install pytest pytest-asyncio
   ```

## Making Changes

### Bug Reports

Open a [GitHub Issue](https://github.com/foxtrotglobal/geofeed/issues) and include:
- A clear description of the bug
- Steps to reproduce it
- Expected vs. actual behavior
- Your Python version and OS

### Feature Requests

Open a [GitHub Issue](https://github.com/foxtrotglobal/geofeed/issues) with a description of what you'd like and why it would be useful.

### Code Changes

- Keep pull requests focused — one logical change per PR
- Write or update tests for any new behavior
- Make sure all existing tests pass before submitting:
  ```bash
  pytest -v
  ```
- Follow the existing code style (no linter is enforced, but match the surrounding code)

## Adding a New Platform Provider

GeoFeed is designed to be extended. To add a new platform:

1. Create `providers/myplatform.py` and subclass `BaseProvider`:
   ```python
   from providers.base import BaseProvider
   from models import GeoPost, SearchParams

   class MyPlatformProvider(BaseProvider):
       name = "myplatform"
       color = "#123456"  # Marker color on the map

       def is_configured(self) -> bool:
           return bool(self.api_key)

       async def search(self, params: SearchParams) -> list[GeoPost]:
           # Implement geo search here
           ...
   ```

2. Register it in both `server.py` and `main.py` under `ALL_PROVIDERS`:
   ```python
   from providers.myplatform import MyPlatformProvider
   ALL_PROVIDERS = {
       ...
       "myplatform": MyPlatformProvider,
   }
   ```

3. Add credentials to `config.yaml.example`

4. Write tests in `tests/test_providers.py` using mocked HTTP responses

## Submitting a Pull Request

1. Push your branch:
   ```bash
   git push origin feature/my-improvement
   ```
2. Open a pull request against the `main` branch on GitHub
3. Fill in the PR description explaining what changed and why
4. The CI workflow will automatically run all tests against Python 3.11 and 3.12

## Code of Conduct

Please be respectful and constructive in all interactions. This project follows the [Contributor Covenant](https://www.contributor-covenant.org/) code of conduct.
