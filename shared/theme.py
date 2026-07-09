from __future__ import annotations

import streamlit as st


def apply_theme() -> None:
    st.markdown(
        """
<style>
:root {
  --vdb-bg: #0b1020;
  --vdb-panel: rgba(255,255,255,.055);
  --vdb-panel-2: rgba(255,255,255,.08);
  --vdb-border: rgba(255,255,255,.14);
  --vdb-text: #f5f7fb;
  --vdb-muted: rgba(245,247,251,.68);
  --vdb-accent: #7c6cff;
  --vdb-accent-2: #25d0ff;
  --vdb-good: #35d07f;
  --vdb-warn: #ffbe55;
}

.block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1450px; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0b1020 0%, #11172b 100%); }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: rgba(245,247,251,.8); }
[data-testid="stMetric"] {
  background: var(--vdb-panel);
  border: 1px solid var(--vdb-border);
  border-radius: 18px;
  padding: 1rem;
  box-shadow: 0 10px 28px rgba(0,0,0,.16);
}
.stButton > button, .stDownloadButton > button, [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"] {
  border-radius: 14px !important;
  min-height: 2.75rem;
  font-weight: 700 !important;
}
.vdb-hero {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--vdb-border);
  background:
    radial-gradient(circle at top left, rgba(124,108,255,.34), transparent 35%),
    radial-gradient(circle at bottom right, rgba(37,208,255,.18), transparent 35%),
    linear-gradient(135deg, rgba(255,255,255,.09), rgba(255,255,255,.035));
  border-radius: 28px;
  padding: 2rem 2.1rem;
  margin-bottom: 1.15rem;
  box-shadow: 0 24px 70px rgba(0,0,0,.22);
}
.vdb-hero h1 { margin: 0; font-size: clamp(2rem, 4vw, 3.5rem); line-height: 1; letter-spacing: -.06em; }
.vdb-hero p { margin: .75rem 0 0 0; color: var(--vdb-muted); font-size: 1.02rem; max-width: 880px; }
.vdb-hero .vdb-badge-row { margin-top: 1rem; display: flex; gap: .5rem; flex-wrap: wrap; }
.vdb-pill {
  display: inline-flex; align-items: center; gap: .35rem;
  border: 1px solid var(--vdb-border);
  background: rgba(255,255,255,.07);
  border-radius: 999px;
  padding: .32rem .7rem;
  color: rgba(245,247,251,.82);
  font-size: .82rem;
  font-weight: 700;
}
.vdb-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; }
@media (max-width: 1050px) { .vdb-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 680px) { .vdb-grid { grid-template-columns: 1fr; } }
.vdb-card {
  border: 1px solid var(--vdb-border);
  background: linear-gradient(180deg, rgba(255,255,255,.075), rgba(255,255,255,.035));
  border-radius: 22px;
  padding: 1.05rem;
  min-height: 182px;
  box-shadow: 0 14px 42px rgba(0,0,0,.16);
}
.vdb-card:hover { border-color: rgba(124,108,255,.58); transform: translateY(-1px); transition: all .16s ease; }
.vdb-card-top { display:flex; justify-content: space-between; gap: .75rem; align-items:flex-start; }
.vdb-icon {
  width: 42px; height: 42px; border-radius: 15px;
  display:flex; align-items:center; justify-content:center;
  background: linear-gradient(135deg, rgba(124,108,255,.26), rgba(37,208,255,.16));
  border: 1px solid var(--vdb-border);
  font-size: 1.25rem;
}
.vdb-card h3 { margin: .75rem 0 .35rem; font-size: 1.05rem; letter-spacing: -.02em; }
.vdb-card p { margin: 0; color: var(--vdb-muted); font-size: .9rem; line-height: 1.42; min-height: 3.8rem; }
.vdb-card-footer { margin-top: .9rem; display:flex; gap:.4rem; flex-wrap:wrap; }
.vdb-status { font-size:.75rem; padding:.2rem .55rem; border-radius:999px; border:1px solid var(--vdb-border); color:rgba(245,247,251,.8); }
.status-built-in { background: rgba(53,208,127,.14); border-color: rgba(53,208,127,.34); }
.status-ready { background: rgba(124,108,255,.16); border-color: rgba(124,108,255,.34); }
.status-linked { background: rgba(255,190,85,.13); border-color: rgba(255,190,85,.28); }
.vdb-section-title { margin: 1.4rem 0 .8rem; display:flex; align-items:center; justify-content:space-between; gap:1rem; }
.vdb-section-title h2 { margin: 0; font-size: 1.25rem; letter-spacing: -.03em; }
.vdb-muted { color: var(--vdb-muted); }
.vdb-command {
  border: 1px solid var(--vdb-border);
  background: rgba(0,0,0,.2);
  border-radius: 18px;
  padding: 1rem;
}
.vdb-mini-row { display:grid; grid-template-columns: 1fr 1fr; gap:1rem; }
@media (max-width: 800px) { .vdb-mini-row { grid-template-columns: 1fr; } }
.vdb-timeline {
  border-left: 2px solid rgba(124,108,255,.35);
  margin-left: .45rem;
  padding-left: 1rem;
}
.vdb-step { margin-bottom: 1rem; }
.vdb-step b { color: #fff; }
.vdb-step span { display:block; color:var(--vdb-muted); font-size:.9rem; margin-top:.1rem; }
</style>
        """,
        unsafe_allow_html=True,
    )
