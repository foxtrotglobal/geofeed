# Installation

## Prerequisites

- **Python 3.11+** — `python3 --version`
- **git**
- At least one API key — Bluesky, Mastodon, Telegram, Reddit, Aparat, and Rubika need none

## Steps

### 1. Clone

```bash
git clone https://github.com/foxtrotglobal/geofeed.git
cd geofeed
```

### 2. Virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright (for Snapchat)

```bash
playwright install chromium
```

!!! note
    Only required if you want Snapchat support. All other platforms work without Playwright.

### 5. Configure

```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml` with your credentials. See [Configuration](configuration.md) for details.

### 6. Run

```bash
python main.py --server        # web UI at http://localhost:5000
```
