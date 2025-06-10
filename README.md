# Lean Report Viewer

A Streamlit app for browsing and visualizing backtest results from local folders or S3-compatible object storage.

---

## Prerequisites

- **Python 3.10+** (managed by [mise](https://mise.jdx.dev/))
- [mise](https://mise.jdx.dev/) (for environment and tool management)
- [uv](https://github.com/astral-sh/uv) (for fast Python package installs)

---

## 1. Install mise

Follow the [mise installation instructions](https://mise.jdx.dev/docs/installing/):

```sh
curl https://mise.jdx.dev/install.sh | bash
# Then restart your shell or follow the printed instructions
```

---

## 2. Install uv

With mise (recommended):

```sh
mise use -g uv@latest
```

Or with pip:

```sh
pip install uv
```

---

## 3. Set up S3 credentials

Create a file called `.mise.local.toml` in your project root (this file is git-ignored). Add your S3 credentials:

```toml
[env]
S3_ACCESS_KEY_ID = "your-access-key-id"
S3_SECRET_ACCESS_KEY = "your-secret-access-key"
S3_ENDPOINT_URL = "https://your-objectstorage-endpoint.com"
S3_REGION = "your-region"
```

- **Never commit secrets to git!**
- These environment variables will be automatically loaded if you have mise shell integration enabled.

---

## 4. Install Python and dependencies

If you have a `pyproject.toml` or `requirements.txt`, run:

```sh
uv venv
uv pip install -r requirements.txt
```

Or, if using `pyproject.toml`:

```sh
uv pip install .
```

---

## 5. Run the Streamlit app

From the `src/` directory (or project root if you prefer):

```sh
streamlit run src/app.py
```

---

## Troubleshooting

- Make sure you have enabled mise shell integration (`mise activate` or follow [mise shell setup](https://mise.jdx.dev/docs/shell/)).
- Check your environment variables:
  ```sh
  echo $S3_ACCESS_KEY_ID
  ```
- If you have issues with S3, double-check your credentials and endpoint.

---

## Project structure

- `src/app.py` — Main Streamlit app
- `src/s3_utils.py` — S3 utility functions
- `src/utils.py` — Local file utilities
- `.mise.local.toml` — Your local (uncommitted) secrets and environment variables
- `.gitignore` — Ignores `.mise.local.toml`, `.env`, and other sensitive files

---

## License

MIT 