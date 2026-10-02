"""
Automated Unit Tests for Dynamic AI Model Discovery Engine (model_fetcher.py).
"""

import os
import json
import unittest
from unittest.mock import MagicMock, patch
import model_fetcher


class TestModelFetcher(unittest.TestCase):

    def test_baseline_catalog_curated_size(self):
        # Curated catalog should be between 10 and 20 ideal models
        self.assertGreaterEqual(len(model_fetcher.BASELINE_MODELS), 10)
        self.assertLessEqual(len(model_fetcher.BASELINE_MODELS), 20)
        self.assertIn("gemini-3.6-flash", model_fetcher.BASELINE_MODELS)
        self.assertIn("gpt-4o", model_fetcher.BASELINE_MODELS)
        self.assertIn("claude-3-7-sonnet-latest", model_fetcher.BASELINE_MODELS)

    @patch("os.path.exists", return_value=True)
    def test_load_cached_models(self, mock_exists):
        fake_cache = json.dumps({"timestamp": 123456.0, "models": ["custom-model-1", "custom-model-2"]})
        with patch("builtins.open", unittest.mock.mock_open(read_data=fake_cache)):
            models = model_fetcher.load_cached_models()
            self.assertEqual(models, ["custom-model-1", "custom-model-2"])

    def test_save_cached_models(self):
        with patch("builtins.open", unittest.mock.mock_open()) as mock_file:
            with patch("os.makedirs") as mock_dirs:
                model_fetcher.save_cached_models(["model-a", "model-b"])
                mock_file.assert_called_once()
                mock_dirs.assert_called_once()

    def test_fetch_google_models_empty_key(self):
        res = model_fetcher.fetch_google_models("")
        self.assertEqual(res, [])

    @patch("google.genai.Client")
    def test_fetch_google_models_curation(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        m1 = MagicMock()
        m1.name = "models/gemini-3.6-flash"

        m2 = MagicMock()
        m2.name = "models/gemini-embedding-001"

        m3 = MagicMock()
        m3.name = "models/gemini-3.1-pro-preview-customtools"

        m4 = MagicMock()
        m4.name = "models/gemini-3.6-pro"

        mock_client.models.list.return_value = [m1, m2, m3, m4]

        models = model_fetcher.fetch_google_models("fake-google-key")
        self.assertIn("gemini-3.6-flash", models)
        self.assertIn("gemini-3.6-pro", models)
        self.assertNotIn("gemini-embedding-001", models)
        self.assertNotIn("gemini-3.1-pro-preview-customtools", models)

    @patch("openai.OpenAI")
    def test_fetch_openai_models_mocked(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        m1 = MagicMock()
        m1.id = "gpt-4o"
        m2 = MagicMock()
        m2.id = "o3-mini"
        m3 = MagicMock()
        m3.id = "text-embedding-ada-002"

        mock_client.models.list.return_value = [m1, m2, m3]

        models = model_fetcher.fetch_openai_models("fake-openai-key")
        self.assertIn("gpt-4o", models)
        self.assertIn("o3-mini", models)
        self.assertNotIn("text-embedding-ada-002", models)

    @patch("anthropic.Anthropic")
    def test_fetch_anthropic_models_mocked(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        m1 = MagicMock()
        m1.id = "claude-3-7-sonnet-latest"
        mock_client.models.list.return_value = [m1]

        models = model_fetcher.fetch_anthropic_models("fake-anthropic-key")
        self.assertEqual(models, ["claude-3-7-sonnet-latest"])

    def test_fetch_openrouter_public_models(self):
        models = model_fetcher.fetch_openrouter_public_models()
        self.assertGreaterEqual(len(models), 1)
        self.assertLessEqual(len(models), 5)
        self.assertTrue(any("gemini-3.6-flash" in m for m in models))

    @patch("model_fetcher.fetch_google_models", return_value=["gemini-3.6-flash"])
    @patch("model_fetcher.fetch_openai_models", return_value=["gpt-4o"])
    @patch("model_fetcher.save_cached_models")
    def test_fetch_all_dynamic_models_hierarchy(self, mock_save, mock_oai, mock_goog):
        cfg = {"google": {"api_key": "test"}, "openai": {"api_key": "test"}}
        res = model_fetcher.fetch_all_dynamic_models(cfg, current_selection="my-active-model")

        # Active selection should be first
        self.assertEqual(res[0], "my-active-model")
        # Live provider models next
        self.assertIn("gemini-3.6-flash", res)
        self.assertIn("gpt-4o", res)
        # Baseline catalog preserved
        self.assertIn("claude-3-7-sonnet-latest", res)
        # Save was triggered
        mock_save.assert_called_once()
        # Ensure total curated models stays clean and concise (<= 20)
        self.assertLessEqual(len(res), 20)


if __name__ == "__main__":
    unittest.main()
