"""Test suite for Multi-Account YouTube uploading and Multi-Provider AI Tool Suite."""
import os
import sys
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
import app
import core.youtube_uploader as yt
import core.ai_copywriter as ai


class TestMultiProviderAI(unittest.TestCase):
    """Verifies AI copywriter provider registry, dispatching, and fallback engines."""

    def test_provider_registry(self):
        providers = ai.get_available_ai_providers()
        self.assertIsInstance(providers, list)
        self.assertGreaterEqual(len(providers), 8)
        ids = [p["id"] for p in providers]
        self.assertIn("auto", ids)
        self.assertIn("gemini", ids)
        self.assertIn("groq", ids)
        self.assertIn("ollama", ids)
        self.assertIn("openai", ids)
        self.assertIn("claude", ids)
        self.assertIn("deepseek", ids)
        self.assertIn("openrouter", ids)
        self.assertIn("custom", ids)
        self.assertIn("offline", ids)

    def test_offline_copywriter(self):
        res = ai.generate_offline_shorts_copy(
            clip_title="INSANE 1000X MULTIPLIER ON SWEET BONANZA",
            win_amount="$15,000",
            streamer="Trainwreckstv",
            promo_code="TRAIN100",
            category="casino",
        )
        self.assertEqual(len(res["titles"]), 5)
        self.assertEqual(len(res["descriptions"]), 3)
        self.assertGreaterEqual(len(res["hashtags"]), 5)
        for t in res["titles"]:
            self.assertIn("#shorts", t.lower())

    def test_auto_dispatcher_with_no_key_uses_offline(self):
        res = ai.generate_shorts_metadata(
            clip_title="Insane Valorant Ace Clutch",
            category="gaming",
            streamer="TenZ",
            provider="auto",
        )
        self.assertEqual(len(res["titles"]), 5)
        self.assertEqual(len(res["descriptions"]), 3)
        self.assertTrue(any("Valorant" in t or "CLUTCH" in t.upper() or "ACE" in t.upper() or "BRO" in t.upper() for t in res["titles"]))

    @patch("requests.post")
    def test_openai_compatible_dispatcher(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "titles": [
                                "HE DID NOT MISS A SINGLE BULLET! 🎯 #shorts",
                                "The Most Insane Clutch In Valorant History! 🔥 #shorts",
                                "LOOK AT HIS CROSSHAIR PLACEMENT! 😱 #shorts",
                                "Why Nobody Can Beat This Guy Right Now... 💀 #shorts",
                                "How Did He Win A 1v5 In Overtime?! 🤯 #shorts"
                            ],
                            "descriptions": [
                                "Action-packed gameplay from the stream! #shorts #gaming",
                                "Could you hit this shot? Tell us in the comments! #shorts",
                                "Best Valorant highlight clips and clutch plays. #shorts"
                            ],
                            "hashtags": ["#shorts", "#valorant", "#gaming", "#clutch"]
                        })
                    }
                }
            ]
        }
        mock_post.return_value = mock_resp

        res = ai.generate_shorts_metadata(
            clip_title="1v5 Valorant Ace",
            api_key="sk-test-key-12345",
            provider="openai",
            model="gpt-4o-mini",
        )
        self.assertEqual(len(res["titles"]), 5)
        self.assertIn("OpenAI", res["provider"])

    @patch("requests.post")
    def test_claude_api_dispatcher(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "content": [
                {
                    "text": json.dumps({
                        "titles": [
                            "Streamer Completely Loses It On Live Stream! 😭 #shorts",
                            "The Funniest Clip You'll Watch Today 🤣 #shorts",
                            "Nobody Expected Him To Say That... 💀 #shorts",
                            "His Face Was Actually In Shock! 😳 #shorts",
                            "Best Stream Reaction Of 2026! 🔥 #shorts"
                        ],
                        "descriptions": [
                            "Pure comedy from stream! #shorts",
                            "What would you do in his shoes? #shorts",
                            "Daily stream highlights & moments. #shorts"
                        ],
                        "hashtags": ["#shorts", "#streamer", "#funny"]
                    })
                }
            ]
        }
        mock_post.return_value = mock_resp

        res = ai.generate_shorts_metadata(
            clip_title="Funniest Streamer Fail",
            api_key="sk-ant-test-key",
            provider="claude",
            category="just_chatting",
        )
        self.assertEqual(len(res["titles"]), 5)
        self.assertIn("Claude", res["provider"])

    @patch("requests.post")
    def test_groq_failover_when_70b_returns_404(self, mock_post):
        """Simulates Groq 404 on llama-3.3-70b-versatile and verifies seamless fallback to llama-3.1-8b-instant."""
        def side_effect(url, **kwargs):
            body = kwargs.get("json", {})
            model = body.get("model", "")
            resp = MagicMock()
            if model == "llama-3.3-70b-versatile":
                resp.status_code = 404
                resp.text = json.dumps({"error": {"message": "The model `llama-3.3-70b-versatile` does not exist or you do not have access to it.", "type": "invalid_request_error"}})
                resp.json.return_value = {"error": {"message": "The model `llama-3.3-70b-versatile` does not exist or you do not have access to it."}}
                return resp
            elif model == "llama-3.1-8b-instant":
                resp.status_code = 200
                resp.json.return_value = {
                    "choices": [{
                        "message": {
                            "content": json.dumps({
                                "titles": [
                                    "HE HIT A 5000X MULTIPLIER! 🎰 #shorts",
                                    "Watch His Reaction At The End! 😱 #shorts",
                                    "Biggest Win Of The Stream! 🔥 #shorts",
                                    "Nobody Expected This Spin... 🤯 #shorts",
                                    "He Thought He Was Down To $0 💀 #shorts"
                                ],
                                "descriptions": ["Huge hit on stream!", "Drop a comment!", "Subscribe for more!"],
                                "hashtags": ["#shorts", "#bigwin", "#casino"]
                            })
                        }
                    }]
                }
                return resp
            resp.status_code = 500
            resp.text = "Unexpected model"
            return resp

        mock_post.side_effect = side_effect

        res = ai.generate_shorts_metadata(
            clip_title="Crazy Slot Win",
            api_key="gsk_real_groq_key_12345",
            provider="groq",
            model="llama-3.3-70b-versatile",
        )
        self.assertEqual(len(res["titles"]), 5)
        self.assertIn("llama-3.1-8b-instant", res["provider"])
        self.assertTrue(res.get("api_connected"))

    @patch("requests.post")
    def test_smart_cross_routing_groq_and_grok(self, mock_post):
        """Verifies intelligent auto-routing between Groq (gsk_) and xAI Grok (xai-)."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "titles": ["TITLE 1 #shorts", "TITLE 2 #shorts", "TITLE 3 #shorts", "TITLE 4 #shorts", "TITLE 5 #shorts"],
                        "descriptions": ["D1", "D2", "D3"],
                        "hashtags": ["#shorts"]
                    })
                }
            }]
        }
        mock_post.return_value = mock_resp

        # 1. User selected 'groq' but gave an xAI Grok key
        res1 = ai.generate_shorts_metadata(
            clip_title="Clutch play",
            api_key="xai-test-key-999",
            provider="groq",
        )
        self.assertIn("xAI Grok", res1["provider"])

        # 2. User selected 'grok' but gave a Groq key
        res2 = ai.generate_shorts_metadata(
            clip_title="Clutch play",
            api_key="gsk_test_key_888",
            provider="grok",
        )
        self.assertIn("Groq", res2["provider"])

    def test_clean_api_key_sanitization(self):
        """Verifies clean_api_key handles smart quotes, whitespace, Bearer prefix, and zero-width chars."""
        # Smart quotes
        self.assertEqual(ai.clean_api_key("“gsk_12345”"), "gsk_12345")
        # Single smart quotes
        self.assertEqual(ai.clean_api_key("‘xai-12345’"), "xai-12345")
        # Bearer prefix
        self.assertEqual(ai.clean_api_key("Bearer gsk_12345"), "gsk_12345")
        self.assertEqual(ai.clean_api_key("bearer xai-12345"), "xai-12345")
        # Zero-width spaces & BOM
        self.assertEqual(ai.clean_api_key("\ufeff\u200bgsk_12345\u200b"), "gsk_12345")

    @patch("requests.post")
    def test_401_cross_provider_failover_groq_to_grok(self, mock_post):
        """Verifies that if Groq returns 401, system seamlessly tries xAI Grok before giving up."""
        def side_effect(url, **kwargs):
            resp = MagicMock()
            if "groq.com" in url:
                resp.status_code = 401
                resp.text = json.dumps({"error": {"message": "Invalid API Key"}})
                resp.json.return_value = {"error": {"message": "Invalid API Key"}}
                return resp
            elif "x.ai" in url:
                resp.status_code = 200
                resp.json.return_value = {
                    "choices": [{
                        "message": {
                            "content": json.dumps({
                                "titles": ["T1 #shorts", "T2 #shorts", "T3 #shorts", "T4 #shorts", "T5 #shorts"],
                                "descriptions": ["D1", "D2", "D3"],
                                "hashtags": ["#shorts"]
                            })
                        }
                    }]
                }
                return resp
            resp.status_code = 500
            return resp

        mock_post.side_effect = side_effect

        res = ai.generate_shorts_metadata(
            clip_title="Clutch play",
            api_key="key_that_fails_on_groq_but_works_on_xai",
            provider="groq",
        )
        self.assertEqual(len(res["titles"]), 5)
        self.assertIn("xAI Grok", res["provider"])
        self.assertTrue(res.get("api_connected"))




class TestYouTubeMultiAccount(unittest.TestCase):
    """Verifies multi-account channel management and broadcast uploads."""

    def setUp(self):
        self.test_accounts_dir = yt.ACCOUNTS_DIR / "_test_accounts"
        self.test_accounts_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        import shutil
        if self.test_accounts_dir.is_dir():
            shutil.rmtree(self.test_accounts_dir, ignore_errors=True)

    def test_accounts_listing_and_disconnect(self):
        # Create dummy channel 1
        ch1 = {
            "channel_id": "UC_TEST_1",
            "channel_title": "Main Gaming Channel",
            "channel_avatar": "https://example.com/avatar1.jpg",
            "channel_custom_url": "@MainGaming",
            "token_data": {"token": "fake_token_1", "refresh_token": "fake_refresh_1"},
            "updated_at": 1729000000,
        }
        ch2 = {
            "channel_id": "UC_TEST_2",
            "channel_title": "Shorts Clips Daily",
            "channel_avatar": "https://example.com/avatar2.jpg",
            "channel_custom_url": "@ShortsClips",
            "token_data": {"token": "fake_token_2", "refresh_token": "fake_refresh_2"},
            "updated_at": 1729000100,
        }

        # Save to actual ACCOUNTS_DIR with unique test prefixes
        file1 = yt.ACCOUNTS_DIR / "UC_TEST_1.json"
        file2 = yt.ACCOUNTS_DIR / "UC_TEST_2.json"

        with open(file1, "w", encoding="utf-8") as f:
            json.dump(ch1, f)
        with open(file2, "w", encoding="utf-8") as f:
            json.dump(ch2, f)

        try:
            status = yt.get_youtube_auth_status()
            self.assertTrue(status["has_secrets"])
            # Verify accounts array exists
            self.assertIn("accounts", status)
            account_ids = [a["channel_id"] for a in status["accounts"]]
            self.assertIn("UC_TEST_1", account_ids)
            self.assertIn("UC_TEST_2", account_ids)

            # Test disconnecting single account
            removed = yt.disconnect_youtube_account("UC_TEST_1")
            self.assertTrue(removed)
            self.assertFalse(file1.is_file())
            self.assertTrue(file2.is_file())

            status_after = yt.get_youtube_auth_status()
            account_ids_after = [a["channel_id"] for a in status_after["accounts"]]
            self.assertNotIn("UC_TEST_1", account_ids_after)
            self.assertIn("UC_TEST_2", account_ids_after)

        finally:
            file1.unlink(missing_ok=True)
            file2.unlink(missing_ok=True)

    @patch("core.youtube_uploader.upload_single_channel_short")
    @patch("core.youtube_uploader._get_credentials_for_channel")
    def test_multi_channel_broadcast_upload(self, mock_get_creds, mock_single_upload):
        mock_creds = MagicMock()
        mock_get_creds.side_effect = lambda cid: (
            mock_creds,
            {"channel_id": cid, "channel_title": f"Channel {cid}"}
        )

        mock_single_upload.side_effect = lambda **kwargs: {
            "channel_id": kwargs["channel_meta"]["channel_id"],
            "channel_title": kwargs["channel_meta"]["channel_title"],
            "video_id": f"vid_{kwargs['channel_meta']['channel_id']}",
            "shorts_url": f"https://youtube.com/shorts/vid_{kwargs['channel_meta']['channel_id']}",
            "watch_url": f"https://youtube.com/watch?v=vid_{kwargs['channel_meta']['channel_id']}",
            "title": kwargs["title"],
            "privacy_status": kwargs["privacy_status"],
        }

        # Create a dummy test video
        test_video = yt.CREDENTIALS_DIR / "dummy_test.mp4"
        test_video.write_bytes(b"dummy mp4 content")

        try:
            res = yt.upload_shorts_video(
                video_path=test_video,
                title="Epic Multi-Upload Short #shorts",
                description="Test broadcast to 2 channels",
                channel_ids=["UC_CHANNEL_A", "UC_CHANNEL_B"],
            )

            self.assertEqual(res["total_uploaded"], 2)
            self.assertEqual(len(res["results"]), 2)
            self.assertEqual(res["results"][0]["channel_id"], "UC_CHANNEL_A")
            self.assertEqual(res["results"][1]["channel_id"], "UC_CHANNEL_B")
            self.assertEqual(mock_single_upload.call_count, 2)
        finally:
            test_video.unlink(missing_ok=True)


class TestAppEndpoints(unittest.TestCase):
    """Verifies FastAPI endpoints for AI providers and YouTube multi-account."""

    def setUp(self):
        self.client = TestClient(app.app)

    def test_ai_providers_endpoint(self):
        resp = self.client.get("/api/ai/providers")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("providers", data)
        self.assertGreaterEqual(len(data["providers"]), 8)

    def test_ai_generate_metadata_endpoint(self):
        resp = self.client.post("/api/ai/generate-metadata", json={
            "clip_title": "Grand Jackpot Winner",
            "category": "casino",
            "win_amount": "$50,000",
            "streamer": "ClassyBeef",
            "provider": "offline",
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["titles"]), 5)
        self.assertEqual(len(data["descriptions"]), 3)
        self.assertGreaterEqual(len(data["hashtags"]), 5)

    def test_youtube_accounts_endpoint(self):
        resp = self.client.get("/api/youtube/accounts")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("accounts", data)
        self.assertIsInstance(data["accounts"], list)


if __name__ == "__main__":
    unittest.main()
