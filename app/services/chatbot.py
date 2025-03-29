import google.generativeai as genai
from flask import current_app

def query_gemini(prompt, analysis_context=None):
    """
    Mengirim pertanyaan ke Google Gemini API dan mendapatkan respons
    """
    try:
        # Konfigurasi API key dari config
        api_key = current_app.config['GEMINI_API_KEY']
        genai.configure(api_key=api_key)
        
        # Siapkan model
        model = genai.GenerativeModel(model_name="gemini-2.0-flash")
        
        # Tambahkan konteks analisis sentimen jika tersedia
        if analysis_context:
            # Memproses data top_topics - pastikan isinya string
            top_topics_str = ""
            if 'top_topics' in analysis_context and isinstance(analysis_context['top_topics'], list):
                top_topics = []
                for topic in analysis_context['top_topics']:
                    if isinstance(topic, dict) and 'topic' in topic:
                        top_topics.append(topic['topic'])
                    elif isinstance(topic, str):
                        top_topics.append(topic)
                top_topics_str = ', '.join(top_topics)
            
            # Memproses data top_hashtags - pastikan isinya string
            top_hashtags_str = ""
            if 'top_hashtags' in analysis_context and isinstance(analysis_context['top_hashtags'], list):
                top_hashtags = []
                for hashtag in analysis_context['top_hashtags']:
                    if isinstance(hashtag, dict) and 'tag' in hashtag:
                        top_hashtags.append(hashtag['tag'])
                    elif isinstance(hashtag, str):
                        top_hashtags.append(hashtag)
                top_hashtags_str = ', '.join(top_hashtags)
            
            context = f"""
            Berikut adalah hasil analisis sentimen dari data X tentang {analysis_context['title']}:
            - Total tweet: {analysis_context['total_tweets']}
            - Sentimen Positif: {analysis_context['positive_count']} tweets ({analysis_context['positive_percent']}%)
            - Sentimen Netral: {analysis_context['neutral_count']} tweets ({analysis_context['neutral_percent']}%)
            - Sentimen Negatif: {analysis_context['negative_count']} tweets ({analysis_context['negative_percent']}%)
            
            Topik utama yang dibicarakan: {top_topics_str}
            
            Hashtag populer: {top_hashtags_str}
            
            Judul analisis: {analysis_context['title']}
            
            Berdasarkan data tersebut, silakan berikan evaluasi kebijakan dan respons untuk pertanyaan berikut.
            Jawab dalam bahasa Indonesia yang formal dan profesional, namun tetap mudah dimengerti.
            Cantumkan angka-angka penting dari data analisis untuk mendukung argumentasi.
            Berikan 2-3 rekomendasi spesifik untuk perbaikan kebijakan berdasarkan sentimen publik yang terdeteksi.
            
            Format respons dengan paragraf yang terpisah, gunakan tanda '*' untuk kata yang perlu ditekankan, 
            dan buat daftar dengan tanda '-' jika diperlukan.
            """
            
            # Detect if prompt is about a specific policy
            
            full_prompt = f"{context}\n\nPertanyaan pengguna: {prompt}\n\n"
        else:
            full_prompt = prompt
        
        # Set generation config
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 2048,
        }
        
        # Send request to Gemini
        response = model.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        
        return response.text
    except Exception as e:
        return f"Maaf, terjadi kesalahan dalam berkomunikasi dengan Gemini API: {str(e)}"