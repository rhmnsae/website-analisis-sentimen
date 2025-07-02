import json
import os
import pandas as pd
from flask import Blueprint, current_app, flash, redirect, request, jsonify, send_file, session, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.services.sentiment_analysis import predict_sentiments, extract_hashtags, extract_topics
from app.services.sentiment_analysis import analyze_sentiment_per_hashtag, get_top_users, extract_words_by_sentiment
from app.services.visualization import create_sentiment_plot, create_improved_word_cloud
from app.models.database import db, Analysis, AnalysisData
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.lib.units import inch, cm
from reportlab.platypus import PageBreak
from reportlab.platypus.flowables import HRFlowable
from reportlab.graphics.charts.barcharts import VerticalBarChart
from app.services.utils import user_lock_required

analysis_bp = Blueprint('analysis', __name__)

def clean_for_json(value):
    """Convert NaN/None values to empty string for JSON serialization"""
    if pd.isna(value) or value is None:
        return ""
    return value

@analysis_bp.route('/api/analysis-data', methods=['GET'])
@login_required
def get_analysis_data():
    """Endpoint to get the current analysis data for the client"""
    analysis_id = request.args.get('id')
    
    # Jika ada parameter id, gunakan untuk mengambil data spesifik
    if analysis_id:
        try:
            analysis = Analysis.query.get_or_404(int(analysis_id))
            # Pastikan user punya akses
            if analysis.user_id != current_user.id:
                return jsonify({'error': 'Tidak memiliki akses ke analisis ini'}), 403
                
            analysis_data = AnalysisData.query.filter_by(analysis_id=analysis.id).first()
            if not analysis_data:
                return jsonify({'error': 'Data analisis tidak ditemukan'}), 404
                
            # Simpan di session untuk penggunaan lainnya
            session['analysis_file'] = analysis_data.file_path
            session['analysis_context'] = {
                'title': analysis.title,
                'description': analysis.description or '',
                'total_tweets': analysis.total_tweets,
                'positive_count': analysis.positive_count,
                'neutral_count': analysis.neutral_count,
                'negative_count': analysis.negative_count,
                'positive_percent': analysis.positive_percent,
                'neutral_percent': analysis.neutral_percent,
                'negative_percent': analysis.negative_percent
            }
            
            # Kembalikan data lengkap
            return jsonify(analysis_data.get_data())
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # Jika tidak ada parameter id, gunakan data dari session seperti sebelumnya
    if 'analysis_file' not in session:
        return jsonify({'error': 'No analysis data available'}), 404
    
    file_path = session.get('analysis_file')
    if not os.path.exists(file_path):
        return jsonify({'error': 'Analysis file not found'}), 404
    # Check if analysis_file exists in the session
    if 'analysis_file' not in session:
        return jsonify({'error': 'No analysis data available'}), 404
    
    file_path = session.get('analysis_file')
    if not os.path.exists(file_path):
        return jsonify({'error': 'Analysis file not found'}), 404
    
    # Get analysis data by ID from session
    analysis_context = session.get('analysis_context', {})
    
    try:
        # Baca file hasil analisis
        result_df = pd.read_csv(file_path)
        
        # Hitung statistik
        sentiment_counts = result_df['predicted_sentiment'].value_counts()
        total_tweets = len(result_df)
        
        # Ekstrak hashtags
        hashtag_counts = extract_hashtags(result_df)
        
        # Ekstrak topik
        topics = extract_topics(result_df)
        
        # Analisis sentimen per hashtag
        hashtag_sentiment = analyze_sentiment_per_hashtag(result_df)
        
        # Dapatkan pengguna teratas
        top_users = get_top_users(result_df)
        
        # Try to extract words by sentiment with improved function
        try:
            sentiment_words = extract_words_by_sentiment(result_df)
        except Exception as e:
            print(f"Error in sentiment word extraction: {e}")
            sentiment_words = {
                'positive': [],
                'neutral': [],
                'negative': []
            }
        
        # Create plots with updated color scheme
        sentiment_plot = create_sentiment_plot(result_df)
        
        # Create improved word cloud with new function
        try:
            word_cloud = create_improved_word_cloud(result_df)
        except Exception as e:
            print(f"Error creating word cloud: {e}")
            word_cloud = None
        
        # Siapkan data untuk tampilan
        positive_count = int(sentiment_counts.get('Positif', 0))
        neutral_count = int(sentiment_counts.get('Netral', 0))
        negative_count = int(sentiment_counts.get('Negatif', 0))
        
        title = analysis_context.get('title', 'Analisis Sentimen X')
        description = analysis_context.get('description', '')
        
        # Create analysis results with error checking for all components
        analysis_results = {
            'title': title,
            'description': description,
            'total_tweets': total_tweets,
            'positive_count': positive_count,
            'neutral_count': neutral_count,
            'negative_count': negative_count,
            'positive_percent': round((positive_count / total_tweets * 100), 1) if total_tweets > 0 else 0,
            'neutral_percent': round((neutral_count / total_tweets * 100), 1) if total_tweets > 0 else 0,
            'negative_percent': round((negative_count / total_tweets * 100), 1) if total_tweets > 0 else 0,
            'top_hashtags': [{'tag': tag, 'count': count} for tag, count in hashtag_counts.most_common(10)],
            'topics': topics,
            'hashtag_sentiment': hashtag_sentiment,
            'top_users': top_users,
            'sentiment_words': {
                'positive': sentiment_words.get('positive', []),
                'neutral': sentiment_words.get('neutral', []),
                'negative': sentiment_words.get('negative', [])
            },
            'sentiment_plot': sentiment_plot,
            'word_cloud': word_cloud if word_cloud else None
        }
        
        # Add necessary fields to tweets that we'll send directly to the client
        tweets_for_display = []
        for _, row in result_df.iterrows():
            tweet = {
                'username': clean_for_json(row.get('username', '')),
                'content': clean_for_json(row.get('content', '')),
                'date': clean_for_json(row.get('date', '')),
                'likes': clean_for_json(row.get('likes', 0)),
                'retweets': clean_for_json(row.get('retweets', 0)),
                'replies': clean_for_json(row.get('replies', 0)),
                'predicted_sentiment': clean_for_json(row.get('predicted_sentiment', '')),
                'confidence': clean_for_json(row.get('confidence', 0))
            }
            
            # Add optional fields if they exist
            for field in ['tweet_url', 'image_url', 'lang', 'location']:
                if field in row and not pd.isna(row[field]):
                    tweet[field] = clean_for_json(row[field])
            
            tweets_for_display.append(tweet)
        
        # Add tweets to the results
        analysis_results['tweets'] = tweets_for_display
        
        return jsonify(analysis_results)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# Modifikasi untuk fungsi upload_file dalam file app/routes/analysis_routes.py
@analysis_bp.route('/upload', methods=['POST', 'GET'])
@login_required
@user_lock_required  # Tambahkan decorator untuk lock per user
def upload_file():
    """
    Route untuk mengunggah dan menganalisis file CSV.
    Dengan lock untuk mencegah duplikasi proses.
    """
    # Jika metode GET, ini mungkin untuk force cleanup lock
    if request.method == 'GET':
        # Respond with simple success
        return jsonify({'status': 'success', 'message': 'Lock checked'})
    
    # Logging untuk memulai proses
    current_app.logger.info(f"User {current_user.id} ({current_user.username}) memulai upload dan analisis file")
    
    try:
        # 1. Validasi awal dan persiapan
        # Verifikasi model terlatih ada
        if not os.path.exists(current_app.config['MODEL_PATH']):
            current_app.logger.error(f"Model tidak ditemukan di {current_app.config['MODEL_PATH']}")
            return jsonify({
                'error': f'Model terlatih tidak ditemukan: {current_app.config["MODEL_PATH"]}. '
                         f'Mohon pindahkan model Anda ke folder models/'
            })
        
        # Cek apakah ada file yang diunggah
        if 'csv-file' not in request.files:
            current_app.logger.warning("Tidak ada bagian file dalam request")
            return jsonify({'error': 'No file part'})
        
        file = request.files['csv-file']
        if file.filename == '':
            current_app.logger.warning("Nama file kosong")
            return jsonify({'error': 'No selected file'})
        
        # 2. Proses file yang diunggah
        if file:
            try:
                # Dapatkan data dari form
                title = request.form.get('title', 'Analisis Sentimen X').strip()
                description = request.form.get('description', '').strip()
                
                current_app.logger.info(f"Memproses analisis: {title}")
                
                # Generate timestamp untuk membuat file dan nama analisis unik
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                
                # Cek apakah analisis dengan judul yang sama sudah ada
                existing_analysis = Analysis.query.filter_by(
                    user_id=current_user.id, 
                    title=title
                ).first()
                
                # Jika judul sudah ada, tambahkan timestamp ke judul
                original_title = title
                if existing_analysis:
                    title = f"{original_title} ({timestamp})"
                    current_app.logger.info(f"Judul duplikat terdeteksi. Mengubah judul menjadi '{title}'")
                
                # Buat nama file yang aman dan unik dengan timestamp
                secure_name = secure_filename(file.filename)
                unique_filename = f"{timestamp}_{secure_name}"
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                
                # Simpan file yang diunggah
                file.save(file_path)
                current_app.logger.info(f"File berhasil disimpan di: {file_path}")
                
                # 3. Proses analisis sentimen
                # Tentukan path output hasil analisis
                output_file = os.path.join(current_app.config['UPLOAD_FOLDER'], f'analyzed_{unique_filename}')
                
                # Proses file untuk analisis sentimen
                current_app.logger.info(f"Memulai analisis sentimen untuk file: {file_path}")
                
                # PENTING: Hanya ada satu pemanggilan predict_sentiments di sini
                try:
                    # Tambahkan log sebelum memanggil predict_sentiments
                    current_app.logger.info(f"Memanggil fungsi predict_sentiments untuk file: {file_path}")
                    
                    result_df = predict_sentiments(file_path)
                    
                    # Tambahkan log setelah predict_sentiments berhasil
                    current_app.logger.info(f"predict_sentiments berhasil - jumlah baris: {len(result_df)}")
                except Exception as e:
                    current_app.logger.error(f"Error pada predict_sentiments: {e}")
                    return jsonify({'error': f'Gagal melakukan analisis sentimen: {str(e)}'})
                
                # Simpan hasil analisis ke CSV
                result_df.to_csv(output_file, index=False)
                
                # Simpan path ke session
                session['analysis_file'] = output_file
                
                # 4. Siapkan data untuk respons dan database
                # Hitung statistik
                try:
                    sentiment_counts = result_df['predicted_sentiment'].value_counts()
                    total_tweets = len(result_df)
                except Exception as e:
                    current_app.logger.error(f"Error saat menghitung statistik: {e}")
                    return jsonify({'error': f'Gagal menghitung statistik: {str(e)}'})
                
                # Siapkan data untuk tampilan
                positive_count = int(sentiment_counts.get('Positif', 0))
                neutral_count = int(sentiment_counts.get('Netral', 0))
                negative_count = int(sentiment_counts.get('Negatif', 0))
                
                # Hitung persentase
                positive_percent = round((positive_count / total_tweets * 100), 1) if total_tweets > 0 else 0
                neutral_percent = round((neutral_count / total_tweets * 100), 1) if total_tweets > 0 else 0
                negative_percent = round((negative_count / total_tweets * 100), 1) if total_tweets > 0 else 0
                
                # Ekstrak data tambahan
                current_app.logger.info(f"Mengekstrak informasi tambahan (hashtags, topik, dll)")
                
                try:
                    hashtag_counts = extract_hashtags(result_df)
                    topics = extract_topics(result_df)
                    hashtag_sentiment = analyze_sentiment_per_hashtag(result_df)
                    top_users = get_top_users(result_df)
                except Exception as e:
                    current_app.logger.error(f"Error saat ekstraksi informasi tambahan: {e}")
                    # Lanjutkan meskipun ada error pada ekstraksi tambahan
                
                # Ekstrak kata-kata berdasarkan sentimen
                try:
                    sentiment_words = extract_words_by_sentiment(result_df)
                except Exception as e:
                    current_app.logger.error(f"Error dalam ekstraksi kata berdasarkan sentimen: {e}")
                    sentiment_words = {
                        'positive': [],
                        'neutral': [],
                        'negative': []
                    }
                
                # Buat visualisasi
                try:
                    sentiment_plot = create_sentiment_plot(result_df)
                except Exception as e:
                    current_app.logger.error(f"Error saat membuat plot sentimen: {e}")
                    sentiment_plot = None
                
                try:
                    word_cloud = create_improved_word_cloud(result_df)
                except Exception as e:
                    current_app.logger.error(f"Error saat membuat word cloud: {e}")
                    word_cloud = None
                
                # 5. Persiapkan data untuk respons JSON dan database
                analysis_results = {
                    'title': title,
                    'description': description,
                    'total_tweets': total_tweets,
                    'positive_count': positive_count,
                    'neutral_count': neutral_count,
                    'negative_count': negative_count,
                    'positive_percent': positive_percent,
                    'neutral_percent': neutral_percent,
                    'negative_percent': negative_percent,
                    'top_hashtags': [{'tag': tag, 'count': count} for tag, count in hashtag_counts.most_common(10)],
                    'topics': topics,
                    'hashtag_sentiment': hashtag_sentiment,
                    'top_users': top_users,
                    'sentiment_words': {
                        'positive': sentiment_words.get('positive', []),
                        'neutral': sentiment_words.get('neutral', []),
                        'negative': sentiment_words.get('negative', [])
                    },
                    'sentiment_plot': sentiment_plot,
                    'word_cloud': word_cloud if word_cloud else None
                }
                
                # Persiapkan data tweet untuk tampilan
                tweets_for_display = []
                for _, row in result_df.iterrows():
                    tweet = {
                        'username': clean_for_json(row.get('username', '')),
                        'content': clean_for_json(row.get('content', '')),
                        'date': clean_for_json(row.get('date', '')),
                        'likes': clean_for_json(row.get('likes', 0)),
                        'retweets': clean_for_json(row.get('retweets', 0)),
                        'replies': clean_for_json(row.get('replies', 0)),
                        'predicted_sentiment': clean_for_json(row.get('predicted_sentiment', '')),
                        'confidence': clean_for_json(row.get('confidence', 0))
                    }
                    
                    # Tambahkan field opsional jika ada
                    for field in ['tweet_url', 'image_url', 'lang', 'location']:
                        if field in row and not pd.isna(row[field]):
                            tweet[field] = clean_for_json(row[field])
                    
                    tweets_for_display.append(tweet)
                
                # Tambahkan tweets ke hasil analisis
                analysis_results['tweets'] = tweets_for_display
                
                # Simpan konteks analisis ke session untuk chatbot
                session['analysis_context'] = {
                    'title': title,
                    'description': description,
                    'total_tweets': total_tweets,
                    'positive_count': positive_count,
                    'neutral_count': neutral_count, 
                    'negative_count': negative_count,
                    'positive_percent': positive_percent,
                    'neutral_percent': neutral_percent,
                    'negative_percent': negative_percent,
                    'top_hashtags': [h['tag'] for h in analysis_results['top_hashtags'][:5]],
                    'top_topics': [t['topic'] for t in topics[:5]] if topics else []
                }
                
                # 6. Simpan analisis ke database
                current_app.logger.info(f"Menyimpan hasil analisis ke database")
                
                try:
                    # Buat objek analisis
                    new_analysis = Analysis(
                        title=title,
                        description=description,
                        total_tweets=total_tweets,
                        positive_count=positive_count,
                        neutral_count=neutral_count,
                        negative_count=negative_count,
                        positive_percent=positive_percent,
                        neutral_percent=neutral_percent,
                        negative_percent=negative_percent,
                        user_id=current_user.id
                    )
                    
                    # Tambahkan ke session database
                    db.session.add(new_analysis)
                    db.session.flush()  # Dapatkan ID tanpa commit
                    
                    # Simpan data detail analisis
                    analysis_data = AnalysisData(
                        analysis_id=new_analysis.id,
                        data_json=json.dumps(analysis_results),
                        file_path=output_file
                    )
                    
                    # Tambahkan ke session database
                    db.session.add(analysis_data)
                    
                    # Commit perubahan ke database
                    db.session.commit()
                    current_app.logger.info(f"Analisis berhasil disimpan ke database dengan ID: {new_analysis.id}")
                    
                    # 7. Kembalikan respons JSON
                    return jsonify(analysis_results)
                    
                except Exception as e:
                    # Rollback jika terjadi error
                    db.session.rollback()
                    current_app.logger.error(f"Error saat menyimpan ke database: {e}")
                    raise
                    
            except Exception as e:
                # Tangani error selama proses
                import traceback
                error_details = traceback.format_exc()
                current_app.logger.error(f"Error saat menganalisis file: {e}\n{error_details}")
                
                # Rollback database jika diperlukan
                try:
                    db.session.rollback()
                except:
                    pass
                    
                # Hapus file yang sudah diunggah jika terjadi error (opsional)
                try:
                    if 'file_path' in locals() and os.path.exists(file_path):
                        os.remove(file_path)
                        current_app.logger.info(f"File dihapus karena terjadi error: {file_path}")
                except Exception as e:
                    current_app.logger.error(f"Gagal menghapus file: {e}")
                    
                return jsonify({'error': str(e)})
    
    except Exception as e:
        # Tangani semua exception yang mungkin terjadi
        import traceback
        error_details = traceback.format_exc()
        current_app.logger.error(f"Error tak terduga: {e}\n{error_details}")
        return jsonify({'error': f'Error tak terduga: {str(e)}'})
    
    
@analysis_bp.route('/clean-lock', methods=['GET'])
@login_required
def clean_lock():
    """
    Route untuk membersihkan lock pengguna yang mungkin macet
    """
    from app.services.utils import UserLock
    
    try:
        # Buat lock object dan bersihkan
        lock_obj = UserLock(current_user.id)
        success = lock_obj.force_cleanup()
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Lock berhasil dibersihkan. Anda dapat mencoba analisis lagi sekarang.'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Gagal membersihkan lock, namun tidak ada lock aktif ditemukan.'
            }), 400
    except Exception as e:
        current_app.logger.error(f"Error saat membersihkan lock: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@analysis_bp.route('/filter_tweets', methods=['POST'])
@login_required
def filter_tweets():
    data = request.json
    sentiment_filter = data.get('sentiment', 'all')
    
    # Get the analysis file path from session
    file_path = session.get('analysis_file')
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'No analysis data available'})
    
    # Read the analysis results from file
    result_df = pd.read_csv(file_path)
    
    # Filter by sentiment
    if sentiment_filter != 'all':
        result_df = result_df[result_df['predicted_sentiment'] == sentiment_filter]
    
    # Prepare tweets for display
    tweets_for_display = []
    for _, row in result_df.iterrows():
        tweet = {
            'username': clean_for_json(row.get('username', '')),
            'content': clean_for_json(row.get('content', '')),
            'date': clean_for_json(row.get('date', '')),
            'likes': clean_for_json(row.get('likes', 0)),
            'retweets': clean_for_json(row.get('retweets', 0)),
            'replies': clean_for_json(row.get('replies', 0)),
            'predicted_sentiment': clean_for_json(row.get('predicted_sentiment', '')),
            'confidence': clean_for_json(row.get('confidence', 0))
        }
        
        # Add optional fields if they exist
        for field in ['tweet_url', 'image_url', 'lang', 'location']:
            if field in row and not pd.isna(row[field]):
                tweet[field] = clean_for_json(row[field])
        
        tweets_for_display.append(tweet)
        
    return jsonify({'tweets': tweets_for_display})

@analysis_bp.route('/download_report', methods=['GET'])
@login_required
def download_report():
    """Endpoint untuk mengunduh laporan analisis dalam format PDF"""
    # Cek apakah ada parameter id dari request
    analysis_id = request.args.get('id')
    
    # Jika ada parameter id, gunakan untuk mengambil data spesifik
    if analysis_id:
        try:
            # Ambil analisis berdasarkan ID
            analysis = Analysis.query.get_or_404(int(analysis_id))
            
            # Pastikan user punya akses
            if analysis.user_id != current_user.id:
                flash("Tidak memiliki akses ke analisis ini", "error")
                return redirect(url_for('history.index'))
                
            # Ambil data analisis
            analysis_data = AnalysisData.query.filter_by(analysis_id=analysis.id).first()
            if not analysis_data:
                flash("Data analisis tidak ditemukan", "error")
                return redirect(url_for('history.index'))
                
            # Gunakan data dari analisis untuk membuat laporan
            file_path = analysis_data.file_path
            
            # Buat analysis_context dari data analisis
            analysis_context = {
                'title': analysis.title,
                'description': analysis.description or '',
                'total_tweets': analysis.total_tweets,
                'positive_count': analysis.positive_count,
                'neutral_count': analysis.neutral_count,
                'negative_count': analysis.negative_count,
                'positive_percent': analysis.positive_percent,
                'neutral_percent': analysis.neutral_percent,
                'negative_percent': analysis.negative_percent
            }
            
            # Tambahkan top hashtags dan topics jika tersedia di data analisis
            try:
                data_json = analysis_data.get_data()
                
                # Ambil top_hashtags
                if 'top_hashtags' in data_json:
                    top_hashtags = []
                    for hashtag in data_json['top_hashtags'][:5]:
                        if isinstance(hashtag, dict) and 'tag' in hashtag:
                            top_hashtags.append(hashtag['tag'])
                        elif isinstance(hashtag, str):
                            top_hashtags.append(hashtag)
                    analysis_context['top_hashtags'] = top_hashtags
                
                # Ambil top topics
                if 'topics' in data_json:
                    top_topics = []
                    for topic in data_json['topics'][:5]:
                        if isinstance(topic, dict) and 'topic' in topic:
                            top_topics.append(topic['topic'])
                        elif isinstance(topic, str):
                            top_topics.append(topic)
                    analysis_context['top_topics'] = top_topics
            except Exception as e:
                current_app.logger.error(f"Error saat mengambil detail hashtag/topics: {e}")
                # Jika gagal, tetap gunakan analisis tanpa data tambahan
                analysis_context['top_hashtags'] = []
                analysis_context['top_topics'] = []
            
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
            return redirect(url_for('history.index'))
    else:
        # Gunakan data dari session (perilaku asli)
        if 'analysis_file' not in session or 'analysis_context' not in session:
            flash("Tidak ada data analisis yang tersedia. Silakan upload file CSV terlebih dahulu.", "warning")
            return redirect(url_for('main.input_data'))
        
        # Ambil data analisis dari file
        file_path = session.get('analysis_file')
        analysis_context = session.get('analysis_context')
    
    # Validasi file path
    if not os.path.exists(file_path):
        flash("File analisis tidak ditemukan.", "error")
        return redirect(url_for('main.input_data'))
    
    # Baca data analisis
    analysis_df = pd.read_csv(file_path)
    
    # Siapkan buffer untuk PDF
    buffer = BytesIO()
    
    # Buat dokumen PDF
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                           rightMargin=50, leftMargin=50,
                           topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()
    elements = []
    
    # ============= DEFINISI STYLE =============
    
    # Warna
    primary_color = colors.HexColor('#1b3a59')     # Biru tua
    secondary_color = colors.HexColor('#2d6b9c')   # Biru sedang
    accent_color = colors.HexColor('#f1b211')      # Kuning emas
    light_color = colors.HexColor('#e6e6e6')       # Abu muda
    
    # Definisi style halaman
    def add_page_number(canvas, doc):
        page_num = canvas.getPageNumber()
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.darkgrey)
        canvas.drawRightString(doc.pagesize[0] - 50, 30, f"Halaman {page_num}")
        canvas.drawString(50, 30, f"Laporan Analisis Sentimen • {datetime.now().strftime('%d-%m-%Y')}")
        canvas.restoreState()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=22,
        alignment=1,  # Center alignment
        spaceAfter=12,
        textColor=primary_color,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        fontSize=16,
        alignment=1,
        spaceAfter=20,
        textColor=secondary_color
    )
    
    heading1_style = ParagraphStyle(
        'Heading1',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=primary_color,
        spaceBefore=16,
        spaceAfter=10,
        underline=1,
        leftIndent=0
    )
    
    heading2_style = ParagraphStyle(
        'Heading2',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=secondary_color,
        spaceBefore=12,
        spaceAfter=8,
        leftIndent=0
    )
    
    heading3_style = ParagraphStyle(
        'Heading3',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=secondary_color,
        spaceBefore=10,
        spaceAfter=6,
        leftIndent=10
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=8,
        textColor=colors.black,
        leading=14,  # line spacing
        leftIndent=0
    )
    
    bullet_style = ParagraphStyle(
        'Bullet',
        parent=normal_style,
        leftIndent=15,
        bulletIndent=0,
        bulletText='•'
    )
    
    # Fungsi untuk membuat horizontal line
    def horizontal_line():
        line = HRFlowable(
            width="100%",
            thickness=1,
            color=secondary_color,
            spaceBefore=5,
            spaceAfter=10
        )
        elements.append(line)
    
   # ============= HALAMAN SAMPUL =============
    elements.append(Spacer(1, 1*inch))
    elements.append(Paragraph("LAPORAN ANALISIS SENTIMEN", title_style))
    elements.append(Paragraph("Platform X (Twitter)", subtitle_style))
    elements.append(Spacer(1, 0.5*inch))
    
    # Dua garis pembatas
    horizontal_line()
    elements.append(Spacer(1, 0.2*inch))
    
    # Judul Analisis
    elements.append(Paragraph(f"<b>Topik:</b> {analysis_context['title']}", heading1_style))
    elements.append(Spacer(1, 0.5*inch))
    
    # Metadata dan statistik utama
    date_text = f"<b>Tanggal Pembuatan:</b> {datetime.now().strftime('%d %B %Y')}"
    time_text = f"<b>Waktu:</b> {datetime.now().strftime('%H:%M')}"
    total_text = f"<b>Total Data:</b> {analysis_context['total_tweets']} tweets"
    period_text = f"<b>Periode Analisis:</b> {datetime.now().strftime('%B %Y')}"
    
    elements.append(Paragraph(date_text, normal_style))
    elements.append(Paragraph(time_text, normal_style))
    elements.append(Paragraph(total_text, normal_style))
    elements.append(Paragraph(period_text, normal_style))
    
    elements.append(Spacer(1, 0.5*inch))
    horizontal_line()
    
    # Statistik sentimen halaman depan
    pos_percent = analysis_context['positive_percent']
    neu_percent = analysis_context['neutral_percent']
    neg_percent = analysis_context['negative_percent']
    
    dominant = "Positif" if pos_percent >= max(neu_percent, neg_percent) else \
               "Netral" if neu_percent >= max(pos_percent, neg_percent) else "Negatif"
    
    sentiment_summary = f"""
    <b>Ringkasan Sentimen:</b><br/>
    • <font color="green">Positif</font>: {pos_percent}%<br/>
    • <font color="blue">Netral</font>: {neu_percent}%<br/> 
    • <font color="red">Negatif</font>: {neg_percent}%<br/><br/>
    <b>Sentimen Dominan:</b> {dominant}
    """
    
    elements.append(Paragraph(sentiment_summary, normal_style))
    elements.append(Spacer(1, 1*inch))
    
    # Watermark
    elements.append(Paragraph(
        "Dihasilkan oleh Aplikasi Analisis Sentimen X",
        ParagraphStyle(
            'Watermark',
            parent=normal_style,
            alignment=1,
            textColor=colors.gray,
            fontSize=10
        )
    ))
    
    # Page break
    elements.append(PageBreak())
    
    # ============= DAFTAR ISI =============
    elements.append(Paragraph("DAFTAR ISI", heading1_style))
    horizontal_line()
    
    toc_items = [
        "<b>1. Ringkasan Eksekutif</b>",
        "<b>2. Analisis Sentimen</b>",
        "   2.1 Distribusi Sentimen",
        "   2.2 Visualisasi Sentimen",
        "<b>3. Topik dan Hashtag Utama</b>",
        "   3.1 Topik Utama",
        "   3.2 Hashtag Populer",
        "<b>4. Sampel Tweet</b>",
        "   4.1 Tweet Positif",
        "   4.2 Tweet Netral",
        "   4.3 Tweet Negatif",
        "<b>5. Kesimpulan dan Rekomendasi</b>",
        "   5.1 Kesimpulan",
        "   5.2 Rekomendasi",
        "   5.3 Metodologi Analisis",
    ]
    
    for item in toc_items:
        elements.append(Paragraph(item, normal_style))
        elements.append(Spacer(1, 5))
    
    elements.append(Spacer(1, 0.5*inch))
    elements.append(PageBreak())
    
    # ============= RINGKASAN EKSEKUTIF =============
    elements.append(Paragraph("1. RINGKASAN EKSEKUTIF", heading1_style))
    horizontal_line()
    
    executive_summary = f"""
    Laporan ini menyajikan hasil analisis sentimen terhadap {analysis_context['total_tweets']} tweets 
    yang terkait dengan "{analysis_context['title']}" pada platform X (Twitter). Data dianalisis 
    menggunakan model pembelajaran mesin (machine learning) berbasis IndoBERT yang terlatih 
    untuk mengklasifikasikan sentimen ke dalam tiga kategori: Positif, Netral, dan Negatif.
    """
    elements.append(Paragraph(executive_summary, normal_style))
    
    elements.append(Paragraph("Temuan Utama:", heading3_style))
    
    # Ambil top topics dan hashtags jika tersedia di context
    top_topics_text = "belum teridentifikasi"
    if 'top_topics' in analysis_context and analysis_context['top_topics']:
        top_topics_text = ", ".join(analysis_context['top_topics'][:3])
    
    top_hashtags_text = "belum teridentifikasi"
    if 'top_hashtags' in analysis_context and analysis_context['top_hashtags']:
        top_hashtags_text = ", ".join(analysis_context['top_hashtags'][:3])
    
    findings_text = f"""
    • Dari total {analysis_context['total_tweets']} tweets yang dianalisis, <b>{pos_percent}%</b> memiliki 
      sentimen positif, <b>{neu_percent}%</b> netral, dan <b>{neg_percent}%</b> negatif.<br/><br/>
      
    • Sentimen <b>{dominant}</b> mendominasi percakapan tentang topik ini, 
      menunjukkan bahwa publik secara umum memiliki pandangan {'positif' if dominant == 'Positif' else
      'netral' if dominant == 'Netral' else 'negatif'} terhadap "{analysis_context['title']}".<br/><br/>
      
    • Topik-topik utama yang sering dibicarakan meliputi: {top_topics_text}.<br/><br/>
    
    • Hashtag populer yang sering digunakan dalam tweets meliputi: {top_hashtags_text}.<br/><br/>
    """
    elements.append(Paragraph(findings_text, normal_style))
    
    # Insight tambahan berdasarkan sentimen dominan
    insight_text = {
        "Positif": f"""
        <b>Insight Utama:</b> Dominasi sentimen positif ({pos_percent}%) menunjukkan adanya 
        penerimaan dan dukungan publik yang baik terhadap topik ini. Penting untuk mempertahankan 
        momentum positif ini dengan terus mengkomunikasikan aspek-aspek yang mendapatkan respons baik.<br/><br/>
        """,
        
        "Netral": f"""
        <b>Insight Utama:</b> Dominasi sentimen netral ({neu_percent}%) menunjukkan bahwa banyak 
        percakapan bersifat informatif atau faktual tanpa menunjukkan emosi kuat. Ini menandakan perlu 
        upaya lebih untuk menggeser sentimen ke arah positif dengan mengkomunikasikan nilai dan manfaat.<br/><br/>
        """,
        
        "Negatif": f"""
        <b>Insight Utama:</b> Dominasi sentimen negatif ({neg_percent}%) menunjukkan adanya 
        kekhawatiran atau ketidakpuasan publik terhadap topik ini. Penting untuk mengidentifikasi 
        sumber masalah utama dan memberikan klarifikasi serta solusi untuk memperbaiki persepsi.<br/><br/>
        """
    }
    
    elements.append(Paragraph(insight_text[dominant], normal_style))
    elements.append(Spacer(1, 0.3*inch))
    elements.append(PageBreak())
    
    # ============= ANALISIS SENTIMEN =============
    elements.append(Paragraph("2. ANALISIS SENTIMEN", heading1_style))
    horizontal_line()
    
    # Distribusi Sentimen
    elements.append(Paragraph("2.1 Distribusi Sentimen", heading2_style))
    
    sentiment_table_content = f"""
    <b>Total Tweets Dianalisis:</b> {analysis_context['total_tweets']}<br/><br/>
    <font color="green"><b>Tweet Positif:</b> {analysis_context['positive_count']} ({pos_percent}%)</font><br/>
    <font color="blue"><b>Tweet Netral:</b> {analysis_context['neutral_count']} ({neu_percent}%)</font><br/>
    <font color="red"><b>Tweet Negatif:</b> {analysis_context['negative_count']} ({neg_percent}%)</font>
    """
    
    elements.append(Paragraph(sentiment_table_content, 
        ParagraphStyle('BoxedContent', 
                      parent=normal_style,
                      backColor=light_color,
                      borderColor=secondary_color,
                      borderWidth=1,
                      borderPadding=10,
                      borderRadius=5,
                      spaceBefore=10,
                      spaceAfter=10)))
    
    # Analisis Trend
    sentiment_analysis = f"""
    <b>Analisis Sentimen:</b><br/><br/>
    Berdasarkan data di atas, sentimen <b>{dominant}</b> mendominasi percakapan tentang 
    "{analysis_context['title']}" dengan persentase {pos_percent if dominant == 'Positif' else 
    neu_percent if dominant == 'Netral' else neg_percent}%. 
    """
    elements.append(Paragraph(sentiment_analysis, normal_style))
    
    # Visualisasi Sentimen
    elements.append(Paragraph("2.2 Visualisasi Sentimen", heading2_style))
    
    # Diagram Lingkaran (Pie Chart)
    elements.append(Paragraph("Distribusi Sentimen (Pie Chart):", heading3_style))
    
    # Buat pie chart
    drawing = Drawing(400, 200)
    pie = Pie()
    pie.x = 150
    pie.y = 25
    pie.width = 150
    pie.height = 150
    pie.data = [analysis_context['positive_count'], analysis_context['neutral_count'], analysis_context['negative_count']]
    pie.labels = [f'Positif ({pos_percent}%)', f'Netral ({neu_percent}%)', f'Negatif ({neg_percent}%)']
    
    # Colors
    pie.slices.strokeWidth = 0.5
    pie.slices[0].fillColor = colors.green
    pie.slices[1].fillColor = colors.blue
    pie.slices[2].fillColor = colors.red
    
    # Add legend
    from reportlab.graphics.charts.legends import Legend
    legend = Legend()
    legend.alignment = 'right'
    legend.x = 320
    legend.y = 100
    legend.colorNamePairs = [(colors.green, f'Positif ({pos_percent}%)'), 
                             (colors.blue, f'Netral ({neu_percent}%)'),
                             (colors.red, f'Negatif ({neg_percent}%)')]
    
    drawing.add(pie)
    drawing.add(legend)
    elements.append(drawing)
    
    elements.append(Paragraph("Interpretasi:", heading3_style))
    chart_interpretation = f"""
    Diagram lingkaran di atas menunjukkan dominasi sentimen {dominant.lower()} dalam percakapan tentang 
    "{analysis_context['title']}". Hal ini mengindikasikan bahwa publik secara umum {'mendukung dan memiliki pandangan positif' if dominant == 'Positif' else 'bersikap netral dan objektif' if dominant == 'Netral' 
    else 'memiliki kekhawatiran dan kritik'} terhadap topik ini.
    """
    elements.append(Paragraph(chart_interpretation, normal_style))
    elements.append(PageBreak())
    
    # ============= TOPIK DAN HASHTAG UTAMA =============
    elements.append(Paragraph("3. TOPIK DAN HASHTAG UTAMA", heading1_style))
    horizontal_line()
    
    # Topik Utama
    elements.append(Paragraph("3.1 Topik Utama", heading2_style))
    
    topic_intro = f"""
    Berikut adalah topik-topik utama yang paling sering muncul dalam tweets terkait 
    "{analysis_context['title']}":
    """
    elements.append(Paragraph(topic_intro, normal_style))
    
    # Get topics from analysis context
    top_topics = []
    if 'top_topics' in analysis_context:
        top_topics = analysis_context['top_topics'][:8] if analysis_context['top_topics'] else []
    
    if top_topics:
        # Format topic list with bullet points
        topics_list = ""
        for i, topic in enumerate(top_topics, 1):
            topics_list += f"<b>{i}.</b> {topic}<br/>"
        
        # Display topics in a box
        elements.append(Paragraph(topics_list, 
            ParagraphStyle('BoxedTopics', 
                          parent=normal_style,
                          backColor=light_color,
                          borderColor=secondary_color,
                          borderWidth=1,
                          borderPadding=10,
                          spaceBefore=10,
                          spaceAfter=10)))
    else:
        elements.append(Paragraph("Data topik utama tidak tersedia.", normal_style))
    
    # Topic Analysis
    topic_analysis = f"""
    <b>Analisis Topik:</b><br/><br/>
    Topik-topik utama yang dibicarakan mencerminkan fokus perhatian publik terkait 
    "{analysis_context['title']}". Dengan memahami topik-topik ini, kita dapat menyesuaikan
    strategi komunikasi untuk lebih efektif menjangkau audiens target.
    """
    elements.append(Paragraph(topic_analysis, normal_style))
    
    # Hashtag Populer
    elements.append(Paragraph("3.2 Hashtag Populer", heading2_style))
    
    hashtag_intro = f"""
    Berikut adalah hashtag yang paling sering digunakan dalam percakapan terkait 
    "{analysis_context['title']}":
    """
    elements.append(Paragraph(hashtag_intro, normal_style))
    
    # Get hashtags from analysis context
    top_hashtags = []
    if 'top_hashtags' in analysis_context:
        top_hashtags = analysis_context['top_hashtags'][:8] if analysis_context['top_hashtags'] else []
    
    if top_hashtags:
        # Format hashtag list with bullet points
        hashtags_list = ""
        for i, hashtag in enumerate(top_hashtags, 1):
            hashtag_tag = hashtag if isinstance(hashtag, str) else 'Unknown'
            hashtags_list += f"<b>{i}.</b> {hashtag_tag}<br/>"
        
        # Display hashtags in a box
        elements.append(Paragraph(hashtags_list, 
            ParagraphStyle('BoxedHashtags', 
                          parent=normal_style,
                          backColor=light_color,
                          borderColor=secondary_color,
                          borderWidth=1,
                          borderPadding=10,
                          spaceBefore=10,
                          spaceAfter=10)))
    else:
        elements.append(Paragraph("Data hashtag populer tidak tersedia.", normal_style))
    
    # Hashtag Analysis
    hashtag_analysis = f"""
    <b>Analisis Hashtag:</b><br/><br/>
    Hashtag yang populer memberikan gambaran tentang bagaimana percakapan dikategorikan dan
    diorganisir di media sosial. Hashtag ini juga dapat digunakan untuk melacak percakapan
    terkait dan meningkatkan jangkauan komunikasi.
    """
    elements.append(Paragraph(hashtag_analysis, normal_style))
    elements.append(PageBreak())
    
    # ============= SAMPEL TWEET =============
    elements.append(Paragraph("4. SAMPEL TWEET", heading1_style))
    horizontal_line()
    
    # Helper function untuk memotong teks yang terlalu panjang
    def truncate_text(text, max_length=100):
        if text and len(text) > max_length:
            return text[:max_length] + "..."
        return text if text else ""
    
    # Fungsi untuk menambahkan sampel tweet dengan styling yang lebih baik
    def add_tweet_samples(section_num, category, sentiment_type, color):
        elements.append(Paragraph(f"4.{section_num} Tweet {category}", heading2_style))
        elements.append(Paragraph(f"Berikut adalah sampel tweet dengan sentimen {category.lower()}:", normal_style))
        
        # Filter tweets by sentiment
        tweets = analysis_df[analysis_df['predicted_sentiment'] == sentiment_type].head(3)
        
        if len(tweets) > 0:
            for i, (_, tweet) in enumerate(tweets.iterrows(), 1):
                username = tweet.get('username', 'user')
                content = truncate_text(tweet.get('content', ''), 150)
                confidence = f"{tweet.get('confidence', 0):.1f}%"
                date = tweet.get('date', datetime.now().strftime('%d %b %Y'))
                
                # Format tweet
                tweet_text = f"""
                <font color="blue"><b>@{username}</b></font> • {date}<br/>
                {content}<br/>
                <font color="gray"><i>Confidence: {confidence}</i></font>
                """
                
                # Custom tweet style with background color
                tweet_style = ParagraphStyle(
                    f'Tweet{sentiment_type}{i}',
                    parent=normal_style,
                    backColor=light_color,
                    borderColor=color,
                    borderWidth=1,
                    borderPadding=8,
                    spaceBefore=10,
                    spaceAfter=10
                )
                
                elements.append(Paragraph(tweet_text, tweet_style))
        else:
            elements.append(Paragraph(f"Tidak ada tweet {category.lower()} yang tersedia.", normal_style))
        
        # Add analysis for each sentiment type
        analysis_text = {
            "Positif": """
            <b>Karakteristik Tweet Positif:</b><br/>
            Tweet positif umumnya mengandung ekspresi dukungan, apresiasi, atau optimisme. 
            Kata-kata yang sering muncul antara lain: "bagus", "sukses", "terima kasih", 
            "mendukung", "setuju", dll.<br/><br/>
            """,
            
            "Netral": """
            <b>Karakteristik Tweet Netral:</b><br/>
            Tweet netral umumnya bersifat informatif, faktual, atau berupa pertanyaan. 
            Tweet ini tidak menunjukkan emosi atau pendapat yang kuat, baik positif maupun negatif.<br/><br/>
            """,
            
            "Negatif": """
            <b>Karakteristik Tweet Negatif:</b><br/>
            Tweet negatif umumnya mengandung ekspresi kritik, kekecewaan, atau kekhawatiran. 
            Kata-kata yang sering muncul antara lain: "kecewa", "masalah", "buruk", "gagal", 
            "tidak setuju", dll.<br/><br/>
            """
        }
        
        elements.append(Paragraph(analysis_text[sentiment_type], normal_style))
        elements.append(Spacer(1, 0.2*inch))
    
    # Tambahkan sampel tweet untuk setiap sentimen
    add_tweet_samples(1, "Positif", "Positif", colors.green)
    add_tweet_samples(2, "Netral", "Netral", colors.blue)
    add_tweet_samples(3, "Negatif", "Negatif", colors.red)
    
    elements.append(PageBreak())
    
    # ============= KESIMPULAN DAN REKOMENDASI =============
    elements.append(Paragraph("5. KESIMPULAN DAN REKOMENDASI", heading1_style))
    horizontal_line()
    
    # Kesimpulan
    elements.append(Paragraph("5.1 Kesimpulan", heading2_style))
    
    # Get top topics and hashtags for conclusion
    top_topics_text = "beragam topik"
    if 'top_topics' in analysis_context and analysis_context['top_topics']:
        top_topics_text = ", ".join(analysis_context['top_topics'][:3])
    
    top_hashtags_text = "beragam hashtag"
    if 'top_hashtags' in analysis_context and analysis_context['top_hashtags']:
        top_hashtags_text = ", ".join(analysis_context['top_hashtags'][:3])
    
    conclusion_text = f"""
    Berdasarkan analisis sentimen terhadap {analysis_context['total_tweets']} tweets terkait 
    "{analysis_context['title']}", dapat disimpulkan bahwa:<br/><br/>
    
    1. Sentimen publik secara keseluruhan cenderung {'positif' if dominant == 'Positif' else
       'netral' if dominant == 'Netral' else 'negatif'} dengan persentase {pos_percent if dominant == 'Positif' 
       else neu_percent if dominant == 'Netral' else neg_percent}%.<br/><br/>
    
    2. Topik-topik utama yang dibicarakan adalah seputar {top_topics_text}.<br/><br/>
    
    3. Hashtag yang paling sering digunakan adalah {top_hashtags_text}.<br/><br/>
    
    4. Percakapan di media sosial X menunjukkan {'tingkat dukungan dan antusiasme yang baik' 
       if dominant == 'Positif' else 'sikap yang cenderung netral dan informatif' 
       if dominant == 'Netral' else 'adanya kekhawatiran dan kritik'} terhadap topik ini.<br/><br/>
    """
    
    elements.append(Paragraph(conclusion_text, normal_style))
    
    # Rekomendasi berdasarkan sentimen dominan
    elements.append(Paragraph("5.2 Rekomendasi", heading2_style))
    
    recommendation_text = {
        "Positif": f"""
        Berdasarkan dominasi sentimen positif, berikut adalah rekomendasi untuk mempertahankan
        dan meningkatkan persepsi positif publik:<br/><br/>
        
        1. <b>Pertahankan Momentum Positif</b> - Teruskan komunikasi aspek-aspek yang mendapatkan
           respon positif dari publik.<br/><br/>
        
        2. <b>Manfaatkan Pendukung</b> - Identifikasi dan libatkan pendukung aktif untuk
           memperluas jangkauan pesan positif.<br/><br/>
        
        3. <b>Gunakan Hashtag Populer</b> - Manfaatkan hashtag {top_hashtags_text}
           untuk meningkatkan visibilitas pesan.<br/><br/>
        
        4. <b>Eksplorasi Topik Potensial</b> - Kembangkan konten seputar {top_topics_text}
           yang mendapat respons positif.<br/><br/>
        
        5. <b>Pantau Secara Berkala</b> - Lakukan analisis sentimen secara berkala untuk
           mendeteksi perubahan tren dan menyesuaikan strategi.<br/><br/>
        """,
        
        "Netral": f"""
        Berdasarkan dominasi sentimen netral, berikut adalah rekomendasi untuk meningkatkan
        sentimen ke arah yang lebih positif:<br/><br/>
        
        1. <b>Tingkatkan Komunikasi Nilai</b> - Perkuat pesan tentang manfaat dan nilai positif
           untuk menggeser sentimen dari netral ke positif.<br/><br/>
        
        2. <b>Edukasi Publik</b> - Lakukan edukasi yang lebih intensif tentang aspek-aspek
           penting yang mungkin belum dipahami sepenuhnya.<br/><br/>
        
        3. <b>Ciptakan Konten Engaging</b> - Kembangkan konten yang lebih menarik dan memicu
           respons emosional positif.<br/><br/>
        
        4. <b>Gunakan Influencer</b> - Libatkan influencer untuk memperkuat pesan dan menciptakan
           sentimen yang lebih positif.<br/><br/>
        
        5. <b>Pantau Tren Pergeseran</b> - Perhatikan percakapan netral yang berpotensi
           bergeser ke arah positif atau negatif.<br/><br/>
        """,
        
        "Negatif": f"""
        Berdasarkan dominasi sentimen negatif, berikut adalah rekomendasi untuk memperbaiki
        persepsi publik:<br/><br/>
        
        1. <b>Identifikasi Masalah Utama</b> - Lakukan analisis mendalam terhadap sumber
           kekhawatiran dan kritik utama.<br/><br/>
        
        2. <b>Berikan Klarifikasi</b> - Komunikasikan klarifikasi untuk isu-isu yang sering
           mendapat kritik.<br/><br/>
        
        3. <b>Tunjukkan Langkah Perbaikan</b> - Informasikan tentang langkah-langkah konkret
           yang sedang atau akan dilakukan untuk mengatasi masalah.<br/><br/>
        
        4. <b>Engagement Aktif</b> - Tingkatkan keterlibatan dengan audiens kritis untuk
           menunjukkan keterbukaan terhadap umpan balik.<br/><br/>
        
        5. <b>Pemantauan Intensif</b> - Lakukan pemantauan lebih sering untuk melihat
           perubahan sentimen setelah implementasi rekomendasi.<br/><br/>
        """
    }
    
    elements.append(Paragraph(recommendation_text[dominant], normal_style))
    
    # Metodologi
    elements.append(Paragraph("5.3 Metodologi Analisis", heading2_style))
    
    methodology_text = f"""
    Analisis sentimen dalam laporan ini menggunakan model machine learning berbasis IndoBERT
    yang dilatih khusus untuk mengklasifikasikan teks Bahasa Indonesia ke dalam tiga kategori
    sentimen: Positif, Netral, dan Negatif.<br/><br/>
    
    Model ini memiliki akurasi sekitar 85% berdasarkan validasi pada dataset pengujian. Persentase
    kepercayaan (confidence score) ditampilkan untuk setiap sampel tweet sebagai indikasi
    tingkat keyakinan model terhadap prediksi yang dihasilkan.<br/><br/>
    
    Data tweets diambil dari platform X (Twitter) menggunakan Scraping data dengan filter
    berdasarkan kata kunci yang relevan dengan topik "{analysis_context['title']}".<br/><br/>
    """
    
    elements.append(Paragraph(methodology_text, normal_style))
    
    # Footer
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph(
        f"Laporan ini dibuat secara otomatis oleh Aplikasi Analisis Sentimen X • {datetime.now().strftime('%d %B %Y')}",
        ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            alignment=1,  # Center
            textColor=colors.gray
        )
    ))
    
    # Build PDF with page numbers
    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)
    buffer.seek(0)
    
    # Return file
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Laporan_Analisis_Sentimen_{analysis_context['title'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
        mimetype='application/pdf'
    )