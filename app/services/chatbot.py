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
            context = f"""
            Berikut adalah hasil analisis sentimen dari data X tentang {analysis_context['title']}:
            - Total tweet: {analysis_context['total_tweets']}
            - Sentimen Positif: {analysis_context['positive_count']} tweets ({analysis_context['positive_percent']}%)
            - Sentimen Netral: {analysis_context['neutral_count']} tweets ({analysis_context['neutral_percent']}%)
            - Sentimen Negatif: {analysis_context['negative_count']} tweets ({analysis_context['negative_percent']}%)
            
            Topik utama yang dibicarakan: {', '.join(analysis_context['top_topics'])}
            
            Hashtag populer: {', '.join(analysis_context['top_hashtags'])}
            
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