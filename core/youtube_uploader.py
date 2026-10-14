"""YouTube Shorts direct uploader supporting OAuth 2.0 and resumable uploads."""
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from core.config import BASE_DIR

CREDENTIALS_DIR = BASE_DIR / "credentials"
CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

CLIENT_SECRETS_FILE = CREDENTIALS_DIR / "client_secret.json"
TOKEN_FILE = CREDENTIALS_DIR / "youtube_token.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def get_youtube_client_type() -> str:
    """Returns 'desktop', 'web', or 'none' depending on client_secret.json."""
    if not CLIENT_SECRETS_FILE.is_file():
        return "none"
    try:
        with open(CLIENT_SECRETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "installed" in data:
            return "desktop"
        if "web" in data:
            return "web"
    except Exception:
        pass
    return "unknown"


def save_client_secrets_json(content: str) -> Path:
    """Saves user-uploaded or pasted client_secrets.json."""
    data = json.loads(content) if isinstance(content, str) else content
    with open(CLIENT_SECRETS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return CLIENT_SECRETS_FILE


def get_youtube_auth_status() -> Dict[str, Any]:
    """
    Checks if OAuth client secrets exist and if valid user credentials token exists.
    Returns channel info if authenticated.
    """
    has_secrets = CLIENT_SECRETS_FILE.is_file()
    client_type = get_youtube_client_type()
    if not has_secrets:
        return {
            "has_secrets": False,
            "has_client_secrets": False,
            "authenticated": False,
            "client_type": client_type,
            "channel_title": None,
            "channel_id": None,
            "channel_avatar": None,
        }

    if not TOKEN_FILE.is_file():
        return {
            "has_secrets": True,
            "has_client_secrets": True,
            "authenticated": False,
            "client_type": client_type,
            "channel_title": None,
            "channel_id": None,
            "channel_avatar": None,
        }

    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if not creds:
            return {"has_secrets": True, "authenticated": False, "client_type": client_type}

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                f.write(creds.to_json())

        if not creds.valid:
            return {"has_secrets": True, "authenticated": False, "client_type": client_type}

        # Fetch channel snippet
        youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
        channels_resp = youtube.channels().list(mine=True, part="snippet").execute()
        items = channels_resp.get("items", [])
        if items:
            snippet = items[0].get("snippet", {})
            return {
                "has_secrets": True,
                "authenticated": True,
                "client_type": client_type,
                "channel_title": snippet.get("title", "YouTube Channel"),
                "channel_id": items[0].get("id"),
                "channel_avatar": snippet.get("thumbnails", {}).get("default", {}).get("url"),
                "channel_custom_url": snippet.get("customUrl"),
            }
        return {"has_secrets": True, "authenticated": True, "client_type": client_type, "channel_title": "YouTube User"}
    except Exception as e:
        print(f"YouTube status check notice: {e}")
        return {"has_secrets": True, "authenticated": False, "client_type": client_type, "error": str(e)}


def disconnect_youtube() -> bool:
    """Removes stored youtube_token.json to allow reconnecting."""
    try:
        if TOKEN_FILE.is_file():
            TOKEN_FILE.unlink(missing_ok=True)
        return True
    except Exception as e:
        print(f"Error disconnecting YouTube: {e}")
        return False


def create_youtube_flow(redirect_uri: str = "http://127.0.0.1:7860/api/youtube/oauth2callback") -> Flow:
    """Creates a google-auth Flow supporting both web and installed client configurations."""
    if not CLIENT_SECRETS_FILE.is_file():
        raise FileNotFoundError(
            "client_secret.json not found. Please upload your OAuth Client ID file first."
        )

    with open(CLIENT_SECRETS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    flow = Flow.from_client_config(
        data,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )
    return flow


def get_youtube_authorization_url(redirect_uri: str = "http://127.0.0.1:7860/api/youtube/oauth2callback") -> Dict[str, Any]:
    """Generates the authorization URL and state for user consent."""
    flow = create_youtube_flow(redirect_uri=redirect_uri)
    auth_url, state = flow.authorization_url(
        prompt="consent",
        access_type="offline",
        include_granted_scopes="true",
    )
    return {
        "auth_url": auth_url,
        "state": state,
        "redirect_uri": redirect_uri,
        "client_type": get_youtube_client_type(),
    }


def exchange_youtube_code(
    code: str,
    redirect_uri: str = "http://127.0.0.1:7860/api/youtube/oauth2callback",
) -> Dict[str, Any]:
    """Exchanges authorization code for access and refresh tokens."""
    clean_code = code.strip()
    # If the user pasted a full redirect URL like http://127.0.0.1:7860/api/youtube/oauth2callback?code=xxx
    if "code=" in clean_code:
        import urllib.parse
        parsed = urllib.parse.urlparse(clean_code)
        qs = urllib.parse.parse_qs(parsed.query)
        if "code" in qs and qs["code"]:
            clean_code = qs["code"][0]

    flow = create_youtube_flow(redirect_uri=redirect_uri)
    flow.fetch_token(code=clean_code)
    creds = flow.credentials

    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())

    return get_youtube_auth_status()


def start_youtube_oauth_flow() -> Dict[str, Any]:
    """Fallback local server flow."""
    if not CLIENT_SECRETS_FILE.is_file():
        raise FileNotFoundError(
            "client_secret.json not found. Please upload your OAuth Client ID file first."
        )

    with open(CLIENT_SECRETS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # If web app without custom redirect, adapt to installed
    if "web" in data and "installed" not in data:
        data_to_use = {"installed": data["web"]}
    else:
        data_to_use = data

    flow = InstalledAppFlow.from_client_config(
        data_to_use,
        scopes=SCOPES,
    )
    creds = flow.run_local_server(port=0, prompt="consent", timeout_seconds=120)

    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())

    return get_youtube_auth_status()


def upload_shorts_video(
    video_path: Path,
    title: str,
    description: str,
    tags: Optional[List[str]] = None,
    privacy_status: str = "public",
    made_for_kids: bool = False,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> Dict[str, Any]:
    """
    Uploads a 9:16 vertical video directly to YouTube Shorts with resumable chunks.
    Automatically ensures '#Shorts' tag is embedded for Shorts algorithm recognition.
    """
    if not video_path.is_file():
        raise FileNotFoundError(f"Video file does not exist: {video_path}")

    if not TOKEN_FILE.is_file():
        raise PermissionError("YouTube account is not connected. Authenticate first.")

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    if not creds.valid:
        raise PermissionError("YouTube credentials are invalid or expired. Reconnect channel.")

    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

    # Clean title and tags
    clean_title = title.strip()
    if "#shorts" not in clean_title.lower() and len(clean_title) <= 90:
        clean_title = f"{clean_title} #shorts"

    clean_desc = description.strip()
    if "#shorts" not in clean_desc.lower():
        clean_desc = f"{clean_desc}\n\n#shorts"

    clean_tags = list(tags or [])
    for default_tag in ["Shorts", "Kick", "Casino", "Big Win", "Slots"]:
        if default_tag not in clean_tags:
            clean_tags.append(default_tag)

    body = {
        "snippet": {
            "title": clean_title[:100],
            "description": clean_desc[:5000],
            "tags": clean_tags,
            "categoryId": "20",  # Gaming
        },
        "status": {
            "privacyStatus": privacy_status.lower() if privacy_status in ("public", "private", "unlisted") else "public",
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }

    if progress_cb:
        progress_cb(0.05, "Preparing YouTube resumable upload chunk stream...")

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        chunksize=1024 * 1024 * 4,  # 4MB chunks
        resumable=True,
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    last_pct = 0.05

    while response is None:
        status, response = request.next_chunk()
        if status:
            frac = status.progress()
            last_pct = max(last_pct, 0.05 + frac * 0.90)
            if progress_cb:
                progress_cb(last_pct, f"Uploading to YouTube Shorts: {int(frac * 100)}%...")

    if not response or "id" not in response:
        raise ValueError("YouTube upload completed but did not return video ID.")

    video_id = response["id"]
    shorts_url = f"https://youtube.com/shorts/{video_id}"
    watch_url = f"https://www.youtube.com/watch?v={video_id}"

    if progress_cb:
        progress_cb(1.0, f"Successfully uploaded! Video ID: {video_id}")

    return {
        "video_id": video_id,
        "shorts_url": shorts_url,
        "watch_url": watch_url,
        "title": clean_title,
        "privacy_status": body["status"]["privacyStatus"],
    }
