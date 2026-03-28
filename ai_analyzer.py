from typing import Dict, Generator, List

from openai import OpenAI


_SHOW_TYPES = {"stdout", "stderr", "command", "exit", "fatal"}

_SYSTEM_PROMPT = """You are an expert DevOps engineer and full-stack developer specializing in Vercel deployments.
You diagnose deployment failures quickly and provide clear, actionable fix steps.
Format your response in Markdown with these sections:
## Root Cause
## Error Explanation
## Fix Steps
## Prevention Tips"""


def _extract_text(event: Dict) -> str:
    payload = event.get("payload", event)
    return (payload.get("text") or "").strip()


def build_prompt(deployment: Dict, events: List[Dict]) -> str:
    """Build the analysis prompt from deployment metadata and log events."""
    lines: List[str] = []
    for event in events:
        if event.get("type") not in _SHOW_TYPES:
            continue
        text = _extract_text(event)
        if not text:
            continue
        t = event.get("type", "")
        if t == "stderr":
            prefix = "[ERROR] "
        elif t == "command":
            prefix = "[CMD] $ "
        elif t == "exit":
            prefix = "[EXIT] "
        elif t == "fatal":
            prefix = "[FATAL] "
        else:
            prefix = ""
        lines.append(f"{prefix}{text}")

    log_text = "\n".join(lines)
    if len(log_text) > 8000:
        truncated = len(log_text) - 8000
        log_text = f"[... {truncated} chars omitted from start ...]\n" + log_text[-8000:]

    meta = deployment.get("meta", {})
    branch = meta.get("githubCommitRef") or meta.get("gitlabCommitRef") or "N/A"
    commit = meta.get("githubCommitMessage") or meta.get("gitlabCommitMessage") or "N/A"
    if len(commit) > 120:
        commit = commit[:120] + "..."

    error_msg = deployment.get("errorMessage", "")
    error_code = deployment.get("errorCode", "")

    parts = [
        "Analyze this failed Vercel deployment and provide fix recommendations.",
        "",
        "**Deployment Details:**",
        f"- Project: {deployment.get('name', 'Unknown')}",
        f"- Status: {deployment.get('state') or deployment.get('readyState', 'ERROR')}",
        f"- Branch: {branch}",
        f"- Commit: {commit}",
    ]
    if error_code:
        parts.append(f"- Error Code: {error_code}")
    if error_msg:
        parts.append(f"- Error Message: {error_msg}")

    parts += [
        "",
        "**Build Logs:**",
        "```",
        log_text if log_text else "(no log output captured)",
        "```",
        "",
        "Identify the root cause and provide specific, actionable steps to fix this deployment failure.",
    ]

    return "\n".join(parts)


def stream_analysis(
    deployment: Dict,
    events: List[Dict],
    api_key: str,
) -> Generator[str, None, None]:
    """Yield GPT-4o's streaming analysis of a deployment failure."""
    client = OpenAI(api_key=api_key)
    prompt = build_prompt(deployment, events)

    stream = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=2048,
        stream=True,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
