# Open Deployment Monitor

AI-powered Vercel deployment monitoring that helps your team stop wasting time in log hell.

When a deployment fails, this tool pulls deployment details and build logs, then generates an AI diagnosis with:
- Root cause
- Error explanation
- Fix steps
- Prevention tips

All AI analysis runs inside an isolated Daytona Sandbox to protect your secrets and logs.

## Why This Exists

CI/CD failures can block the entire team. Reading long build logs in a dashboard is slow and painful.

Open Deployment Monitor improves flow by turning failed deployment data into actionable guidance in seconds.

## Core Workflow (4 Steps)

1. Connect
- Add your Vercel token, OpenAI API key, and Daytona API key.
- Click Connect.

2. Monitor
- View recent deployments and status at a glance.
- Filter by project and deployment state.

3. Investigate
- Open a deployment to inspect logs.
- Focus on all lines or error-only lines.

4. Analyze
- Run AI analysis for failed deployments.
- Get clear diagnosis, fixes, and prevention advice.

## Security: Daytona Sandbox Advantage

- AI analysis does not run in your local app process.
- A temporary Daytona sandbox is created for each analysis.
- Deployment data is sent to that isolated environment only.
- Sandbox is destroyed after analysis.

This provides better isolation for API keys and log data.

## Tech Stack

- Streamlit UI
- Vercel REST API
- OpenAI API
- Daytona Sandbox SDK

## Project Structure

- app.py: Main Streamlit UI and workflow
- vercel_client.py: Vercel API integration (projects, deployments, logs)
- sandbox_runner.py: Isolated Daytona execution for AI analysis
- ai_analyzer.py: Prompt construction and streaming analysis helpers
- requirements.txt: Python dependencies
- .env.example: Environment variable template

## Prerequisites

- Python 3.10+
- Vercel API token (Full Account scope)
- OpenAI API key
- Daytona API key

## Quick Start

1. Clone and enter the project

```bash
git clone <your-repo-url>
cd open-deployment
```

2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Create environment file

```bash
cp .env.example .env
```

5. Fill your keys in .env

```env
VERCEL_TOKEN=your_vercel_token_here
OPENAI_API_KEY=your_openai_api_key_here
VERCEL_TEAM_ID=
DAYTONA_API_KEY=your_daytona_api_key_here
```

6. Start the app

```bash
streamlit run app.py
```

Then open the local Streamlit URL shown in your terminal.

## How To Use

1. In the sidebar, verify your keys and click Connect.
2. Select account/team and project.
3. Choose a deployment from the list.
4. Open Build Logs to inspect output.
5. Open AI Analysis and click Analyze with AI.
6. Review root cause, fix steps, and prevention tips.

## Notes and Troubleshooting

- If no projects/deployments appear:
  - Ensure your Vercel token is Full Account scope, not limited scope.
  - Confirm the correct team/account is selected.
- If AI Analysis is unavailable:
  - Add both OPENAI_API_KEY and DAYTONA_API_KEY.
- If a deployment is healthy:
  - AI analysis is skipped by design.

## Product Positioning Copy

Stop letting CI/CD failures stall your team.

Deployment failures should not trap engineers in log hunting for hours. Open Deployment Monitor watches cloud deployments and uses AI to explain exactly why a build failed and how to fix it fast.

Efficiency with privacy: analysis runs in isolated Daytona sandboxes, and each environment is temporary and destroyed after use.
