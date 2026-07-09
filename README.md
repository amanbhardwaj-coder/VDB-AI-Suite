# VDB AI Suite

One Streamlit dashboard for VDB automation tools: inventory converters, Excel utilities, URL checks, JSON helpers, jewelry filter builders, and client-specific tools.

## Run locally

```bash
git clone https://github.com/amanbhardwaj-coder/VDB-AI-Suite.git
cd VDB-AI-Suite
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run Dashboard.py
```

## Optional: pull all existing tool repos into `modules/`

```bash
bash scripts/setup_modules.sh
```

After this, the dashboard will detect local modules. Smiling Rocks is already supported with a built-in adapter when the `Smiling_Rocks` repo exists under `modules/`.

## Current tool registry

- Smiling Rocks Converter
- Inventory Tool AI
- Inventory Tool 2.0
- Inventory Tool
- File Merge
- Excel Splitter
- URL Checker
- JSON to CSV
- Jewelry Filter Creation
- JL

## Integration pattern

Each tool repo can be integrated by exposing a `run()` function:

```python
def run():
    import streamlit as st
    st.title("My Tool")
    # existing app code
```

Then add it to the registry in `Dashboard.py`.
