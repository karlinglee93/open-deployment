import os
from datetime import datetime, timezone
from typing import Optional

import streamlit as st
from dotenv import load_dotenv

from ai_analyzer import stream_analysis
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
        st.title("🚀 Vercel Monitor")
        st.divider()
        st.subheader("Configuration")

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

        if openai_key:
            st.success("✅ AI analysis enabled")
        else:
            st.warning("⚠️ No OpenAI key — AI disabled")

        if daytona_key:
            st.success("✅ Sandboxed AI analysis enabled")
        else:
            st.info("ℹ️ No Daytona key — AI analysis runs locally")

        st.divider()
        st.caption("Get your Vercel token at [vercel.com/account/tokens](https://vercel.com/account/tokens)")
        st.caption("Get your OpenAI key at [platform.openai.com/api-keys](https://platform.openai.com/api-keys)")
        st.caption("Get your Daytona key at [app.daytona.io](https://app.daytona.io)")


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

    col_hdr, col_refresh = st.columns([4, 1])
    col_hdr.markdown("### Deployments")
    if col_refresh.button("↻ Refresh", use_container_width=True):
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

    for dep in deployments:
        dep_id = dep.get("uid") or dep.get("id", "")
        state = dep_state(dep)
        dot = STATE_DOT.get(state, "⚪")
        color = STATE_LABEL_COLOR.get(state, "gray")
        name = dep.get("name", "unknown")
        url = dep.get("url", "")
        created = dep.get("createdAt") or dep.get("created")
        meta = dep.get("meta", {})
        branch = meta.get("githubCommitRef") or meta.get("gitlabCommitRef") or ""
        commit = meta.get("githubCommitMessage") or meta.get("gitlabCommitMessage") or ""
        if commit and len(commit) > 55:
            commit = commit[:55] + "…"

        is_selected = st.session_state.selected_dep_id == dep_id

        with st.container(border=is_selected):
            c1, c2, c3 = st.columns([3, 2, 1])
            with c1:
                st.markdown(f"**{name}**")
                if url:
                    st.caption(f"🔗 {url[:50]}")
                if branch or commit:
                    st.caption(f"{'🌿 ' + branch if branch else ''} {commit}".strip())
            with c2:
                st.markdown(f"{dot} :{color}[{state}]")
                st.caption(age(created))
            with c3:
                btn_label = "📂 Open" if not is_selected else "✓ Open"
                if st.button(btn_label, key=f"open_{dep_id}", use_container_width=True):
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

    state = dep_state(detail)
    dot = STATE_DOT.get(state, "⚪")
    color = STATE_LABEL_COLOR.get(state, "gray")
    name = detail.get("name", "unknown")
    url = detail.get("url", "")
    created = detail.get("createdAt") or detail.get("created")
    ready_at = detail.get("ready")
    error_msg = detail.get("errorMessage", "")

    # Header
    col_title, col_close = st.columns([5, 1])
    col_title.markdown(f"## {dot} {name}")
    if col_close.button("✕ Close", key="close_detail"):
        st.session_state.selected_dep_id = None
        st.session_state.dep_detail = None
        st.session_state.dep_events = []
        st.session_state.ai_analysis = ""
        st.rerun()

    # Metrics row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Status", f":{color}[{state}]")
    m2.metric("Created", age(created))
    if ready_at and state == "READY":
        m3.metric("Build Time", f"{(ready_at - created) // 1000}s" if created else "—")
    elif state == "ERROR":
        m3.metric("Result", ":red[Failed]")
    else:
        m3.metric("Build Time", "—")
    if url:
        m4.markdown(f"**URL**\n[{url[:35]}](https://{url})")

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

    # Show whether analysis will run in sandbox or locally
    if daytona_key:
        st.caption("🔒 Analysis will run in an isolated Daytona sandbox")
    else:
        st.caption("⚠️ Analysis will run locally — add a Daytona API key for sandboxed execution")

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

    # Run analysis — sandboxed if Daytona key is available, local otherwise
    if daytona_key:
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
    else:
        st.info("GPT-4o is analyzing the deployment failure…")
        try:
            result = st.write_stream(
                stream_analysis(
                    deployment=detail,
                    events=events,
                    api_key=openai_key,
                )
            )
            st.session_state.ai_analysis = result
            st.session_state.analyzing = False
        except Exception as e:
            st.error(f"AI analysis failed: {e}")
            st.session_state.analyzing = False


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    render_sidebar()

    if not st.session_state.client:
        st.markdown("# 🚀 Vercel Deployment Monitor")
        st.markdown(
            "Monitor your Vercel deployments and get AI-powered fix recommendations "
            "for failed builds."
        )

        col1, col2 = st.columns(2)
        with col1:
            with st.expander("✨ Features", expanded=True):
                st.markdown(
                    """
- **Live deployment status** — see all recent deployments at a glance
- **Build log viewer** — browse full build output with error highlighting
- **AI error analysis** — GPT-4o analyzes failures and suggests specific fixes
- **Sandboxed AI analysis** — run error analysis in an isolated Daytona sandbox for security
- **Project filtering** — focus on one project or see everything
"""
                )
        with col2:
            with st.expander("🔑 Getting started", expanded=True):
                st.markdown(
                    """
1. Go to [vercel.com/account/tokens](https://vercel.com/account/tokens) and create a token
2. Get an OpenAI API key from [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
3. *(Optional)* Get a Daytona API key from [app.daytona.io](https://app.daytona.io) for sandboxed AI analysis
4. Enter credentials in the sidebar and click **Connect**
5. Select a deployment and click **🤖 Analyze with AI** on any failed build
"""
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
