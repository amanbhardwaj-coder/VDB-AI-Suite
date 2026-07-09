import io
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ----------------------------
# Streamlit setup
# ----------------------------
st.set_page_config(page_title="Fast URL Checker", layout="wide")
st.title("⚡ Fast & Reliable URL Checker (CSV upload or CSV URL)")


# ----------------------------
# URL + CSV helpers
# ----------------------------
def normalize_url(u: str) -> str:
    if u is None or pd.isna(u):
        return ""
    return str(u).strip().replace("\r", "")


def ensure_scheme(url: str) -> str:
    if url and not re.match(r"^https?://", url, re.IGNORECASE):
        return "https://" + url
    return url


def infer_url_columns(df: pd.DataFrame) -> list[str]:
    likely = []
    for c in df.columns:
        name = str(c).lower()
        if "url" in name or "link" in name:
            likely.append(c)
    return likely


def to_google_export_url(url: str) -> str | None:
    if not url:
        return None

    m = re.search(r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    if not m:
        return None

    sheet_id = m.group(1)
    gid = "0"

    gid_m = re.search(r"[?#&]gid=(\d+)", url)
    if gid_m:
        gid = gid_m.group(1)

    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def fetch_text(url: str, timeout: int = 30) -> str:
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.text


def read_csv_flexible(text: str, sep: str = ",", header_mode: str = "infer") -> pd.DataFrame:
    header = "infer" if header_mode == "infer" else None

    try:
        return pd.read_csv(io.StringIO(text), sep=sep, header=header)
    except Exception:
        return pd.read_csv(
            io.StringIO(text),
            sep=sep,
            header=header,
            engine="python",
            on_bad_lines="skip",
        )


# ----------------------------
# HTTP client
# ----------------------------
def make_session(connect_timeout: int, read_timeout: int, total_retries: int) -> requests.Session:
    s = requests.Session()

    retry = Retry(
        total=total_retries,
        connect=total_retries,
        read=total_retries,
        status=total_retries,
        backoff_factor=0.4,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["HEAD", "GET"]),
        raise_on_status=False,
    )

    adapter = HTTPAdapter(
        max_retries=retry,
        pool_connections=200,
        pool_maxsize=200,
    )

    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s._timeout = (connect_timeout, read_timeout)

    return s


# ----------------------------
# URL checker
# ----------------------------
def check_one(
    session: requests.Session,
    url: str,
    prefer_get: bool,
    follow_redirects: bool,
) -> dict:
    raw = normalize_url(url)

    if raw == "":
        return {
            "URL": "",
            "Status Code": "000",
            "Status": "Empty URL",
        }

    u = ensure_scheme(raw)

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; URLChecker/1.0)",
        "Accept": "*/*",
    }

    try:
        if prefer_get:
            resp = session.get(
                u,
                headers=headers,
                allow_redirects=follow_redirects,
                timeout=session._timeout,
                stream=True,
            )
        else:
            resp = session.head(
                u,
                headers=headers,
                allow_redirects=follow_redirects,
                timeout=session._timeout,
            )

            if resp.status_code in (403, 405):
                resp = session.get(
                    u,
                    headers=headers,
                    allow_redirects=follow_redirects,
                    timeout=session._timeout,
                    stream=True,
                )

        code = resp.status_code

        try:
            resp.close()
        except Exception:
            pass

        if code == 200:
            msg = "Working"
        else:
            msg = f"Not Working (Code: {code})"

        return {
            "URL": u,
            "Status Code": str(code),
            "Status": msg,
        }

    except requests.exceptions.RequestException:
        return {
            "URL": u,
            "Status Code": "000",
            "Status": "Could not connect (Code: 000)",
        }


def run_checks(
    urls: list[str],
    workers: int,
    connect_timeout: int,
    read_timeout: int,
    retries: int,
    prefer_get: bool,
    follow_redirects: bool,
) -> pd.DataFrame:
    session = make_session(connect_timeout, read_timeout, retries)
    results = [None] * len(urls)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        future_map = {
            ex.submit(check_one, session, urls[i], prefer_get, follow_redirects): i
            for i in range(len(urls))
        }

        done = 0
        total = len(urls)
        prog = st.progress(0)
        status = st.empty()

        for fut in as_completed(future_map):
            i = future_map[fut]
            results[i] = fut.result()
            done += 1

            if total:
                prog.progress(int(done * 100 / total))

            if done % 25 == 0 or done == total:
                status.write(f"Checked {done}/{total}")

    return pd.DataFrame(results)


# ----------------------------
# UI: input
# ----------------------------
st.subheader("1) Load URLs")

mode = st.radio("Input method", ["Upload CSV", "CSV via URL"], horizontal=True)

c1, c2, c3, c4 = st.columns(4)

with c1:
    workers = st.slider("Workers (parallel)", 1, 300, 80, 1)

with c2:
    connect_timeout = st.slider("Connect timeout (s)", 1, 20, 5, 1)

with c3:
    read_timeout = st.slider("Read timeout (s)", 1, 30, 10, 1)

with c4:
    retries = st.slider("Retries (for 000/429/5xx)", 0, 5, 2, 1)

c5, c6 = st.columns(2)

with c5:
    prefer_get = st.checkbox("Prefer GET (more reliable for CDNs/images)", value=True)

with c6:
    follow_redirects = st.checkbox("Follow redirects", value=True)

sep = st.selectbox("CSV delimiter", options=[",", "\t", ";", "|"], index=0)
header_mode = st.selectbox("CSV header", options=["infer", "none"], index=0)

df = None

if mode == "Upload CSV":
    up = st.file_uploader("Upload CSV", type=["csv"])

    if up is not None:
        df = pd.read_csv(up, sep=sep, header="infer" if header_mode == "infer" else None)

else:
    csv_url = st.text_input("Paste CSV URL (Google Sheets supported)")

    if csv_url:
        export_url = to_google_export_url(csv_url)
        effective_url = export_url or csv_url

        if export_url:
            st.info("Google Sheets link detected → using CSV export URL")
            st.code(effective_url)

        try:
            text = fetch_text(effective_url)

            if "<html" in text[:2000].lower():
                st.warning(
                    "Looks like HTML. The sheet may be private. "
                    "Make it 'Anyone with the link' or use a direct export URL."
                )

                with st.expander("Preview first 2KB"):
                    st.code(text[:2000])

            df = read_csv_flexible(text, sep=sep, header_mode=header_mode)

        except Exception as e:
            st.error(f"Could not fetch/read CSV from URL: {e}")


# ----------------------------
# UI: process
# ----------------------------
if df is not None:
    st.subheader("2) Pick URL columns")
    st.dataframe(df.head(20), use_container_width=True)

    detected_cols = infer_url_columns(df)

    if detected_cols:
        st.info(f"Detected URL columns: **{', '.join(map(str, detected_cols))}**")

    url_cols = st.multiselect(
        "Select one or more columns containing URLs",
        options=list(df.columns),
        default=detected_cols,
    )

    st.subheader("3) Run checks")

    if st.button("Run URL Check ⚡", type="primary"):
        if not url_cols:
            st.error("Please select at least one URL column.")
            st.stop()

        result_df = df.copy()

        all_urls = []
        mapping = []

        for row_idx in range(len(df)):
            for col in url_cols:
                all_urls.append(normalize_url(df.at[row_idx, col]))
                mapping.append((row_idx, col))

        checked_df = run_checks(
            urls=all_urls,
            workers=workers,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            retries=retries,
            prefer_get=prefer_get,
            follow_redirects=follow_redirects,
        )

        for i, result in checked_df.iterrows():
            row_idx, col = mapping[i]

            result_df.at[row_idx, f"{col} Checked URL"] = result["URL"]
            result_df.at[row_idx, f"{col} Status"] = result["Status"]
            result_df.at[row_idx, f"{col} Status Code"] = result["Status Code"]

        st.subheader("Results")
        st.dataframe(result_df, use_container_width=True)

        status_cols = [f"{col} Status Code" for col in url_cols]

        ok = sum((result_df[col] == "200").sum() for col in status_cols)
        not_ok = sum((result_df[col] != "200").sum() for col in status_cols)

        st.write(f"✅ Working (200): **{ok}**  |  ❌ Not 200 / 000: **{not_ok}**")

        out = result_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "⬇️ Download results.csv",
            data=out,
            file_name="results.csv",
            mime="text/csv",
        )
