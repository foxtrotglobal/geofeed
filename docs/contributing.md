# Contributing

See the full [CONTRIBUTING.md](https://github.com/foxtrotglobal/geofeed/blob/main/CONTRIBUTING.md) for the complete guide.

## Quick start

```bash
git clone https://github.com/foxtrotglobal/geofeed.git
cd geofeed
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest pytest-asyncio
```

## Running tests

```bash
pytest -v          # All 169 tests — no API keys needed
```

## Adding a new platform

1. Create `providers/myplatform.py` — subclass `BaseProvider`, implement `search()` and `is_configured()`
2. Register it in `server.py` and `main.py` under `ALL_PROVIDERS`
3. Add credentials to `config.yaml.example`
4. Write tests in `tests/test_providers.py` using mocked HTTP responses
5. Add a page in `docs/platforms/myplatform.md`

See [Adding a Provider](reference/new-provider.md) for the full walkthrough.
