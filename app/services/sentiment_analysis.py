import os
import re
import torch
import pandas as pd
from datetime import datetime
from collections import Counter
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from nltk.corpus import stopwords
from app.services.preprocessing import preprocess_text, tokenize_text
from flask import current_app
import hashlib
import time
from functools import lru_cache

_analysis_cache = {}
# Waktu cache dalam detik (5 menit)
_CACHE_DURATION = 300

def get_file_hash(file_path):
    """
    Menghitung hash MD5 dari file untuk identifikasi unik
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

# Modifikasi fungsi predict_sentiments
def predict_sentiments(file_path):
    """
    Memprediksi sentimen dari teks dalam file CSV menggunakan model IndoBERT terlatih
    dengan mekanisme cache untuk mencegah duplikasi proses
    """
    # Cek apakah file ada
    if not os.path.exists(file_path):
        raise ValueError(f"File tidak ditemukan: {file_path}")
    
    # Hitung hash file
    file_hash = get_file_hash(file_path)
    
    # Cek cache
    current_time = time.time()
    if file_hash in _analysis_cache:
        cache_time, result_df = _analysis_cache[file_hash]
        # Cek apakah cache masih valid
        if current_time - cache_time < _CACHE_DURATION:
            print(f"Menggunakan hasil analisis dari cache untuk file: {file_path}")
            return result_df
    
    # Jika tidak ada di cache atau cache sudah kedaluwarsa, lakukan analisis
    print(f"Memulai analisis baru untuk file: {file_path}")
    
    # Muat data
    df = pd.read_csv(file_path)
    
    # Pastikan kolom full_text atau text ada
    if 'full_text' not in df.columns and 'text' not in df.columns:
        raise ValueError("File CSV harus memiliki kolom 'full_text' atau 'text'")
    
    # Gunakan kolom text jika full_text tidak ada
    text_column = 'full_text' if 'full_text' in df.columns else 'text'
    
    # Preprocessing teks
    print("Preprocessing teks...")
    df['processed_text'] = df[text_column].apply(preprocess_text)
    
    # Muat tokenizer dan model terlatih
    tokenizer, model = load_sentiment_model()
    
    # Siapkan device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.to(device)
    model.eval()
    
    # Siapkan hasil
    results = []
    confidences = []
    sentiment_labels = ['Negatif', 'Netral', 'Positif']
    
    print(f"Melakukan prediksi sentimen untuk {len(df)} tweets...")
    
    # Prediksi dalam batch
    batch_size = 16
    for i in range(0, len(df), batch_size):
        batch_texts = df['processed_text'].iloc[i:i+batch_size].tolist()
        
        # Tokenisasi
        encodings = tokenizer(
            batch_texts,
            add_special_tokens=True,
            max_length=128,
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt'
        )
        
        input_ids = encodings['input_ids'].to(device)
        attention_mask = encodings['attention_mask'].to(device)
        
        # Prediksi
        with torch.no_grad():
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask
            )
            
            probs = torch.nn.functional.softmax(outputs.logits, dim=1)
            preds = torch.argmax(probs, dim=1)
            
            batch_results = [sentiment_labels[pred] for pred in preds.cpu().tolist()]
            batch_confidences = [float(probs[i, preds[i]]) * 100 for i in range(len(preds))]
            
            results.extend(batch_results)
            confidences.extend(batch_confidences)
    
    # Tambahkan hasil prediksi ke dataframe
    df['predicted_sentiment'] = results
    df['confidence'] = confidences
    
    # Tambahkan tanggal jika ada created_at
    if 'created_at' in df.columns:
        df['date'] = pd.to_datetime(df['created_at'], 
                             format='%a %b %d %H:%M:%S %z %Y',  # Format Twitter
                             errors='coerce').dt.strftime('%d %b %Y')
    else:
        # Gunakan tanggal hari ini jika tidak ada kolom created_at
        df['date'] = datetime.now().strftime('%d %b %Y')
    
    # Tambahkan kolom untuk likes, retweets, dan replies jika tidak ada
    if 'favorite_count' not in df.columns:
        df['favorite_count'] = 0
    if 'retweet_count' not in df.columns:
        df['retweet_count'] = 0
    if 'reply_count' not in df.columns:
        df['reply_count'] = 0
    
    # Ganti nama kolom untuk konsistensi dalam UI
    rename_columns = {
        'screen_name': 'username',
        'favorite_count': 'likes',
        'retweet_count': 'retweets',
        'reply_count': 'replies',
        text_column: 'content'
    }
    df = df.rename(columns={col: new_col for col, new_col in rename_columns.items() if col in df.columns})
    
    # Pastikan semua kolom yang diperlukan ada
    required_cols = ['username', 'content', 'date', 'likes', 'retweets', 'replies', 'predicted_sentiment', 'confidence']
    for col in required_cols:
        if col not in df.columns:
            if col == 'username':
                df['username'] = 'user' + df.index.astype(str)
            else:
                df[col] = 0 if col in ['likes', 'retweets', 'replies', 'confidence'] else ''
    
    # Ensure tweet URL is available
    if 'tweet_url' not in df.columns and 'id_str' in df.columns:
        df['tweet_url'] = 'https://twitter.com/i/web/status/' + df['id_str'].astype(str)
    
    # Ensure image URL is available
    if 'image_url' not in df.columns and 'media_url' in df.columns:
        df['image_url'] = df['media_url']
    
    print("Prediksi selesai.")
    
    # Simpan hasil ke cache
    _analysis_cache[file_hash] = (current_time, df)
    
    return df

def load_sentiment_model(model_name='indolem/indobert-base-uncased'):
    """
    Memuat model IndoBERT dan tokenizer
    """
    # Cek apakah model terlatih ada
    model_path = current_app.config['MODEL_PATH']
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model {model_path} tidak ditemukan. Pastikan model terlatih tersedia.")
    
    # Muat tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    # Muat model dasar
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name, 
        num_labels=3  # 3 kelas: Negatif (0), Netral (1), Positif (2)
    )
    
    # Muat state model yang terlatih
    print(f"Memuat model terlatih dari {model_path}...")
    model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
    
    return tokenizer, model

def extract_hashtags(df):
    """
    Ekstrak hashtag dari tweets dan hitung frekuensinya
    """
    hashtag_pattern = re.compile(r'#(\w+)')
    all_hashtags = []
    
    for text in df['content']:
        try:
            hashtags = hashtag_pattern.findall(str(text).lower())
            all_hashtags.extend(hashtags)
        except:
            continue
    
    hashtag_counts = Counter(all_hashtags)
    return hashtag_counts

def extract_topics(df, num_topics=10, min_count=3):
    """
    Ekstrak topik dari dataset berdasarkan frekuensi kata
    """
    # Download stopwords jika belum ada
    try:
        indonesian_stopwords = set(stopwords.words('indonesian'))
    except:
        import nltk
        nltk.download('stopwords')
        indonesian_stopwords = set(stopwords.words('indonesian'))
    
    # Tambahkan stopwords kustom
    custom_stopwords = {
        'yang', 'dan', 'di', 'dengan', 'untuk', 'pada', 'dalam', 'dari', 
        'ke', 'ya', 'ini', 'itu', 'ada', 'juga', 'saya', 'kita', 'akan'
    }
    all_stopwords = indonesian_stopwords.union(custom_stopwords)
    
    # Ekstrak kata-kata dan hitung frekuensi
    word_freq = Counter()
    
    for text in df['processed_text']:
        try:
            words = str(text).lower().split()
            # Filter stopwords dan kata pendek
            filtered_words = [word for word in words if word not in all_stopwords and len(word) > 3]
            word_freq.update(filtered_words)
        except:
            continue
    
    # Ekstrak topik (kata-kata dengan frekuensi tertinggi)
    topics = [{"topic": word, "frequency": count} 
              for word, count in word_freq.most_common(num_topics) 
              if count >= min_count]
    
    return topics

def analyze_sentiment_per_hashtag(df):
    """
    Menganalisis sentimen berdasarkan hashtag
    """
    hashtag_pattern = re.compile(r'#(\w+)')
    hashtag_sentiments = {}
    
    for _, row in df.iterrows():
        try:
            text = str(row['content']).lower()
            sentiment = row['predicted_sentiment']
            hashtags = hashtag_pattern.findall(text)
            
            for tag in hashtags:
                if tag not in hashtag_sentiments:
                    hashtag_sentiments[tag] = {'Positif': 0, 'Netral': 0, 'Negatif': 0, 'total': 0}
                
                hashtag_sentiments[tag][sentiment] += 1
                hashtag_sentiments[tag]['total'] += 1
        except:
            continue
    
    # Convert to percentage and format for display
    result = []
    for tag, counts in hashtag_sentiments.items():
        if counts['total'] >= 3:  # Only include hashtags that appear at least 3 times
            result.append({
                'tag': f'#{tag}',
                'positive': round(counts['Positif'] / counts['total'] * 100),
                'neutral': round(counts['Netral'] / counts['total'] * 100),
                'negative': round(counts['Negatif'] / counts['total'] * 100),
                'total': counts['total']
            })
    
    return sorted(result, key=lambda x: x['total'], reverse=True)[:10]  # Return top 10

def get_top_users(df):
    """
    Mendapatkan pengguna dengan tweet terbanyak dan sentimen dominan mereka
    """
    if 'username' not in df.columns:
        return []
        
    # Group by username and count tweets
    user_counts = df.groupby('username').size().reset_index(name='count')
    
    # Calculate average engagement
    engagement_df = df.groupby('username')[['likes', 'retweets', 'replies']].mean().sum(axis=1).reset_index(name='avg_engagement')
    user_counts = user_counts.merge(engagement_df, on='username')
    
    # Get dominant sentiment for each user
    sentiment_counts = df.groupby(['username', 'predicted_sentiment']).size().reset_index(name='sentiment_count')
    dominant_sentiment = sentiment_counts.loc[sentiment_counts.groupby('username')['sentiment_count'].idxmax()]
    dominant_sentiment = dominant_sentiment[['username', 'predicted_sentiment']].rename(columns={'predicted_sentiment': 'dominant_sentiment'})
    
    # Merge all information
    user_info = user_counts.merge(dominant_sentiment, on='username')
    
    # Sort by tweet count and return top 10
    user_info = user_info.sort_values('count', ascending=False).head(10)
    
    # Convert to list of dictionaries for JSON
    return user_info.to_dict('records')

def extract_words_by_sentiment(df):
    """
    Extract most frequent words for each sentiment category with improved processing
    """
    # Initialize word frequency counters
    positive_words = Counter()
    neutral_words = Counter()
    negative_words = Counter()
    
    # Expanded stopwords with comprehensive list
    stopwords_list = set([
        'yang', 'dan', 'di', 'dengan', 'untuk', 'pada', 'dalam', 'adalah', 'ini', 'itu',
        'ada', 'akan', 'dari', 'ke', 'ya', 'juga', 'saya', 'kita', 'kami', 'mereka',
        'dia', 'anda', 'atau', 'bahwa', 'karena', 'oleh', 'jika', 'maka', 'masih', 'dapat',
        'bisa', 'tersebut', 'agar', 'sebagai', 'secara', 'seperti', 'hingga', 'telah', 'tidak',
        'tak', 'tanpa', 'tapi', 'tetapi', 'lalu', 'mau', 'harus', 'namun', 'ketika', 'saat',
        'http', 'https', 'co', 't', 'a', 'amp', 'rt', 'nya', 'yg', 'dgn', 'utk', 'dr',
        'pd', 'jd', 'sdh', 'tdk', 'bgt', 'kalo', 'gitu', 'gak', 'kan', 'deh', 'sih',
        'nih', 'si', 'oh', 'udah', 'udh', 'eh', 'ah', 'lah', 'ku', 'mu', 'nya', 'ni',
        'aja', 'dg', 'lg', 'yah', 'ya', 'ga', 'gk', 'kk', 'jg', 'sy', 'dpt', 'dtg',
        'bnr', 'tp', 'krn', 'kpd', 'jgn', 'cm', 'blm', 'sdg', 'skrg', 'ckp', 'cuma'
    ])
    
    try:
        # Process each tweet with more robust handling
        for _, row in df.iterrows():
            if pd.isna(row.get('processed_text', '')) or row.get('processed_text', '') == "":
                continue
                
            # Get sentiment
            sentiment = row.get('predicted_sentiment')
            if not sentiment:
                continue
                
            # Better tokenization with preprocessing
            text = row.get('processed_text', '').lower()
            
            # Remove URLs
            text = re.sub(r'https?:\/\/\S+', '', text)
            
            # Remove mentions and hashtags symbols but keep the words
            text = re.sub(r'@(\w+)', r'\1', text)
            text = re.sub(r'#(\w+)', r'\1', text)
            
            # Remove special characters and digits
            text = re.sub(r'[^\w\s]', ' ', text)
            text = re.sub(r'\d+', ' ', text)
            
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            # Tokenize
            tokens = text.split()
            
            # Filter out stopwords and short words
            filtered_tokens = [word for word in tokens 
                             if word not in stopwords_list 
                             and len(word) > 3
                             and not word.isdigit()]
            
            # Add to appropriate counter based on sentiment
            if sentiment == 'Positif':
                positive_words.update(filtered_tokens)
            elif sentiment == 'Netral':
                neutral_words.update(filtered_tokens)
            elif sentiment == 'Negatif':
                negative_words.update(filtered_tokens)
        
        # Get top words for each sentiment (top 20 to ensure we have enough for visualization)
        return {
            'positive': [{"word": word, "count": count} for word, count in positive_words.most_common(20)],
            'neutral': [{"word": word, "count": count} for word, count in neutral_words.most_common(20)],
            'negative': [{"word": word, "count": count} for word, count in negative_words.most_common(20)]
        }
    except Exception as e:
        print(f"Error in extract_words_by_sentiment: {e}")
        # Return empty data if there's an error
        return {
            'positive': [],
            'neutral': [],
            'negative': []
        }