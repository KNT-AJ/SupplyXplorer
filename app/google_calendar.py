from __future__ import annotations

import os
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any

from fastapi import HTTPException
from fastapi.responses import RedirectResponse

# Google OAuth / Calendar deps
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except Exception:
    # Deps may not be installed yet; raise informative error when used
    Credentials = None  # type: ignore
    Flow = None  # type: ignore
    Request = None  # type: ignore
    build = None  # type: ignore


SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
REDIRECT_PATH = "/auth/google/callback"
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", "token.json")
TOKEN_PATH = os.path.abspath(TOKEN_PATH)


@dataclass
class OAuthConfig:
    client_config: Optional[dict]
    client_secrets_file: Optional[str]
    redirect_uri: str


def _load_oauth_config(base_url: str) -> OAuthConfig:
    """Load OAuth client configuration from env or local file.

    Priority:
    - GOOGLE_OAUTH_CLIENT_CONFIG env var containing JSON
    - GOOGLE_OAUTH_CLIENT_SECRETS_FILE env var path
    - ./client_secret.json in project root
    """
    client_config_env = os.getenv("GOOGLE_OAUTH_CLIENT_CONFIG")
    client_file_env = os.getenv("GOOGLE_OAUTH_CLIENT_SECRETS_FILE")

    client_config = None
    client_file = None

    if client_config_env:
        try:
            client_config = json.loads(client_config_env)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Invalid GOOGLE_OAUTH_CLIENT_CONFIG JSON: {e}")
    elif client_file_env and os.path.exists(client_file_env):
        client_file = client_file_env
    else:
        # Default to project root client_secret.json
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        default_path = os.path.join(project_root, "client_secret.json")
        if os.path.exists(default_path):
            client_file = default_path

    redirect_uri = base_url.rstrip("/") + REDIRECT_PATH
    return OAuthConfig(client_config=client_config, client_secrets_file=client_file, redirect_uri=redirect_uri)


def _ensure_deps():
    if Flow is None or build is None:
        raise HTTPException(status_code=500, detail=(
            "Google API libraries not installed. Please add 'google-api-python-client', "
            "'google-auth-oauthlib', and 'google-auth-httplib2' to requirements and install."
        ))


def create_flow(base_url: str, state: Optional[str] = None) -> Flow:
    _ensure_deps()
    cfg = _load_oauth_config(base_url)
    if cfg.client_config:
        flow = Flow.from_client_config(cfg.client_config, scopes=SCOPES, state=state)
    elif cfg.client_secrets_file:
        flow = Flow.from_client_secrets_file(cfg.client_secrets_file, scopes=SCOPES, state=state)
    else:
        raise HTTPException(status_code=500, detail=(
            "Google OAuth client config not found. Provide GOOGLE_OAUTH_CLIENT_CONFIG env JSON, "
            "GOOGLE_OAUTH_CLIENT_SECRETS_FILE env path, or client_secret.json in project root."
        ))
    flow.redirect_uri = cfg.redirect_uri
    return flow


def get_authorization_url(base_url: str, state: Optional[str] = None) -> str:
    flow = create_flow(base_url, state=state)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url


def fetch_and_store_credentials(base_url: str, code: str) -> None:
    _ensure_deps()
    flow = create_flow(base_url)
    flow.fetch_token(code=code)
    creds = flow.credentials
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())


def load_credentials() -> Optional[Credentials]:
    _ensure_deps()
    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
            # Refresh if needed
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(TOKEN_PATH, "w") as f:
                    f.write(creds.to_json())
            if creds and creds.valid:
                return creds
        except Exception:
            return None
    return None


def require_credentials(base_url: str, return_to: Optional[str] = None) -> Credentials | RedirectResponse:
    """Return valid credentials or a RedirectResponse to start OAuth."""
    creds = load_credentials()
    if creds:
        return creds
    # Encode return_to into OAuth state so we can bounce back
    state = return_to or ""
    auth_url = get_authorization_url(base_url, state=state)
    return RedirectResponse(url=auth_url, status_code=302)


def build_calendar_service(creds: Credentials):
    _ensure_deps()
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def build_event_all_day(title: str, event_date: date, description: str, location: Optional[str] = None) -> Dict[str, Any]:
    start_date = event_date.strftime("%Y-%m-%d")
    # For all-day events, Google expects end.date to be exclusive next day
    end_date = (event_date + timedelta(days=1)).strftime("%Y-%m-%d")
    body = {
        "summary": title,
        "start": {"date": start_date},
        "end": {"date": end_date},
        "description": description,
    }
    if location:
        body["location"] = location
    return body

