"""Daytona Sandbox integration — runs AI error analysis in an isolated environment."""

import base64
import json
import os
import textwrap
from typing import Dict, List, Optional

from daytona_sdk import Daytona, DaytonaConfig


def create_daytona_client(api_key: Optional[str] = None) -> Daytona:
    """Create a Daytona client from an API key or environment variable."""
    key = api_key or os.getenv("DAYTONA_API_KEY", "")
    if not key:
        raise ValueError("Daytona API key is required.")
    return Daytona(DaytonaConfig(api_key=key))


def run_analysis_in_sandbox(
    daytona_key: str,
    openai_key: str,
    deployment: Dict,
    events: List[Dict],
) -> str:
    """Run the AI error analysis inside an isolated Daytona sandbox.

    This ensures the OpenAI call and all data processing happen in a
    sandboxed environment that cannot access or modify local files.
    """
    client = create_daytona_client(daytona_key)
    sandbox = client.create(timeout=120)

    try:
        # Install openai SDK inside the sandbox
        sandbox.process.exec("pip install openai", timeout=120)

        # Prepare deployment data as JSON, base64-encode to avoid shell escaping issues
        analysis_data = json.dumps({
            "deployment": deployment,
            "events": events,
            "openai_key": openai_key,
        })
        data_b64 = base64.b64encode(analysis_data.encode("utf-8")).decode("ascii")

        # Write the data file into the sandbox via Python
        sandbox.process.code_run(
            f"import base64, pathlib; "
            f"pathlib.Path('/home/daytona/analysis_data.json').write_bytes("
            f"base64.b64decode('{data_b64}'))"
        )

        # The analysis script that will run inside the sandbox
        analysis_script = textwrap.dedent('''\
            import json
            import sys

            from openai import OpenAI

            SHOW_TYPES = {"stdout", "stderr", "command", "exit", "fatal"}

            SYSTEM_PROMPT = """You are an expert DevOps engineer and full-stack developer specializing in Vercel deployments.
            You diagnose deployment failures quickly and provide clear, actionable fix steps.
            Format your response in Markdown with these sections:
            ## Root Cause
            ## Error Explanation
            ## Fix Steps
            ## Prevention Tips"""


            def extract_text(event):
                payload = event.get("payload", event)
                return (payload.get("text") or "").strip()


            def build_prompt(deployment, events):
                lines = []
                for event in events:
                    if event.get("type") not in SHOW_TYPES:
                        continue
                    text = extract_text(event)
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

                log_text = "\\n".join(lines)
                if len(log_text) > 8000:
                    truncated = len(log_text) - 8000
                    log_text = f"[... {truncated} chars omitted from start ...]\\n" + log_text[-8000:]

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
                return "\\n".join(parts)


            def main():
                with open("/home/daytona/analysis_data.json", "r") as f:
                    data = json.load(f)

                deployment = data["deployment"]
                events = data["events"]
                api_key = data["openai_key"]

                client = OpenAI(api_key=api_key)
                prompt = build_prompt(deployment, events)

                response = client.chat.completions.create(
                    model="gpt-4o",
                    max_tokens=2048,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                )
                result = response.choices[0].message.content
                print(result)


            if __name__ == "__main__":
                main()
        ''')

        # Write the analysis script into the sandbox via Python
        script_b64 = base64.b64encode(analysis_script.encode("utf-8")).decode("ascii")
        sandbox.process.code_run(
            f"import base64, pathlib; "
            f"pathlib.Path('/home/daytona/run_analysis.py').write_bytes("
            f"base64.b64decode('{script_b64}'))"
        )

        # Execute the analysis script inside the sandbox
        response = sandbox.process.exec(
            "python /home/daytona/run_analysis.py",
            timeout=120,
        )

        if response.exit_code != 0:
            raise RuntimeError(
                f"Sandbox analysis failed (exit code {response.exit_code}): "
                f"{response.result}"
            )

        return response.result

    finally:
        # Always clean up the sandbox
        try:
            client.delete(sandbox)
        except Exception:
            pass
