import json
import requests
from typing import Any, Dict, List, Optional


class VercelAPIError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)


def _extract_event_text(event: Dict) -> str:
    """Normalize both nested-payload and flat event shapes."""
    payload = event.get("payload", event)
    return (payload.get("text") or "").strip()


class VercelClient:
    BASE_URL = "https://api.vercel.com"

    def __init__(self, token: str, team_id: Optional[str] = None):
        self.token = token
        self.team_id = team_id or None
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _params(self, extra: Optional[Dict] = None) -> Dict:
        params: Dict = {}
        if self.team_id:
            params["teamId"] = self.team_id
        if extra:
            params.update(extra)
        return params

    def _get(self, path: str, params: Optional[Dict] = None) -> Any:
        url = f"{self.BASE_URL}{path}"
        response = self.session.get(url, params=self._params(params), timeout=30)
        if response.status_code == 401:
            raise VercelAPIError("Invalid API token. Check your Vercel token.", 401)
        if response.status_code == 403:
            raise VercelAPIError("Access denied. Check token permissions.", 403)
        if response.status_code == 404:
            raise VercelAPIError(f"Not found: {path}", 404)
        if not response.ok:
            try:
                msg = response.json().get("error", {}).get("message", response.text)
            except Exception:
                msg = response.text
            raise VercelAPIError(f"API error ({response.status_code}): {msg}", response.status_code)
        return response.json()

    def validate_token(self) -> Dict:
        return self._get("/v2/user")

    def get_teams(self) -> List[Dict]:
        try:
            data = self._get("/v2/teams")
            return data.get("teams", [])
        except VercelAPIError as e:
            if e.status_code in (403, 404):
                return []   # token scope doesn't include teams — treat as no teams
            raise

    def get_projects(self, limit: int = 100) -> List[Dict]:
        try:
            data = self._get("/v9/projects", {"limit": limit})
            return data.get("projects", [])
        except VercelAPIError as e:
            if e.status_code == 403 and self.team_id:
                # Token doesn't have access to this team — try without teamId
                self.team_id = None
                data = self._get("/v9/projects", {"limit": limit})
                return data.get("projects", [])
            raise

    def get_deployments(
        self,
        project_id: Optional[str] = None,
        limit: int = 20,
        state: Optional[str] = None,
    ) -> List[Dict]:
        params: Dict = {"limit": limit}
        if project_id:
            params["projectId"] = project_id
        if state:
            params["state"] = state
        data = self._get("/v6/deployments", params)
        return data.get("deployments", [])

    def get_deployment(self, deployment_id: str) -> Dict:
        return self._get(f"/v13/deployments/{deployment_id}")

    def get_build_logs(self, deployment_id: str) -> List[Dict]:
        """Fetch build log events for a deployment."""
        for version in ("/v3", "/v2"):
            try:
                url = f"{self.BASE_URL}{version}/deployments/{deployment_id}/events"
                response = self.session.get(
                    url,
                    params=self._params({"limit": -1}),
                    timeout=30,
                )
                if not response.ok:
                    continue

                # Try JSON array
                try:
                    data = response.json()
                    if isinstance(data, list):
                        return data
                    if isinstance(data, dict) and "events" in data:
                        return data["events"]
                except Exception:
                    pass

                # Fall back to newline-delimited JSON
                events = []
                for line in response.text.splitlines():
                    line = line.strip()
                    if line:
                        try:
                            events.append(json.loads(line))
                        except Exception:
                            pass
                if events:
                    return events

            except Exception:
                continue

        return []

    def get_readable_logs(self, deployment_id: str) -> List[Dict]:
        """Return only human-readable log events."""
        SHOW_TYPES = {"stdout", "stderr", "command", "exit", "fatal"}
        events = self.get_build_logs(deployment_id)
        return [e for e in events if e.get("type") in SHOW_TYPES]
