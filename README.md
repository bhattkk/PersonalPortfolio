# PersonalPortfolio
# This is personal portfolio report.
#
## Debug: Local Python environment (`.venv`)

If your editor can't resolve imports (for example `import redis`), create the virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

When to update: if you change `requirements.txt`, update the existing environment by re-installing:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

