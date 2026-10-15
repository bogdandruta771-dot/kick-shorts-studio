"""YouTube Shorts direct multi-account uploader supporting OAuth 2.0 and resumable uploads."""
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

ACCOUNTS_DIR = CREDENTIALS_DIR / "accounts"
ACCOUNTS_DIR.mkdir(parents=True, exist_ok=True)

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


def _save_account_token_and_meta(creds: Credentials, channel_info: Dict[str, Any]) -> Path:
    """Stores credentials and metadata for an authenticated YouTube channel."""
    channel_id = channel_info.get("channel_id") or f"channel_{int(time.time())}"
    account_file = ACCOUNTS_DIR / f"{channel_id}.json"

    token_info = json.loads(creds.to_json())
    payload = {
        "channel_id": channel_id,
        "channel_title": channel_info.get("channel_title") or "YouTube Channel",
        "channel_avatar": channel_info.get("channel_avatar"),
        "channel_custom_url": channel_info.get("channel_custom_url"),
        "token_data": token_info,
        "updated_at": int(time.time()),
    }

    with open(account_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    # Sync primary TOKEN_FILE for legacy compatibility
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())

    return account_file


def _load_creds_from_account_file(file_path: Path) -> Optional[tuple[Credentials, Dict[str, Any]]]:
    """Loads credentials and account metadata from a stored account json file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        token_data = dict(data.get("token_data") if "token_data" in data else data)

        # If client_id or client_secret missing from token_data, attempt to fill from CLIENT_SECRETS_FILE
        if "client_id" not in token_data or "client_secret" not in token_data:
            if CLIENT_SECRETS_FILE.is_file():
                try:
                    with open(CLIENT_SECRETS_FILE, "r", encoding="utf-8") as sf:
                        s_data = json.load(sf)
                    s_info = s_data.get("installed") or s_data.get("web") or {}
                    if "client_id" not in token_data and "client_id" in s_info:
                        token_data["client_id"] = s_info["client_id"]
                    if "client_secret" not in token_data and "client_secret" in s_info:
                        token_data["client_secret"] = s_info["client_secret"]
                except Exception:
                    pass

        try:
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        except Exception:
            creds = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=token_data.get("client_id", "dummy_client_id"),
                client_secret=token_data.get("client_secret", "dummy_client_secret"),
                scopes=token_data.get("scopes", SCOPES),
            )

        if not creds:
            return None

        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                if "token_data" in data:
                    data["token_data"] = json.loads(creds.to_json())
                    data["updated_at"] = int(time.time())
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
                else:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(creds.to_json())
            except Exception as ref_err:
                pass

        meta = {
            "channel_id": data.get("channel_id") or file_path.stem,
            "channel_title": data.get("channel_title") or "YouTube Channel",
            "channel_avatar": data.get("channel_avatar"),
            "channel_custom_url": data.get("channel_custom_url"),
            "file": file_path.name,
        }
        return creds, meta
    except Exception as e:
        print(f"Notice: Failed to load account credentials from {file_path.name}: {e}")
        return None


def _migrate_legacy_token():
    """Migrates single youtube_token.json into accounts/ directory if not already migrated."""
    if not TOKEN_FILE.is_file():
        return
    # If accounts directory already has files, migration is already done
    if any(ACCOUNTS_DIR.glob("*.json")):
        return

    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if creds and creds.valid or (creds and creds.refresh_token):
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
            channels_resp = youtube.channels().list(mine=True, part="snippet").execute()
            items = channels_resp.get("items", [])
            if items:
                snippet = items[0].get("snippet", {})
                _save_account_token_and_meta(creds, {
                    "channel_id": items[0].get("id"),
                    "channel_title": snippet.get("title", "YouTube Channel"),
                    "channel_avatar": snippet.get("thumbnails", {}).get("default", {}).get("url"),
                    "channel_custom_url": snippet.get("customUrl"),
                })
            else:
                _save_account_token_and_meta(creds, {
                    "channel_id": "primary_channel",
                    "channel_title": "YouTube User",
                })
    except Exception as e:
        print(f"Legacy token migration notice: {e}")


def list_youtube_accounts() -> List[Dict[str, Any]]:
    """Returns a list of all currently connected YouTube channels/accounts."""
    _migrate_legacy_token()
    accounts = []
    account_files = sorted(ACCOUNTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    for p in account_files:
        res = _load_creds_from_account_file(p)
        if res:
            creds, meta = res
            meta["is_valid"] = creds.valid
            accounts.append(meta)

    return accounts


def get_youtube_auth_status() -> Dict[str, Any]:
    """
    Checks if OAuth client secrets exist and returns all connected YouTube accounts.
    Maintains full backwards compatibility with legacy single-account checks.
    """
    has_secrets = CLIENT_SECRETS_FILE.is_file()
    client_type = get_youtube_client_type()
    if not has_secrets:
        return {
            "has_secrets": False,
            "has_client_secrets": False,
            "authenticated": False,
            "client_type": client_type,
            "accounts": [],
            "account_count": 0,
            "channel_title": None,
            "channel_id": None,
            "channel_avatar": None,
        }

    accounts = list_youtube_accounts()
    authenticated = len(accounts) > 0

    primary = accounts[0] if accounts else {}
    return {
        "has_secrets": True,
        "has_client_secrets": True,
        "authenticated": authenticated,
        "client_type": client_type,
        "accounts": accounts,
        "account_count": len(accounts),
        "channel_title": primary.get("channel_title"),
        "channel_id": primary.get("channel_id"),
        "channel_avatar": primary.get("channel_avatar"),
        "channel_custom_url": primary.get("channel_custom_url"),
    }


def disconnect_youtube_account(channel_id: str) -> bool:
    """Removes a specific YouTube channel connection."""
    target_file = ACCOUNTS_DIR / f"{channel_id}.json"
    removed = False
    if target_file.is_file():
        target_file.unlink(missing_ok=True)
        removed = True

    # Check remaining accounts
    remaining = list_youtube_accounts()
    if remaining:
        # Update TOKEN_FILE to first remaining
        first_file = ACCOUNTS_DIR / f"{remaining[0]['channel_id']}.json"
        res = _load_creds_from_account_file(first_file)
        if res:
            creds, _ = res
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
    else:
        if TOKEN_FILE.is_file():
            TOKEN_FILE.unlink(missing_ok=True)

    return removed


def disconnect_youtube() -> bool:
    """Removes all stored YouTube accounts and token to allow clean reconnecting."""
    try:
        for p in ACCOUNTS_DIR.glob("*.json"):
            p.unlink(missing_ok=True)
        if TOKEN_FILE.is_file():
            TOKEN_FILE.unlink(missing_ok=True)
        return True
    except Exception as e:
        print(f"Error disconnecting YouTube accounts: {e}")
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
    """Generates the authorization URL and state for user consent, prompting account chooser for multi-channel support."""
    flow = create_youtube_flow(redirect_uri=redirect_uri)
    auth_url, state = flow.authorization_url(
        prompt="select_account consent",
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
    """Exchanges authorization code for access and refresh tokens, saving channel metadata."""
    clean_code = code.strip()
    if "code=" in clean_code:
        import urllib.parse
        parsed = urllib.parse.urlparse(clean_code)
        qs = urllib.parse.parse_qs(parsed.query)
        if "code" in qs and qs["code"]:
            clean_code = qs["code"][0]

    flow = create_youtube_flow(redirect_uri=redirect_uri)
    flow.fetch_token(code=clean_code)
    creds = flow.credentials

    # Identify channel info via YouTube Data API
    channel_info = {}
    try:
        youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
        channels_resp = youtube.channels().list(mine=True, part="snippet").execute()
        items = channels_resp.get("items", [])
        if items:
            snippet = items[0].get("snippet", {})
            channel_info = {
                "channel_id": items[0].get("id"),
                "channel_title": snippet.get("title", "YouTube Channel"),
                "channel_avatar": snippet.get("thumbnails", {}).get("default", {}).get("url"),
                "channel_custom_url": snippet.get("customUrl"),
            }
    except Exception as exc:
        print(f"Notice: Failed to fetch channel snippet: {exc}")

    if not channel_info.get("channel_id"):
        channel_info = {
            "channel_id": f"channel_{int(time.time())}",
            "channel_title": "Connected YouTube Channel",
        }

    _save_account_token_and_meta(creds, channel_info)
    return get_youtube_auth_status()


def start_youtube_oauth_flow() -> Dict[str, Any]:
    """Fallback local server flow."""
    if not CLIENT_SECRETS_FILE.is_file():
        raise FileNotFoundError(
            "client_secret.json not found. Please upload your OAuth Client ID file first."
        )

    with open(CLIENT_SECRETS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "web" in data and "installed" not in data:
        data_to_use = {"installed": data["web"]}
    else:
        data_to_use = data

    flow = InstalledAppFlow.from_client_config(
        data_to_use,
        scopes=SCOPES,
    )
    creds = flow.run_local_server(port=0, prompt="select_account consent", timeout_seconds=120)

    channel_info = {}
    try:
        youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
        channels_resp = youtube.channels().list(mine=True, part="snippet").execute()
        items = channels_resp.get("items", [])
        if items:
            snippet = items[0].get("snippet", {})
            channel_info = {
                "channel_id": items[0].get("id"),
                "channel_title": snippet.get("title", "YouTube Channel"),
                "channel_avatar": snippet.get("thumbnails", {}).get("default", {}).get("url"),
                "channel_custom_url": snippet.get("customUrl"),
            }
    except Exception:
        pass

    _save_account_token_and_meta(creds, channel_info or {"channel_id": "primary_channel"})
    return get_youtube_auth_status()


def _get_credentials_for_channel(channel_id: Optional[str] = None) -> tuple[Credentials, Dict[str, Any]]:
    """Resolves credentials and metadata for a specific channel or the primary connected channel."""
    _migrate_legacy_token()
    if channel_id:
        target_file = ACCOUNTS_DIR / f"{channel_id}.json"
        if target_file.is_file():
            res = _load_creds_from_account_file(target_file)
            if res:
                return res

    # Otherwise look for any valid account in ACCOUNTS_DIR
    accounts = list_youtube_accounts()
    if accounts:
        first_cid = accounts[0]["channel_id"]
        res = _load_creds_from_account_file(ACCOUNTS_DIR / f"{first_cid}.json")
        if res:
            return res

    # Fallback to single TOKEN_FILE if present
    if TOKEN_FILE.is_file():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
        if creds.valid:
            return creds, {"channel_id": "default", "channel_title": "Connected Channel"}

    raise PermissionError("No connected YouTube account found. Please connect your channel first.")


def upload_single_channel_short(
    creds: Credentials,
    channel_meta: Dict[str, Any],
    video_path: Path,
    title: str,
    description: str,
    tags: Optional[List[str]] = None,
    privacy_status: str = "public",
    made_for_kids: bool = False,
    progress_cb: Optional[Callable[[float, str], None]] = None,
    pct_start: float = 0.05,
    pct_end: float = 0.95,
) -> Dict[str, Any]:
    """Uploads a vertical Short to a single authenticated YouTube channel."""
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    channel_name = channel_meta.get("channel_title", "YouTube Channel")

    # Clean title and tags
    clean_title = title.strip()
    if "#shorts" not in clean_title.lower() and len(clean_title) <= 90:
        clean_title = f"{clean_title} #shorts"

    clean_desc = description.strip()
    if "#shorts" not in clean_desc.lower():
        clean_desc = f"{clean_desc}\n\n#shorts"

    clean_tags = list(tags or [])
    for default_tag in ["Shorts", "Kick", "Stream", "Highlights", "Viral"]:
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
        progress_cb(pct_start, f"Preparing upload for {channel_name}...")

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
    last_pct = pct_start

    while response is None:
        status, response = request.next_chunk()
        if status:
            frac = status.progress()
            current_pct = pct_start + frac * (pct_end - pct_start)
            last_pct = max(last_pct, current_pct)
            if progress_cb:
                progress_cb(last_pct, f"Uploading to {channel_name}: {int(frac * 100)}%...")

    if not response or "id" not in response:
        raise ValueError(f"Upload to {channel_name} completed without video ID.")

    video_id = response["id"]
    shorts_url = f"https://youtube.com/shorts/{video_id}"
    watch_url = f"https://www.youtube.com/watch?v={video_id}"

    return {
        "channel_id": channel_meta.get("channel_id"),
        "channel_title": channel_name,
        "video_id": video_id,
        "shorts_url": shorts_url,
        "watch_url": watch_url,
        "title": clean_title,
        "privacy_status": body["status"]["privacyStatus"],
    }


def upload_shorts_video(
    video_path: Path,
    title: str,
    description: str,
    tags: Optional[List[str]] = None,
    privacy_status: str = "public",
    made_for_kids: bool = False,
    channel_id: Optional[str] = None,
    channel_ids: Optional[List[str]] = None,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> Dict[str, Any]:
    """
    Uploads a 9:16 vertical video directly to YouTube Shorts with resumable chunks.
    Supports single-account upload or multi-account simultaneous broadcast posting.
    """
    if not video_path.is_file():
        raise FileNotFoundError(f"Video file does not exist: {video_path}")

    # Determine target channel IDs
    target_cids: List[str] = []
    if channel_ids:
        target_cids = [cid.strip() for cid in channel_ids if cid.strip()]
    elif channel_id:
        target_cids = [channel_id.strip()]

    # If no specific channels requested, default to all connected or primary
    if not target_cids:
        all_accounts = list_youtube_accounts()
        if all_accounts:
            target_cids = [all_accounts[0]["channel_id"]]

    if not target_cids:
        # Check fallback
        _creds, meta = _get_credentials_for_channel(None)
        target_cids = [meta.get("channel_id", "default")]

    total_channels = len(target_cids)
    results = []

    for idx, cid in enumerate(target_cids):
        creds, meta = _get_credentials_for_channel(cid)
        slice_start = 0.05 + (idx / total_channels) * 0.90
        slice_end = 0.05 + ((idx + 1) / total_channels) * 0.90

        if progress_cb and total_channels > 1:
            progress_cb(slice_start, f"Broadcasting to channel {idx + 1} of {total_channels} ({meta.get('channel_title')})...")

        res = upload_single_channel_short(
            creds=creds,
            channel_meta=meta,
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            privacy_status=privacy_status,
            made_for_kids=made_for_kids,
            progress_cb=progress_cb,
            pct_start=slice_start,
            pct_end=slice_end,
        )
        results.append(res)

    primary_res = results[0]
    if progress_cb:
        if total_channels > 1:
            progress_cb(1.0, f"Successfully published to all {total_channels} channels!")
        else:
            progress_cb(1.0, f"Successfully uploaded! Video ID: {primary_res['video_id']}")

    return {
        "video_id": primary_res["video_id"],
        "shorts_url": primary_res["shorts_url"],
        "watch_url": primary_res["watch_url"],
        "title": primary_res["title"],
        "privacy_status": primary_res["privacy_status"],
        "results": results,
        "total_uploaded": len(results),
    }
