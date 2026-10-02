import os
import json
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, Tuple
import requests
from event_bus import get_event_bus, Event

class SocialPlatform(str, Enum):
    YOUTUBE_SHORTS = "YouTube Shorts"
    TIKTOK = "TikTok"
    INSTAGRAM_REELS = "Instagram Reels"


class PublishPrivacy(str, Enum):
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"


@dataclass
class PublishPayload:
    """
    Standard social media upload payload across all supported platforms.
    """
    file_path: str
    title: str = ""
    description: str = ""
    privacy: str = "public"
    tags: List[str] = field(default_factory=list)
    share_to_feed: bool = True

    def validate(self) -> None:
        """Validates payload sanity and file existence."""
        if not self.file_path or not os.path.exists(self.file_path):
            raise ValueError(f"Video file not found: {self.file_path}")
        
        valid_privacies = [p.value for p in PublishPrivacy]
        if self.privacy.lower() not in valid_privacies:
            raise ValueError(f"Invalid privacy '{self.privacy}'. Must be one of: {valid_privacies}")

    def format_youtube_title(self) -> str:
        """Ensures the title contains #Shorts for YouTube detection, within 100 chars."""
        clean_title = (self.title or "Viral Highlight").strip()
        if "#shorts" not in clean_title.lower():
            if len(clean_title) + len(" #Shorts") <= 100:
                clean_title = f"{clean_title} #Shorts"
            else:
                clean_title = f"{clean_title[:91].strip()} #Shorts"
        return clean_title[:100]

    def format_full_description(self) -> str:
        """Combines caption with hashtags."""
        desc = (self.description or "").strip()
        hashtags = [t if t.startswith("#") else f"#{t}" for t in self.tags if t.strip()]
        if "#Shorts" not in hashtags:
            hashtags.append("#Shorts")
        tag_str = " ".join(hashtags)
        if desc and tag_str:
            return f"{desc}\n\n{tag_str}"
        return desc or tag_str


class YouTubeShortsClient:
    """
    YouTube Data API v3 Resumable Uploader for YouTube Shorts.
    """
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    UPLOAD_INIT_URL = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"

    def verify_credentials(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Validates OAuth credentials by requesting a refreshed access token."""
        yt_cfg = config.get("social", {}).get("youtube", {})
        client_id = yt_cfg.get("client_id", "").strip()
        client_secret = yt_cfg.get("client_secret", "").strip()
        refresh_token = yt_cfg.get("refresh_token", "").strip()

        if not client_id or not client_secret or not refresh_token:
            return False, "Missing Client ID, Client Secret, or Refresh Token in Settings."

        try:
            resp = requests.post(
                self.TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                },
                timeout=10
            )
            data = resp.json()
            if resp.status_code == 200 and "access_token" in data:
                return True, "✅ YouTube OAuth credentials verified successfully!"
            error_desc = data.get("error_description", data.get("error", f"HTTP {resp.status_code}"))
            return False, f"YouTube OAuth error: {error_desc}"
        except Exception as e:
            return False, f"Connection failed: {e}"

    def upload(
        self,
        payload: PublishPayload,
        config: Dict[str, Any],
        progress_callback: Optional[Callable[[float], None]] = None,
        logger: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Uploads a video to YouTube Shorts using Google's Resumable Upload protocol.
        Returns the published YouTube Shorts link.
        """
        payload.validate()
        yt_cfg = config.get("social", {}).get("youtube", {})
        client_id = yt_cfg.get("client_id", "").strip()
        client_secret = yt_cfg.get("client_secret", "").strip()
        refresh_token = yt_cfg.get("refresh_token", "").strip()

        if not client_id or not client_secret or not refresh_token:
            raise ValueError("YouTube OAuth is not configured. Please enter your credentials in Settings.")

        # Step 1: Obtain fresh access token
        if logger:
            logger("🔑 Refreshing YouTube OAuth access token...")
        token_resp = requests.post(
            self.TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            },
            timeout=15
        )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise RuntimeError(f"Failed to authenticate with YouTube: {token_data.get('error_description', 'No access token')}")

        # Step 2: Initialize resumable upload session
        file_size = os.path.getsize(payload.file_path)
        metadata = {
            "snippet": {
                "title": payload.format_youtube_title(),
                "description": payload.format_full_description(),
                "tags": payload.tags,
                "categoryId": "20"  # Gaming
            },
            "status": {
                "privacyStatus": payload.privacy.lower(),
                "selfDeclaredMadeForKids": False
            }
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(file_size)
        }

        if logger:
            logger(f"🚀 Initializing YouTube upload session for '{payload.format_youtube_title()}' ({file_size / (1024*1024):.1f} MB)...")

        init_resp = requests.post(self.UPLOAD_INIT_URL, headers=headers, json=metadata, timeout=20)
        if init_resp.status_code not in (200, 201):
            raise RuntimeError(f"YouTube upload initialization failed ({init_resp.status_code}): {init_resp.text}")

        upload_url = init_resp.headers.get("Location")
        if not upload_url:
            raise RuntimeError("YouTube API did not return an upload session Location URL.")

        # Step 3: Stream video chunks
        chunk_size = 5 * 1024 * 1024  # 5MB chunks
        bytes_uploaded = 0

        with open(payload.file_path, "rb") as video_file:
            while bytes_uploaded < file_size:
                chunk = video_file.read(chunk_size)
                if not chunk:
                    break
                current_chunk_size = len(chunk)
                start_byte = bytes_uploaded
                end_byte = bytes_uploaded + current_chunk_size - 1

                chunk_headers = {
                    "Content-Range": f"bytes {start_byte}-{end_byte}/{file_size}",
                    "Content-Type": "video/mp4"
                }

                put_resp = requests.put(upload_url, headers=chunk_headers, data=chunk, timeout=60)
                bytes_uploaded += current_chunk_size

                fraction = min(1.0, bytes_uploaded / file_size)
                if progress_callback:
                    progress_callback(fraction)
                if logger:
                    logger(f"📤 Uploaded {int(fraction * 100)}% ({bytes_uploaded / (1024*1024):.1f} MB)...")

                if put_resp.status_code in (200, 201):
                    # Finished upload
                    res_data = put_resp.json()
                    video_id = res_data.get("id")
                    if video_id:
                        final_url = f"https://youtube.com/shorts/{video_id}"
                        if logger:
                            logger(f"🎉 Published to YouTube Shorts: {final_url}")
                        return final_url

        raise RuntimeError("Upload ended without receiving confirmation from YouTube.")


class TikTokClient:
    """
    TikTok Content Posting API v2 Client.
    """
    USER_INFO_URL = "https://open.tiktokapis.com/v2/user/info/"
    INIT_POST_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"

    def verify_credentials(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Validates TikTok access token."""
        tk_cfg = config.get("social", {}).get("tiktok", {})
        access_token = tk_cfg.get("access_token", "").strip()

        if not access_token:
            return False, "Missing TikTok Access Token in Settings."

        try:
            resp = requests.get(
                self.USER_INFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                params={"fields": "open_id,display_name"},
                timeout=10
            )
            data = resp.json()
            if data.get("error", {}).get("code") == "ok" or resp.status_code == 200:
                name = data.get("data", {}).get("user", {}).get("display_name", "Creator")
                return True, f"✅ TikTok verified! Connected as: {name}"
            return False, f"TikTok token error: {data.get('error', {}).get('message', 'Invalid token')}"
        except Exception as e:
            return False, f"Connection failed: {e}"

    def upload(
        self,
        payload: PublishPayload,
        config: Dict[str, Any],
        progress_callback: Optional[Callable[[float], None]] = None,
        logger: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Uploads and publishes video via TikTok Content Posting API.
        Returns the publish identifier.
        """
        payload.validate()
        tk_cfg = config.get("social", {}).get("tiktok", {})
        access_token = tk_cfg.get("access_token", "").strip()

        if not access_token:
            raise ValueError("TikTok is not configured. Please enter your Access Token in Settings.")

        file_size = os.path.getsize(payload.file_path)
        title = (payload.title or "Clip Highlight")[:150]
        privacy_level = "PUBLIC_TO_EVERYONE" if payload.privacy == "public" else "SELF_ONLY"

        if logger:
            logger(f"🚀 Initializing TikTok upload for '{title}' ({file_size / (1024*1024):.1f} MB)...")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8"
        }

        body = {
            "post_info": {
                "title": title,
                "privacy_level": privacy_level,
                "disable_duet": False,
                "disable_stitch": False,
                "disable_comment": False
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": file_size,
                "chunk_size": file_size,
                "total_chunk_count": 1
            }
        }

        init_resp = requests.post(self.INIT_POST_URL, headers=headers, json=body, timeout=20)
        data = init_resp.json()
        error = data.get("error", {})
        if error.get("code") != "ok" and init_resp.status_code != 200:
            raise RuntimeError(f"TikTok upload init failed: {error.get('message', init_resp.text)}")

        upload_url = data.get("data", {}).get("upload_url")
        publish_id = data.get("data", {}).get("publish_id", "tiktok_published")

        if not upload_url:
            raise RuntimeError("TikTok API did not return an upload URL.")

        if logger:
            logger("📤 Uploading video bytes to TikTok...")

        with open(payload.file_path, "rb") as vf:
            put_headers = {
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes 0-{file_size - 1}/{file_size}"
            }
            put_resp = requests.put(upload_url, headers=put_headers, data=vf, timeout=120)
            if put_resp.status_code not in (200, 201, 204):
                raise RuntimeError(f"TikTok file upload failed ({put_resp.status_code}): {put_resp.text}")

        if progress_callback:
            progress_callback(1.0)

        result_url = f"https://www.tiktok.com/@post/{publish_id}"
        if logger:
            logger(f"🎉 Successfully submitted to TikTok! Publish ID: {publish_id}")
        return result_url


class InstagramReelsClient:
    """
    Instagram Graph API Reels Publisher (Meta Graph API v19+).
    """
    GRAPH_API_BASE = "https://graph.facebook.com/v19.0"

    def verify_credentials(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Validates Instagram User ID and Graph Access Token."""
        ig_cfg = config.get("social", {}).get("instagram", {})
        user_id = ig_cfg.get("user_id", "").strip()
        access_token = ig_cfg.get("access_token", "").strip()

        if not user_id or not access_token:
            return False, "Missing Instagram User ID or Access Token in Settings."

        try:
            resp = requests.get(
                f"{self.GRAPH_API_BASE}/{user_id}",
                params={"fields": "id,username", "access_token": access_token},
                timeout=10
            )
            data = resp.json()
            if "id" in data:
                uname = data.get("username", user_id)
                return True, f"✅ Instagram verified! Connected as @{uname}"
            err_msg = data.get("error", {}).get("message", f"HTTP {resp.status_code}")
            return False, f"Instagram auth failed: {err_msg}"
        except Exception as e:
            return False, f"Connection failed: {e}"

    def upload(
        self,
        payload: PublishPayload,
        config: Dict[str, Any],
        progress_callback: Optional[Callable[[float], None]] = None,
        logger: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Creates video container and publishes Reel via Instagram Graph API.
        """
        payload.validate()
        ig_cfg = config.get("social", {}).get("instagram", {})
        user_id = ig_cfg.get("user_id", "").strip()
        access_token = ig_cfg.get("access_token", "").strip()

        if not user_id or not access_token:
            raise ValueError("Instagram is not configured. Please enter your User ID and Access Token in Settings.")

        caption = payload.format_full_description()
        file_size = os.path.getsize(payload.file_path)

        if logger:
            logger(f"🚀 Initializing Instagram Reel container for @{user_id}...")

        # Step 1: Create Reel Container via Resumable Upload protocol
        container_url = f"{self.GRAPH_API_BASE}/{user_id}/media"
        container_params = {
            "media_type": "REELS",
            "caption": caption,
            "share_to_feed": payload.share_to_feed,
            "upload_type": "resumable",
            "access_token": access_token
        }

        init_resp = requests.post(container_url, data=container_params, timeout=20)
        data = init_resp.json()
        if "id" not in data:
            raise RuntimeError(f"Failed to create Instagram Reel container: {data.get('error', {}).get('message', init_resp.text)}")

        creation_id = data["id"]
        upload_uri = data.get("uri")

        # Step 2: Upload file bytes if upload_uri provided
        if upload_uri:
            if logger:
                logger("📤 Uploading Reel video data to Meta servers...")
            with open(payload.file_path, "rb") as vf:
                upload_headers = {
                    "Authorization": f"OAuth {access_token}",
                    "offset": "0",
                    "file_size": str(file_size)
                }
                upload_resp = requests.post(upload_uri, headers=upload_headers, data=vf, timeout=120)
                if upload_resp.status_code not in (200, 201):
                    raise RuntimeError(f"Instagram upload failed ({upload_resp.status_code}): {upload_resp.text}")

        if progress_callback:
            progress_callback(0.75)

        # Step 3: Publish Media Container
        if logger:
            logger("🎬 Publishing Reel to Instagram feed...")

        publish_url = f"{self.GRAPH_API_BASE}/{user_id}/media_publish"
        pub_resp = requests.post(publish_url, data={"creation_id": creation_id, "access_token": access_token}, timeout=30)
        pub_data = pub_resp.json()

        if "id" not in pub_data:
            # Video may still be processing on Instagram's backend; poll once
            time.sleep(3)
            pub_resp = requests.post(publish_url, data={"creation_id": creation_id, "access_token": access_token}, timeout=30)
            pub_data = pub_resp.json()

        if "id" not in pub_data:
            raise RuntimeError(f"Failed to publish Instagram Reel: {pub_data.get('error', {}).get('message', pub_resp.text)}")

        media_id = pub_data["id"]
        if progress_callback:
            progress_callback(1.0)

        permalink = f"https://www.instagram.com/reel/{media_id}/"
        if logger:
            logger(f"🎉 Published to Instagram Reels: {permalink}")
        return permalink


class SocialPublishManager:
    """
    Central dispatcher for social media publishing across all platforms.
    """

    def __init__(self, event_bus=None) -> None:
        self.event_bus = event_bus or get_event_bus()
        self.clients = {
            SocialPlatform.YOUTUBE_SHORTS.value: YouTubeShortsClient(),
            SocialPlatform.TIKTOK.value: TikTokClient(),
            SocialPlatform.INSTAGRAM_REELS.value: InstagramReelsClient()
        }

    def verify_platform(self, platform: str, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Validates credentials for a specific social platform."""
        client = self.clients.get(platform)
        if not client:
            return False, f"Unsupported platform: {platform}"
        return client.verify_credentials(config)

    def publish_clip(
        self,
        platform: str,
        payload: PublishPayload,
        config: Dict[str, Any],
        progress_callback: Optional[Callable[[float], None]] = None,
        logger: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Publishes a clip payload to the specified social platform.
        Fires Event.SOCIAL_PUBLISHED on success.
        """
        client = self.clients.get(platform)
        if not client:
            raise ValueError(f"Unsupported social platform '{platform}'. Choose from: {list(self.clients.keys())}")

        result_url = client.upload(payload, config, progress_callback=progress_callback, logger=logger)

        if self.event_bus:
            self.event_bus.publish(
                Event.SOCIAL_PUBLISHED,
                platform=platform,
                url=result_url,
                title=payload.title,
                file_path=payload.file_path
            )

        return result_url


_GLOBAL_PUBLISH_MANAGER: Optional[SocialPublishManager] = None

def get_social_publish_manager() -> SocialPublishManager:
    """Returns the singleton SocialPublishManager instance."""
    global _GLOBAL_PUBLISH_MANAGER
    if _GLOBAL_PUBLISH_MANAGER is None:
        _GLOBAL_PUBLISH_MANAGER = SocialPublishManager()
    return _GLOBAL_PUBLISH_MANAGER
