import os
from datetime import datetime, timezone
from typing import Optional

import streamlit as st
from dotenv import load_dotenv

from sandbox_runner import run_analysis_in_sandbox
from vercel_client import VercelAPIError, VercelClient

load_dotenv()

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Vercel Deployment Monitor",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* ── Global typography & palette ─────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Sidebar polish ──────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #f8f9fb 0%, #eef1f6 100%);
    border-right: 1px solid rgba(0,0,0,0.06);
}

/* ── Cards / containers ──────────────────────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 12px !important;
    transition: box-shadow 0.2s ease, transform 0.15s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: 0 4px 20px rgba(0,0,0,0.12);
    transform: translateY(-1px);
}

/* ── Metric cards ────────────────────────────────────────────────── */
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #f8f9fb 0%, #f0f2f6 100%);
    border: 1px solid rgba(0,0,0,0.06);
    border-radius: 12px;
    padding: 16px 20px;
}
div[data-testid="stMetric"] label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    opacity: 0.6;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 1.1rem !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* ── Primary buttons ─────────────────────────────────────────────── */
button[kind="primary"] {
    background: linear-gradient(135deg, #0070f3 0%, #0051cc 100%) !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em;
    transition: all 0.2s ease !important;
}
button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(0,112,243,0.4) !important;
}

/* ── Secondary buttons ───────────────────────────────────────────── */
button[kind="secondary"] {
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}

/* ── Prevent button text from wrapping ───────────────────────────── */
button[kind="primary"] p,
button[kind="secondary"] p,
button p {
    white-space: nowrap !important;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* ── Tabs ────────────────────────────────────────────────────────── */
button[data-baseweb="tab"] {
    font-weight: 600 !important;
    letter-spacing: 0.01em;
    border-radius: 8px 8px 0 0 !important;
}

/* ── Code blocks (logs) ──────────────────────────────────────────── */
pre {
    border-radius: 10px !important;
    border: 1px solid rgba(0,0,0,0.08) !important;
    font-size: 0.82rem !important;
    line-height: 1.6 !important;
}

/* ── Expanders ───────────────────────────────────────────────────── */
details {
    border-radius: 12px !important;
    border: 1px solid rgba(0,0,0,0.08) !important;
}
details summary {
    font-weight: 600;
}

/* ── Dividers ────────────────────────────────────────────────────── */
hr {
    border-color: rgba(0,0,0,0.08) !important;
    margin: 1.2rem 0 !important;
}

/* ── Toast messages ──────────────────────────────────────────────── */
div[data-testid="stToast"] {
    border-radius: 10px !important;
}

/* ── Selectbox ───────────────────────────────────────────────────── */
div[data-baseweb="select"] {
    border-radius: 8px !important;
}

/* ── Hero section animations ─────────────────────────────────────── */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
}
.hero-title {
    font-size: 2.8rem;
    font-weight: 700;
    background: linear-gradient(135deg, #0070f3, #0051cc, #7928ca);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: fadeInUp 0.6s ease-out;
    margin-bottom: 0.3rem;
}
.hero-subtitle {
    font-size: 1.15rem;
    color: #555;
    font-weight: 400;
    animation: fadeInUp 0.6s ease-out 0.1s both;
    margin-bottom: 2rem;
}
.feature-card {
    background: linear-gradient(135deg, #ffffff 0%, #f8f9fb 100%);
    border: 1px solid rgba(0,0,0,0.08);
    border-radius: 16px;
    padding: 28px 24px;
    transition: all 0.25s ease;
    animation: fadeInUp 0.5s ease-out both;
}
.feature-card:hover {
    border-color: rgba(0,112,243,0.3);
    box-shadow: 0 8px 30px rgba(0,112,243,0.08);
    transform: translateY(-2px);
}
.feature-icon {
    font-size: 1.6rem;
    margin-bottom: 10px;
    display: block;
}
.feature-title {
    font-weight: 600;
    font-size: 1rem;
    margin-bottom: 6px;
    color: #1a1a1a;
}
.feature-desc {
    font-size: 0.88rem;
    color: #666;
    line-height: 1.5;
}
.step-number {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: linear-gradient(135deg, #0070f3, #0051cc);
    color: white;
    font-weight: 700;
    font-size: 0.82rem;
    margin-right: 10px;
    flex-shrink: 0;
}
.step-row {
    display: flex;
    align-items: center;
    padding: 10px 0;
    font-size: 0.95rem;
    color: #333;
}
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.82rem;
}
.badge-ready  { background: rgba(0,200,83,0.1); color: #1b8a3e; }
.badge-error  { background: rgba(255,23,68,0.1); color: #c62828; }
.badge-building { background: rgba(255,171,0,0.1); color: #e65100; }
.badge-queued { background: rgba(120,120,120,0.1); color: #616161; }
.badge-canceled { background: rgba(120,120,120,0.1); color: #757575; }

/* ── Deployment row styling ──────────────────────────────────────── */
.dep-name {
    font-weight: 600;
    font-size: 0.95rem;
    margin-bottom: 2px;
    color: #1a1a1a;
}
.dep-url {
    font-size: 0.78rem;
    color: #888;
    font-family: 'SF Mono', 'Fira Code', monospace;
}
.dep-meta {
    font-size: 0.8rem;
    color: #777;
}
</style>
""", unsafe_allow_html=True)

# ── Session state initialisation ─────────────────────────────────────────────

_DEFAULTS = {
    "client": None,
    "user_name": "",
    "teams": [],
    "selected_team_id": None,   # None = personal account
    "projects": [],
    "selected_project_id": None,
    "deployments": [],
    "selected_dep_id": None,
    "dep_detail": None,
    "dep_events": [],
    "ai_analysis": "",
    "analyzing": False,
    "last_project_id": "__unset__",
    "last_team_id": "__unset__",
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Auto-connect from .env on first load ──────────────────────────────────────

def _auto_connect():
    token = os.getenv("VERCEL_TOKEN", "").strip()
    if not token or st.session_state.client:
        return
    try:
        c = VercelClient(token=token, team_id=None)
        user_data = c.validate_token()
        user = user_data.get("user", {})
        name = user.get("name") or user.get("username") or user.get("email", "Unknown")

        # Many Vercel accounts have a defaultTeamId — all projects live there
        default_team_id = user.get("defaultTeamId")
        teams = c.get_teams()

        # If we couldn't list teams but user has a default team, use it
        if not teams and default_team_id:
            c.team_id = default_team_id
            st.session_state.selected_team_id = default_team_id
        elif teams:
            # Auto-select the default team if it's in the list
            for t in teams:
                if t.get("id") == default_team_id:
                    c.team_id = default_team_id
                    st.session_state.selected_team_id = default_team_id
                    break

        # Warn if the token is limited-scope (won't see projects/deployments)
        if user.get("limited"):
            st.session_state["_limited_token"] = True
        else:
            st.session_state["_limited_token"] = False

        st.session_state.client = c
        st.session_state.user_name = name
        st.session_state.teams = teams
        st.session_state["_default_team_id"] = default_team_id
    except VercelAPIError:
        pass  # Invalid token — user will connect manually

_auto_connect()

# ── Constants ─────────────────────────────────────────────────────────────────

STATE_DOT = {
    "READY": "🟢",
    "ERROR": "🔴",
    "BUILDING": "🟡",
    "INITIALIZING": "🟡",
    "QUEUED": "⚪",
    "CANCELED": "⚫",
}

STATE_LABEL_COLOR = {
    "READY": "green",
    "ERROR": "red",
    "BUILDING": "orange",
    "INITIALIZING": "orange",
    "QUEUED": "gray",
    "CANCELED": "gray",
}

# ── Helpers ───────────────────────────────────────────────────────────────────


def age(ts_ms: Optional[int]) -> str:
    if not ts_ms:
        return "—"
    try:
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        secs = int((datetime.now(tz=timezone.utc) - dt).total_seconds())
        if secs < 60:
            return f"{secs}s ago"
        if secs < 3600:
            return f"{secs // 60}m ago"
        if secs < 86400:
            return f"{secs // 3600}h ago"
        return f"{secs // 86400}d ago"
    except Exception:
        return "—"


def dep_state(dep: dict) -> str:
    return dep.get("state") or dep.get("readyState") or "QUEUED"


# ── Sidebar ───────────────────────────────────────────────────────────────────


def render_sidebar():
    with st.sidebar:
        st.markdown(
            '<div style="text-align:center; padding: 8px 0 4px;">'
            '<span style="font-size:1.6rem;">🚀</span><br>'
            '<span style="font-weight:700; font-size:1.1rem; letter-spacing:-0.01em;">Vercel Monitor</span>'
            "</div>",
            unsafe_allow_html=True,
        )
        st.divider()
        st.markdown('<span style="font-weight:600; font-size:0.85rem; text-transform:uppercase; letter-spacing:0.05em; opacity:0.5;">Configuration</span>', unsafe_allow_html=True)
        st.markdown("")  # spacer

        vercel_token = st.text_input(
            "Vercel API Token",
            value=os.getenv("VERCEL_TOKEN", ""),
            type="password",
            placeholder="ver_…",
            help="Create one at vercel.com/account/tokens",
        )
        openai_key = st.text_input(
            "OpenAI API Key",
            value=os.getenv("OPENAI_API_KEY", ""),
            type="password",
            placeholder="sk-…",
            help="Required for AI error analysis",
        )
        daytona_key = st.text_input(
            "Daytona API Key",
            value=os.getenv("DAYTONA_API_KEY", ""),
            type="password",
            placeholder="day-…",
            help="Required for running AI analysis in an isolated sandbox",
        )

        if st.button("Connect", type="primary", use_container_width=True):
            if not vercel_token:
                st.error("Vercel token is required.")
            else:
                with st.spinner("Connecting…"):
                    try:
                        c = VercelClient(token=vercel_token, team_id=None)
                        user_data = c.validate_token()
                        user = user_data.get("user", {})
                        name = user.get("name") or user.get("username") or user.get("email", "Unknown")
                        default_team_id = user.get("defaultTeamId")
                        teams = c.get_teams()

                        # Use defaultTeamId if teams endpoint is blocked
                        if not teams and default_team_id:
                            c.team_id = default_team_id
                        elif teams:
                            for t in teams:
                                if t.get("id") == default_team_id:
                                    c.team_id = default_team_id
                                    break

                        st.session_state.client = c
                        st.session_state.user_name = name
                        st.session_state.teams = teams
                        st.session_state.selected_team_id = c.team_id
                        st.session_state["_default_team_id"] = default_team_id
                        st.session_state.projects = []
                        st.session_state.deployments = []
                        st.session_state.selected_dep_id = None
                        st.session_state.last_project_id = "__unset__"
                        st.session_state.last_team_id = "__unset__"
                        st.toast(f"Connected as {name}", icon="✅")
                    except VercelAPIError as e:
                        st.error(str(e))
                        st.session_state.client = None

        # Store API keys for later use
        st.session_state["_openai_key"] = openai_key
        st.session_state["_daytona_key"] = daytona_key

        st.divider()
        if st.session_state.client:
            st.success(f"✅ Connected as **{st.session_state.user_name}**")
            if st.session_state.get("_limited_token"):
                st.error(
                    "⚠️ **Limited token detected.** Your token has restricted scope and "
                    "cannot access projects or deployments. Create a new token at "
                    "[vercel.com/account/tokens](https://vercel.com/account/tokens) "
                    "with **Full Account** scope."
                )

            # Team / account selector
            teams = st.session_state.teams
            if teams:
                team_options = {"Personal account": None}
                for t in teams:
                    team_options[t.get("name", t.get("slug", t.get("id", "?")))] = t.get("id")
                selected_team_name = st.selectbox(
                    "Account / Team",
                    options=list(team_options.keys()),
                    key="team_selector",
                )
                new_team_id = team_options[selected_team_name]
                if st.session_state.selected_team_id != new_team_id:
                    st.session_state.selected_team_id = new_team_id
                    # Update client's team_id and reload projects
                    st.session_state.client.team_id = new_team_id
                    st.session_state.projects = []
                    st.session_state.deployments = []
                    st.session_state.selected_dep_id = None
                    st.session_state.last_project_id = "__unset__"
        else:
            st.info("Enter credentials above to connect.")

        st.markdown(
            '<span style="font-weight:600; font-size:0.85rem; text-transform:uppercase; '
            'letter-spacing:0.05em; opacity:0.5;">Services</span>',
            unsafe_allow_html=True,
        )
        svc_ai = "🟢 AI analysis" if openai_key else "🔴 AI analysis (no key)"
        svc_sandbox = "🟢 Sandbox mode" if daytona_key else "⚪ Sandbox mode (local)"
        st.markdown(
            f'<div style="font-size:0.85rem; line-height:2;">{svc_ai}<br>{svc_sandbox}</div>',
            unsafe_allow_html=True,
        )

        st.divider()
        st.markdown(
            '<div style="font-size:0.72rem; opacity:0.4; line-height:1.8;">'
            '🔗 <a href="https://vercel.com/account/tokens" target="_blank" style="color:inherit;">Vercel Tokens</a> · '
            '<a href="https://platform.openai.com/api-keys" target="_blank" style="color:inherit;">OpenAI Keys</a> · '
            '<a href="https://app.daytona.io" target="_blank" style="color:inherit;">Daytona</a>'
            "</div>",
            unsafe_allow_html=True,
        )


# ── Deployment list ───────────────────────────────────────────────────────────


def render_deployment_list(client: VercelClient):
    # Project selector
    project_options = {"— All projects —": None}
    for p in st.session_state.projects:
        project_options[p.get("name", p.get("id", "?"))] = p.get("id")

    selected_name = st.selectbox(
        "Project",
        options=list(project_options.keys()),
        key="project_selector",
    )
    project_id = project_options[selected_name]

    # Reload deployments when project changes
    if st.session_state.last_project_id != project_id:
        st.session_state.last_project_id = project_id
        st.session_state.deployments = []
        st.session_state.selected_dep_id = None
        st.session_state.dep_detail = None
        st.session_state.dep_events = []
        st.session_state.ai_analysis = ""

    col_hdr, col_filter, col_refresh = st.columns([3, 2, 1])
    col_hdr.markdown("### 📡 Deployments")
    status_filter = col_filter.selectbox(
        "Status",
        options=["All", "Error", "Ready", "Building", "Canceled"],
        key="status_filter",
        label_visibility="collapsed",
    )
    if col_refresh.button("↻ Refresh", use_container_width=True, type="secondary"):
        st.session_state.deployments = []

    # Load projects lazily (covers the case where team was just switched)
    if not st.session_state.projects:
        with st.spinner("Loading projects…"):
            st.session_state.projects = client.get_projects()
        # Rebuild the selectbox options by re-running
        st.rerun()

    if not st.session_state.deployments:
        with st.spinner("Loading deployments…"):
            st.session_state.deployments = client.get_deployments(
                project_id=project_id, limit=20
            )

    deployments = st.session_state.deployments

    # Apply status filter
    if status_filter != "All":
        filter_map = {
            "Error": ("ERROR",),
            "Ready": ("READY",),
            "Building": ("BUILDING", "INITIALIZING", "QUEUED"),
            "Canceled": ("CANCELED",),
        }
        allowed = filter_map.get(status_filter, ())
        deployments = [d for d in deployments if dep_state(d) in allowed]
    if not deployments:
        st.info("No deployments found for this project.")
        team_id = client.team_id
        with st.expander("🔍 Debug info"):
            st.write(f"**team_id used:** `{team_id or 'None (personal)'}`")
            st.write(f"**project_id filter:** `{project_id or 'None (all)'}`")
            try:
                raw = client._get("/v6/deployments", {"limit": 5})
                st.write("**Raw /v6/deployments response:**")
                st.json(raw)
            except Exception as e:
                st.write(f"Error fetching raw data: {e}")
        return

    STATE_BADGE_CLASS = {
        "READY": "badge-ready",
        "ERROR": "badge-error",
        "BUILDING": "badge-building",
        "INITIALIZING": "badge-building",
        "QUEUED": "badge-queued",
        "CANCELED": "badge-canceled",
    }

    for dep in deployments:
        dep_id = dep.get("uid") or dep.get("id", "")
        state = dep_state(dep)
        dot = STATE_DOT.get(state, "⚪")
        badge_cls = STATE_BADGE_CLASS.get(state, "badge-queued")
        name = dep.get("name", "unknown")
        url = dep.get("url", "")
        created = dep.get("createdAt") or dep.get("created")
        meta = dep.get("meta", {})
        branch = meta.get("githubCommitRef") or meta.get("gitlabCommitRef") or ""
        commit = meta.get("githubCommitMessage") or meta.get("gitlabCommitMessage") or ""
        if commit and len(commit) > 55:
            commit = commit[:55] + "…"

        is_selected = st.session_state.selected_dep_id == dep_id

        with st.container(border=True):
            c1, c2, c3 = st.columns([5, 3, 2])
            with c1:
                st.markdown(f'<div class="dep-name">{name}</div>', unsafe_allow_html=True)
                if url:
                    st.markdown(f'<div class="dep-url">{url[:50]}</div>', unsafe_allow_html=True)
                if branch or commit:
                    parts = f"{'🌿 ' + branch if branch else ''} {commit}".strip()
                    st.markdown(f'<div class="dep-meta">{parts}</div>', unsafe_allow_html=True)
            with c2:
                st.markdown(
                    f'<span class="status-badge {badge_cls}">{dot} {state}</span>',
                    unsafe_allow_html=True,
                )
                st.caption(age(created))
            with c3:
                btn_label = "✓ Selected" if is_selected else "View"
                if st.button(
                    btn_label,
                    key=f"open_{dep_id}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    st.session_state.selected_dep_id = dep_id
                    st.session_state.dep_detail = None
                    st.session_state.dep_events = []
                    st.session_state.ai_analysis = ""
                    st.session_state.analyzing = False


# ── Deployment detail ─────────────────────────────────────────────────────────


def render_deployment_detail(client: VercelClient):
    dep_id = st.session_state.selected_dep_id
    if not dep_id:
        st.info("Select a deployment on the left to view its details.")
        return

    # Load detail if needed
    if not st.session_state.dep_detail:
        with st.spinner("Loading deployment…"):
            try:
                st.session_state.dep_detail = client.get_deployment(dep_id)
            except VercelAPIError as e:
                st.error(str(e))
                return

    # Load events if needed
    if not st.session_state.dep_events:
        with st.spinner("Fetching build logs…"):
            st.session_state.dep_events = client.get_readable_logs(dep_id)

    detail = st.session_state.dep_detail
    events = st.session_state.dep_events

    STATE_BADGE_CLASS = {
        "READY": "badge-ready",
        "ERROR": "badge-error",
        "BUILDING": "badge-building",
        "INITIALIZING": "badge-building",
        "QUEUED": "badge-queued",
        "CANCELED": "badge-canceled",
    }

    state = dep_state(detail)
    dot = STATE_DOT.get(state, "⚪")
    badge_cls = STATE_BADGE_CLASS.get(state, "badge-queued")
    name = detail.get("name", "unknown")
    url = detail.get("url", "")
    created = detail.get("createdAt") or detail.get("created")
    ready_at = detail.get("ready")
    error_msg = detail.get("errorMessage", "")

    # Header
    col_title, col_badge, col_close = st.columns([4, 2, 1])
    col_title.markdown(f"## {name}")
    col_badge.markdown(
        f'<div style="padding-top:12px"><span class="status-badge {badge_cls}">{dot} {state}</span></div>',
        unsafe_allow_html=True,
    )
    if col_close.button("✕ Close", key="close_detail"):
        st.session_state.selected_dep_id = None
        st.session_state.dep_detail = None
        st.session_state.dep_events = []
        st.session_state.ai_analysis = ""
        st.rerun()

    # Metrics row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Created", age(created))
    if ready_at and state == "READY":
        m2.metric("Build Time", f"{(ready_at - created) // 1000}s" if created else "—")
    elif state == "ERROR":
        m2.metric("Result", "Failed")
    else:
        m2.metric("Build Time", "—")
    if url:
        m3.markdown(f"**Preview URL**\n\n[{url[:40]}](https://{url})")
    m4.markdown("")  # keep grid balanced

    if error_msg:
        st.error(f"**Error:** {error_msg}")

    st.divider()

    # Tabs: Logs | AI Analysis
    tab_logs, tab_ai = st.tabs(["📋 Build Logs", "🤖 AI Analysis"])

    with tab_logs:
        render_logs(events)

    with tab_ai:
        render_ai_analysis(detail, events, state)


def render_logs(events: list):
    if not events:
        st.info("No log events captured for this deployment.")
        return

    # Build display lines
    all_lines = []
    error_lines = []

    for event in events:
        t = event.get("type", "")
        payload = event.get("payload", event)
        text = (payload.get("text") or "").strip()
        if not text:
            continue
        if t == "stderr":
            all_lines.append(f"[ERR] {text}")
            error_lines.append(text)
        elif t == "command":
            all_lines.append(f"[CMD] $ {text}")
        elif t == "exit":
            all_lines.append(f"[EXIT] code={text}")
        elif t == "fatal":
            all_lines.append(f"[FATAL] {text}")
            error_lines.append(text)
        else:
            all_lines.append(text)

    if error_lines:
        st.warning(f"🚨 **{len(error_lines)} error line(s)** found in build logs")

    sub_all, sub_err = st.tabs([f"All ({len(all_lines)} lines)", f"Errors ({len(error_lines)})"])

    with sub_all:
        # Show last 300 lines to avoid overwhelming the UI
        display = all_lines[-300:]
        if len(all_lines) > 300:
            st.caption(f"Showing last 300 of {len(all_lines)} lines")
        st.code("\n".join(display), language=None)

    with sub_err:
        if error_lines:
            st.code("\n".join(error_lines), language=None)
        else:
            st.success("No error output found.")


def render_ai_analysis(detail: dict, events: list, state: str):
    openai_key = st.session_state.get("_openai_key", "")
    daytona_key = st.session_state.get("_daytona_key", "")

    is_error = state in ("ERROR", "CANCELED")
    has_stderr = any(
        e.get("type") in ("stderr", "fatal") and (e.get("payload", e).get("text") or "").strip()
        for e in events
    )

    if not is_error and not has_stderr:
        st.success("✅ Deployment looks healthy — no AI analysis needed.")
        return

    if not openai_key:
        st.warning("Add an **OpenAI API Key** in the sidebar to enable AI-powered analysis.")
        return

    if not daytona_key:
        st.warning("Add a **Daytona API Key** in the sidebar to enable AI analysis. "
                    "All analysis runs in an isolated Daytona sandbox for data security.")
        return

    st.caption("🔒 Analysis will run in an isolated Daytona sandbox")

    # Show cached analysis if available
    if st.session_state.ai_analysis and not st.session_state.analyzing:
        st.markdown(st.session_state.ai_analysis)
        if st.button("🔄 Re-analyze", key="reanalyze"):
            st.session_state.ai_analysis = ""
            st.session_state.analyzing = False
            st.rerun()
        return

    # Trigger analysis
    if not st.session_state.analyzing:
        if st.button("🤖 Analyze with AI", type="primary", key="analyze_btn"):
            st.session_state.analyzing = True
            st.rerun()
        return

    # Run analysis in isolated Daytona sandbox
    st.info("🔒 Running analysis in Daytona sandbox…")
    try:
        with st.spinner("Creating sandbox and running analysis…"):
            result = run_analysis_in_sandbox(
                daytona_key=daytona_key,
                openai_key=openai_key,
                deployment=detail,
                events=events,
            )
        st.session_state.ai_analysis = result
        st.session_state.analyzing = False
        st.rerun()
    except Exception as e:
        st.error(f"Sandboxed analysis failed: {e}")
        st.session_state.analyzing = False


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    render_sidebar()

    if not st.session_state.client:
        st.markdown("")  # spacer
        st.markdown('<div class="hero-title">Vercel Deployment Monitor</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="hero-subtitle">'
            "Real-time deployment monitoring with AI-powered error analysis and sandboxed debugging."
            "</div>",
            unsafe_allow_html=True,
        )

        # Feature cards
        features = [
            ("📡", "Live Status", "See all recent deployments at a glance with real-time state tracking"),
            ("📋", "Build Logs", "Browse full build output with automatic error highlighting"),
            ("🤖", "AI Analysis", "Claude analyzes failures and suggests specific, actionable fixes"),
            ("🔒", "Sandboxed", "Run analysis in isolated Daytona sandboxes for data security"),
        ]
        cols = st.columns(4, gap="medium")
        for i, (icon, title, desc) in enumerate(features):
            with cols[i]:
                st.markdown(
                    f'<div class="feature-card" style="animation-delay: {0.15 * i}s">'
                    f'<span class="feature-icon">{icon}</span>'
                    f'<div class="feature-title">{title}</div>'
                    f'<div class="feature-desc">{desc}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("")  # spacer

        # Getting started steps
        st.markdown("#### Get Started")
        steps = [
            ('Create a <a href="https://vercel.com/account/tokens" target="_blank">Vercel API token</a>'),
            ('Grab an <a href="https://platform.openai.com/api-keys" target="_blank">OpenAI API key</a>'),
            ('<em>(Optional)</em> Get a <a href="https://app.daytona.io" target="_blank">Daytona API key</a> for sandboxed analysis'),
            ("Enter credentials in the sidebar and click <strong>Connect</strong>"),
            ('Click <strong>Analyze with AI</strong> on any failed build'),
        ]
        for i, text in enumerate(steps, 1):
            st.markdown(
                f'<div class="step-row">'
                f'<span class="step-number">{i}</span>'
                f'<span>{text}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )
        return

    client = st.session_state.client
    left, right = st.columns([2, 3], gap="large")

    with left:
        render_deployment_list(client)

    with right:
        render_deployment_detail(client)


if __name__ == "__main__":
    main()
