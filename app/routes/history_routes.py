import os
from flask import Blueprint, render_template, redirect, session, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models.database import db, Analysis, AnalysisData
from sqlalchemy import desc
import json
import traceback

history_bp = Blueprint('history', __name__)

@history_bp.route('/history')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Get query parameter for search
    search_query = request.args.get('search', '')
    
    # Get sentiment filter
    sentiment_filter = request.args.get('sentiment', 'all')
    
    # Get sort parameter
    sort_param = request.args.get('sort', 'date-desc')
    
    # Base query
    query = Analysis.query.filter_by(user_id=current_user.id)
    
    # Apply search filter if present
    if search_query:
        query = query.filter(Analysis.title.ilike(f'%{search_query}%'))
    
    # Apply sentiment filter if not "all"
    if sentiment_filter == 'positive':
        query = query.filter(Analysis.positive_percent >= Analysis.neutral_percent, 
                             Analysis.positive_percent >= Analysis.negative_percent)
    elif sentiment_filter == 'neutral':
        query = query.filter(Analysis.neutral_percent >= Analysis.positive_percent,
                             Analysis.neutral_percent >= Analysis.negative_percent)
    elif sentiment_filter == 'negative':
        query = query.filter(Analysis.negative_percent >= Analysis.positive_percent,
                             Analysis.negative_percent >= Analysis.neutral_percent)
    
    # Apply sorting
    if sort_param == 'date-desc':
        query = query.order_by(desc(Analysis.created_at))
    elif sort_param == 'date-asc':
        query = query.order_by(Analysis.created_at)
    elif sort_param == 'tweets-desc':
        query = query.order_by(desc(Analysis.total_tweets))
    elif sort_param == 'title-asc':
        query = query.order_by(Analysis.title)
    else:
        # Default sorting by most recent
        query = query.order_by(desc(Analysis.created_at))
    
    # Paginate results
    analyses = query.paginate(page=page, per_page=per_page)
    
    return render_template('history/index.html', analyses=analyses, search_query=search_query)

@history_bp.route('/history/<int:analysis_id>')
@login_required
def view(analysis_id):
    # Get analysis by ID with error handling
    try:
        analysis = Analysis.query.get_or_404(analysis_id)
        
        # Ensure user owns this analysis
        if analysis.user_id != current_user.id:
            flash('Anda tidak memiliki izin untuk melihat analisis ini.', 'danger')
            return redirect(url_for('history.index'))
        
        # Get analysis data
        analysis_data = AnalysisData.query.filter_by(analysis_id=analysis_id).first()
        
        if not analysis_data:
            flash('Data analisis tidak ditemukan.', 'danger')
            return redirect(url_for('history.index'))
        
        # Get the full data for visualization
        data = analysis_data.get_data()
        
        # Store analysis file path in session for API endpoints
        session['analysis_file'] = analysis_data.file_path
        
        # Store analysis context in session for chatbot
        analysis_context = {
            'title': analysis.title,
            'description': analysis.description or '',
            'total_tweets': analysis.total_tweets,
            'positive_count': analysis.positive_count,
            'neutral_count': analysis.neutral_count,
            'negative_count': analysis.negative_count,
            'positive_percent': analysis.positive_percent,
            'neutral_percent': analysis.neutral_percent,
            'negative_percent': analysis.negative_percent,
            'top_hashtags': data.get('top_hashtags', [])[:5] if isinstance(data.get('top_hashtags', []), list) else [],
            'top_topics': [topic['topic'] for topic in data.get('topics', [])[:5]] if data.get('topics') else []
        }
        
        # Store in session
        session['analysis_context'] = analysis_context
        
        # Debug: Print the data to check if it's correctly loaded
        print(f"Data loaded for analysis {analysis_id}: Total tweets: {analysis.total_tweets}")
        
        return render_template('history/view.html', 
                              analysis=analysis, 
                              data=data,
                              analysis_context=analysis_context)
    except Exception as e:
        traceback.print_exc()
        flash(f'Terjadi kesalahan saat memuat analisis: {str(e)}', 'danger')
        return redirect(url_for('history.index'))

@history_bp.route('/history/<int:analysis_id>/delete', methods=['POST'])
@login_required
def delete(analysis_id):
    try:
        # Debug information
        print(f"Attempting to delete analysis ID: {analysis_id}")
        
        # Get analysis by ID
        analysis = Analysis.query.get_or_404(analysis_id)
        
        # Ensure user owns this analysis
        if analysis.user_id != current_user.id:
            flash('Anda tidak memiliki izin untuk menghapus analisis ini.', 'danger')
            return redirect(url_for('history.index'))
        
        print(f"User authorized to delete analysis: {analysis.title}")
        
        # Get analysis data
        analysis_data = AnalysisData.query.filter_by(analysis_id=analysis_id).first()
        
        # Delete the file from disk if it exists
        if analysis_data and analysis_data.file_path and os.path.exists(analysis_data.file_path):
            try:
                print(f"Deleting file: {analysis_data.file_path}")
                os.remove(analysis_data.file_path)
                print(f"File deleted successfully")
            except (OSError, IOError) as e:
                # Log error but continue with database deletion
                print(f"Error deleting file {analysis_data.file_path}: {e}")
        elif analysis_data and analysis_data.file_path:
            print(f"File not found on disk: {analysis_data.file_path}")
        
        # Delete analysis data if it exists
        if analysis_data:
            print(f"Deleting analysis data from database")
            db.session.delete(analysis_data)
        
        # Delete analysis
        print(f"Deleting analysis from database")
        db.session.delete(analysis)
        
        # Commit changes to the database
        print(f"Committing database changes")
        db.session.commit()
        print(f"Database changes committed successfully")
        
        # Clear from session if this was the current analysis
        if 'analysis_file' in session and 'analysis_context' in session:
            if session.get('analysis_context', {}).get('title') == analysis.title:
                print(f"Clearing session data for analysis")
                session.pop('analysis_file', None)
                session.pop('analysis_context', None)
                print(f"Session data cleared")
        
        flash('Analisis berhasil dihapus.', 'success')
    except Exception as e:
        # Print full traceback for debugging
        traceback.print_exc()
        
        # Rollback the transaction
        db.session.rollback()
        flash(f'Terjadi kesalahan saat menghapus analisis: {str(e)}', 'danger')
    
    return redirect(url_for('history.index'))

@history_bp.route('/history/search')
@login_required
def search():
    query = request.args.get('query', '')
    
    if not query:
        return jsonify([])
    
    # Search analyses by title
    analyses = Analysis.query.filter_by(user_id=current_user.id).filter(
        Analysis.title.ilike(f'%{query}%')
    ).order_by(desc(Analysis.created_at)).limit(10).all()
    
    # Convert to list of dicts
    result = [analysis.to_dict() for analysis in analyses]
    
    return jsonify(result)