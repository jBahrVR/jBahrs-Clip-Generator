import model_fetcher
import unittest
from unittest.mock import MagicMock, patch

class TestModelFetcher(unittest.TestCase):
    def test_is_chat_model(self):
        self.assertTrue(model_fetcher.is_chat_model("gpt-4o"))
        self.assertTrue(model_fetcher.is_chat_model("claude-3-5-sonnet"))
        self.assertTrue(model_fetcher.is_chat_model("gemini-1.5-pro"))
        self.assertTrue(model_fetcher.is_chat_model("openrouter/google/gemini-pro"))
        self.assertTrue(model_fetcher.is_chat_model("deepseek-chat"))
        
        self.assertFalse(model_fetcher.is_chat_model("text-embedding-3-small"))
        self.assertFalse(model_fetcher.is_chat_model("vision-only-model"))
        self.assertFalse(model_fetcher.is_chat_model("whisper-1"))
        
    @patch('model_fetcher.OpenAI')
    def test_fetch_openai_models(self, mock_openai):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_model1 = MagicMock()
        mock_model1.id = "gpt-4o"
        mock_model2 = MagicMock()
        mock_model2.id = "text-embedding-3"
        
        mock_client.models.list.return_value = [mock_model1, mock_model2]
        
        models = model_fetcher.fetch_openai_models("fake_key")
        self.assertEqual(models, ["gpt-4o"])

    @patch('model_fetcher.anthropic.Anthropic')
    def test_fetch_anthropic_models(self, mock_anthropic):
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        mock_model1 = MagicMock()
        mock_model1.id = "claude-3-sonnet"
        
        mock_client.models.list.return_value = [mock_model1]
        
        models = model_fetcher.fetch_anthropic_models("fake_key")
        self.assertEqual(models, ["claude-3-sonnet"])

    @patch('model_fetcher.genai')
    def test_fetch_google_models(self, mock_genai):
        mock_model1 = MagicMock()
        mock_model1.name = "models/gemini-3-flash"
        mock_model1.supported_generation_methods = ["generateContent"]
        
        mock_genai.list_models.return_value = [mock_model1]
        
        models = model_fetcher.fetch_google_models("fake_key")
        self.assertEqual(models, ["gemini-3-flash"])

if __name__ == '__main__':
    unittest.main()
