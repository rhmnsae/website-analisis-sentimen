import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Set non-interactive backend before importing plt
import seaborn as sns
from io import BytesIO
import base64
import numpy as np

def create_sentiment_plot(df):
    """
    Creates minimalist aesthetic sentiment distribution plot
    with consistent style matching word frequency visualization
    """
    # Tetapkan gaya seaborn yang minimalis
    sns.set_style("whitegrid", {'grid.linestyle': ':'})
    
    plt.figure(figsize=(5, 3))
    
    # Urutan sentimen yang konsisten
    sentiment_order = ['Positif', 'Netral', 'Negatif']
    
    # Warna monokrom yang sesuai dengan visualisasi frekuensi kata
    color_map = {
        'Positif': '#ffffff',  # Abu-abu sedang
        'Netral': '#9e9e9e',   # Abu-abu terang
        'Negatif': '#000000'   # Abu-abu gelap
    }
    
    # Buat plot dengan warna yang sesuai
    ax = sns.countplot(
        data=df, 
        x='predicted_sentiment', 
        palette=color_map,
        order=sentiment_order,
        edgecolor='black',
        alpha=0.9,
    )
    
    # Hapus bingkai kecuali di bagian bawah
    sns.despine(left=True, bottom=False)
    
    # Judul dan label sederhana
    plt.title('Distribusi Sentimen pada Dataset', fontsize=8, pad=6, fontweight='bold')
    plt.xlabel('Sentimen', fontsize=6)
    plt.ylabel('Jumlah', fontsize=6)
    
    # Rotasi xticks untuk menghemat ruang
    plt.xticks(fontsize=6)
    
    # Angka di atas bar dengan ukuran yang sesuai
    for p in ax.patches:
        height = p.get_height()
        ax.text(
            p.get_x() + p.get_width() / 2., 
            height + 5, 
            f'{int(height)}', 
            ha='center', 
            va='bottom', 
            fontsize=7
        )
    
    # Atur jarak antar komponen
    plt.tight_layout(pad=1.0)
    
    # Simpan plot ke buffer dan encode ke base64
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=200, bbox_inches='tight', facecolor='white')
    buffer.seek(0)
    plot_data = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    return plot_data

def create_improved_word_cloud(df):
    """
    Creates enhanced word cloud from tweets with better visualization and optimization
    with larger text display and improved overall appearance
    """
    try:
        if 'processed_text' not in df.columns or len(df) == 0:
            return None
        
        # Combine all processed text
        all_text = ' '.join(df['processed_text'].dropna().astype(str).tolist())
        
        # Enhanced stopwords for cleaner visualization
        extra_stopwords = {
            'yang', 'dan', 'di', 'dengan', 'untuk', 'pada', 'dalam', 'adalah', 'ini', 'itu',
            'ada', 'akan', 'dari', 'ke', 'ya', 'juga', 'rt', 'amp', 'yg', 'dgn', 'utk', 'dr',
            'pd', 'jd', 'sdh', 'tdk', 'bisa', 'ada', 'kalo', 'bgt', 'aja', 'gitu', 'gak', 'mau',
            'biar', 'kan', 'klo', 'deh', 'sih', 'nya', 'nih', 'loh', 'juga', 'kita', 'kami',
            'saya', 'mereka', 'dia', 'anda', 'atau', 'bahwa', 'karena', 'oleh', 'jika', 'maka',
            'masih', 'dapat', 'tersebut', 'agar', 'sebagai', 'secara', 'seperti', 'hingga', 'si',
            'oh', 'udah', 'udh', 'eh', 'ah', 'lah', 'ku', 'mu', 'ni', 'aja', 'dg', 'lg', 'yah',
            'ga', 'gk', 'kk', 'jg', 'sy', 'krn', 'tp', 'trs', 'dr', 'kl', 'bs', 'sm', 'dpt',
            'dtg', 'bnr', 'kpd', 'jgn', 'cm', 'blm', 'sdg', 'skrg', 'ckp', 'cuma'
        }
        
        # Tokenize text more effectively
        import re
        words = re.findall(r'\b[a-zA-Z]{4,}\b', all_text.lower())
        
        # Count word frequencies excluding stopwords
        from collections import Counter
        word_freq = Counter([word for word in words if word not in extra_stopwords])
        
        # Get top words for visualization
        top_words = dict(sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:150])
        
        if not top_words:
            return None
        
        # Increase figure size for better proportions and text readability
        plt.figure(figsize=(40, 25))
        
        # Use only top 30 words for better readability with larger text
        words = list(top_words.keys())[:100]
        frequencies = list(top_words.values())[:100]
        y_pos = np.arange(len(words))
        
        # Create color gradient from dark blue to light blue for better contrast
        colors = plt.cm.Blues(np.linspace(0.5, 0.9, len(y_pos)))
        
        # Create horizontal bar chart with enhanced styling and thicker bars
        bars = plt.barh(y_pos, frequencies, color=colors, height=0.9)
        
        # EXTREMELY LARGE TEXT: Dramatically increase font sizes for all text elements
        plt.yticks(y_pos, words, fontsize=50, fontweight='bold')  # Much larger word labels
        plt.xticks(fontsize=46)  # Much larger x-axis values
        plt.xlabel('Frekuensi', fontsize=56, fontweight='bold')  # Much larger x-axis label
        plt.title('Kata yang Sering Muncul dalam Tweet', fontsize=64, fontweight='bold')  # Much larger title
        
        # Add value labels to bars with increased padding and much larger font size
        for i, v in enumerate(frequencies):
            plt.text(v + (max(frequencies) * 0.02), i, str(v), 
                    color='black', fontweight='bold', fontsize=52,
                    va='center')
        
        # Improve overall appearance
        plt.grid(axis='x', linestyle='--', alpha=0.2)  # Subtle grid
        plt.tick_params(axis='both', which='major', pad=10)  # Add padding around ticks
        plt.gca().spines['top'].set_visible(False)  # Remove top border
        plt.gca().spines['right'].set_visible(False)  # Remove right border
        plt.gca().spines['bottom'].set_linewidth(2)  # Make bottom border thicker
        plt.gca().spines['left'].set_linewidth(2)  # Make left border thicker
        
        # Add more space to accommodate larger text
        plt.tight_layout(pad=4.0)
        
        # Create a cleaner, more professional visualization with higher resolution
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=500, bbox_inches='tight', facecolor='white')
        buffer.seek(0)
        plot_data = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return plot_data
    except Exception as e:
        print(f"Error creating improved word cloud: {e}")
        return None