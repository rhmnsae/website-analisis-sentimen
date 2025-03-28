import unittest
import os
import pandas as pd
import torch
from unittest.mock import patch, MagicMock

# Set up paths for testing
os.environ['TESTING'] = 'True'

# Import functions to test
from app.services.preprocessing import preprocess_text, tokenize_text
from app.services.sentiment_analysis import extract_hashtags, extract_topics
from app.services.sentiment_analysis import analyze_sentiment_per_hashtag, extract_words_by_sentiment

class TestPreprocessing(unittest.TestCase):
    
    def test_preprocess_text_empty(self):
        """Test preprocessing of empty text"""
        self.assertEqual(preprocess_text(''), '')
        self.assertEqual(preprocess_text(float('nan')), '')
    
    def test_preprocess_text_urls(self):
        """Test preprocessing of text with URLs"""
        text = "Kunjungi website kami di https://example.com dan baca info terbaru"
        expected = "Kunjungi website kami di dan baca info terbaru"
        self.assertEqual(preprocess_text(text), expected)
    
    def test_preprocess_text_mentions(self):
        """Test preprocessing of text with mentions"""
        text = "Halo @username bagaimana kabarmu?"
        expected = "Halo bagaimana kabarmu"
        self.assertEqual(preprocess_text(text), expected)
    
    def test_preprocess_text_hashtags(self):
        """Test preprocessing of text with hashtags"""
        text = "Bahas #politik #ekonomi terkini"
        expected = "Bahas politik ekonomi terkini"
        self.assertEqual(preprocess_text(text), expected)
    
    def test_tokenize_text(self):
        """Test tokenization and stopword removal"""
        text = "Saya sedang belajar analisis sentimen dengan python"
        tokens = tokenize_text(text)
        # Stopwords "saya", "sedang", "dengan" should be removed
        self.assertNotIn("saya", tokens)
        self.assertNotIn("sedang", tokens)
        self.assertNotIn("dengan", tokens)
        # Content words should remain
        self.assertIn("belajar", tokens)
        self.assertIn("analisis", tokens)
        self.assertIn("sentimen", tokens)
        self.assertIn("python", tokens)


class TestSentimentAnalysis(unittest.TestCase):
    
    def setUp(self):
        """Set up test data"""
        # Create mock dataframe for testing
        self.mock_df = pd.DataFrame({
            'content': [
                "Saya sangat senang dengan #kebijakan baru ini!",
                "Pemerintah harus mengevaluasi #kebijakan yang kurang efektif",
                "Saya netral terhadap #perubahan ini, masih menunggu hasil",
                "#kebijakan baru sepertinya memberikan harapan baru",
                "Sangat kecewa dengan implementasi #perubahan yang lambat"
            ],
            'processed_text': [
                "saya sangat senang dengan kebijakan baru ini",
                "pemerintah harus mengevaluasi kebijakan yang kurang efektif",
                "saya netral terhadap perubahan ini masih menunggu hasil",
                "kebijakan baru sepertinya memberikan harapan baru",
                "sangat kecewa dengan implementasi perubahan yang lambat"
            ],
            'predicted_sentiment': ['Positif', 'Negatif', 'Netral', 'Positif', 'Negatif']
        })
    
    def test_extract_hashtags(self):
        """Test extraction of hashtags from tweets"""
        hashtag_counts = extract_hashtags(self.mock_df)
        
        # Should have two hashtags: #kebijakan (3 occurrences) and #perubahan (2 occurrences)
        self.assertEqual(len(hashtag_counts), 2)
        self.assertEqual(hashtag_counts['kebijakan'], 3)
        self.assertEqual(hashtag_counts['perubahan'], 2)
    
    def test_extract_topics(self):
        """Test extraction of topics from processed text"""
        topics = extract_topics(self.mock_df, num_topics=5, min_count=1)
        
        # Should extract topics like "kebijakan", "perubahan"
        topic_words = [topic['topic'] for topic in topics]
        self.assertIn('kebijakan', topic_words)
        self.assertIn('perubahan', topic_words)
    
    def test_analyze_sentiment_per_hashtag(self):
        """Test analysis of sentiment per hashtag"""
        hashtag_sentiment = analyze_sentiment_per_hashtag(self.mock_df)
        
        # Check if we have sentiment analysis for both hashtags
        hashtags = [hs['tag'] for hs in hashtag_sentiment]
        self.assertTrue(any('#kebijakan' in tag for tag in hashtags))
        self.assertTrue(any('#perubahan' in tag for tag in hashtags))
        
        # Check the sentiment distribution for #kebijakan
        kebijakan_sentiment = next((hs for hs in hashtag_sentiment if hs['tag'] == '#kebijakan'), None)
        if kebijakan_sentiment:
            # 2/3 positive, 1/3 negative
            self.assertEqual(kebijakan_sentiment['positive'], 67)  # 67%
            self.assertEqual(kebijakan_sentiment['negative'], 33)  # 33%
    
    def test_extract_words_by_sentiment(self):
        """Test extraction of words by sentiment"""
        sentiment_words = extract_words_by_sentiment(self.mock_df)
        
        # Check if we have words for each sentiment category
        self.assertTrue(len(sentiment_words['positive']) > 0)
        self.assertTrue(len(sentiment_words['neutral']) > 0)
        self.assertTrue(len(sentiment_words['negative']) > 0)
        
        # Check if positive words include "senang", "harapan"
        positive_words = [item['word'] for item in sentiment_words['positive']]
        self.assertTrue(any(word in positive_words for word in ['senang', 'harapan']))
        
        # Check if negative words include "kecewa", "kurang"
        negative_words = [item['word'] for item in sentiment_words['negative']]
        self.assertTrue(any(word in negative_words for word in ['kecewa', 'kurang']))


class TestModelIntegration(unittest.TestCase):
    
    @patch('app.services.sentiment_analysis.load_sentiment_model')
    @patch('torch.load')
    def test_model_loading(self, mock_torch_load, mock_load_model):
        """Test that model loading function works correctly"""
        # Skip actual loading in tests
        mock_tokenizer = MagicMock()
        mock_model = MagicMock()
        mock_load_model.return_value = (mock_tokenizer, mock_model)
        
        from app.services.sentiment_analysis import load_sentiment_model
        
        # Call the function
        tokenizer, model = load_sentiment_model()
        
        # Verify mock was called
        mock_load_model.assert_called_once()
        
        # Check that we get the expected return values
        self.assertEqual(tokenizer, mock_tokenizer)
        self.assertEqual(model, mock_model)


if __name__ == '__main__':
    unittest.main()