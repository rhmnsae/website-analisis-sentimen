import re
import pandas as pd
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

def preprocess_text(text):
    """
    Preprocessing teks untuk analisis sentimen
    """
    if pd.isna(text):
        return ""
        
    # Konversi ke string jika bukan string
    if not isinstance(text, str):
        text = str(text)
    
    # Menghapus URL
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    
    # Menghapus mentions
    text = re.sub(r'@\w+', '', text)
    
    # Menghapus hashtag (kita hanya hapus tanda #, kata tetap dipertahankan)
    text = re.sub(r'#(\w+)', r'\1', text)
    
    # Menghapus karakter khusus dan angka
    text = re.sub(r'[^\w\s]', '', text)
    
    # Menghapus spasi berlebih
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def tokenize_text(text):
    """
    Tokenize text into words and remove stopwords
    """
    if pd.isna(text) or text == "":
        return []
    
    # Download stopwords if needed
    try:
        id_stopwords = set(stopwords.words('indonesian'))
    except:
        nltk.download('stopwords')
        id_stopwords = set(stopwords.words('indonesian'))
    
    # Add custom stopwords
    custom_stopwords = {
        'yang', 'dan', 'di', 'dengan', 'untuk', 'pada', 'dalam', 'adalah', 'ini', 'itu',
        'ada', 'akan', 'dari', 'ke', 'ya', 'juga', 'saya', 'kita', 'kami', 'mereka',
        'dia', 'anda', 'atau', 'bahwa', 'karena', 'oleh', 'jika', 'maka', 'masih', 'dapat',
        'bisa', 'tersebut', 'agar', 'sebagai', 'secara', 'seperti', 'hingga', 'telah', 'tidak',
        'tak', 'tanpa', 'tapi', 'tetapi', 'lalu', 'mau', 'harus', 'namun', 'ketika', 'saat',
        'http', 'https', 'co', 't', 'a', 'amp', 'rt', 'nya', 'yg', 'dgn', 'utk', 'dr',
        'pd', 'jd', 'sdh', 'tdk', 'bgt', 'kalo', 'gitu', 'gak', 'kan', 'deh', 'sih'
    }
    
    all_stopwords = id_stopwords.union(custom_stopwords)
    
    # Simple word tokenization without relying on NLTK's word_tokenize
    # Split by whitespace and filter out non-alphanumeric characters
    try:
        # Try to use NLTK's word_tokenize if available
        nltk.download('punkt')
        from nltk.tokenize import word_tokenize
        tokens = word_tokenize(text.lower())
    except:
        # Fallback to simple tokenization if NLTK's word_tokenize fails
        tokens = re.findall(r'\b[a-zA-Z0-9]+\b', text.lower())
    
    # Remove stopwords and short words
    filtered_tokens = [word for word in tokens if word not in all_stopwords and len(word) > 2]
    
    return filtered_tokens