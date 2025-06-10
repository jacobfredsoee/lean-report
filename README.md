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

**After installing mise:**

- Trust the project (so mise will load environment variables and tools):

```sh
mise trust .
```

- Activate mise shell integration (so env vars and tools are loaded automatically):

```sh
mise activate
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

---

## 4. Install Python and dependencies

If you have a `pyproject.toml` or `requirements.txt`, run:

```sh
uv venv
uv sync
```

---

## 5. Run the Streamlit app

From the `src/` directory (or project root if you prefer):

```sh
streamlit run src/app.py
```

---