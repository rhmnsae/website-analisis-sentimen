from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models.database import db, Analysis, AnalysisData
from sqlalchemy import desc
import json

history_bp = Blueprint('history', __name__)

@history_bp.route('/history')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Get query parameter for search
    search_query = request.args.get('search', '')
    
    if search_query:
        # Filter analyses by title containing search query
        analyses = Analysis.query.filter_by(user_id=current_user.id).filter(
            Analysis.title.ilike(f'%{search_query}%')
        ).order_by(desc(Analysis.created_at)).paginate(page=page, per_page=per_page)
    else:
        # Get all analyses for current user
        analyses = Analysis.query.filter_by(user_id=current_user.id).order_by(
            desc(Analysis.created_at)
        ).paginate(page=page, per_page=per_page)
    
    return render_template('history/index.html', analyses=analyses, search_query=search_query)

@history_bp.route('/history/<int:analysis_id>')
@login_required
def view(analysis_id):
    # Get analysis by ID
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
        'top_hashtags': data.get('top_hashtags', [])[:5],
        'top_topics': [topic['topic'] for topic in data.get('topics', [])[:5]]
    }
    
    # Store in session
    from flask import session
    session['analysis_context'] = analysis_context
    session['analysis_file'] = analysis_data.file_path
    
    return render_template('history/view.html', analysis=analysis, data=data)

@history_bp.route('/history/<int:analysis_id>/delete', methods=['POST'])
@login_required
def delete(analysis_id):
    # Get analysis by ID
    analysis = Analysis.query.get_or_404(analysis_id)
    
    # Ensure user owns this analysis
    if analysis.user_id != current_user.id:
        flash('Anda tidak memiliki izin untuk menghapus analisis ini.', 'danger')
        return redirect(url_for('history.index'))
    
    # Get analysis data
    analysis_data = AnalysisData.query.filter_by(analysis_id=analysis_id).first()
    
    # Delete analysis data if it exists
    if analysis_data:
        db.session.delete(analysis_data)
    
    # Delete analysis
    db.session.delete(analysis)
    db.session.commit()
    
    flash('Analisis berhasil dihapus.', 'success')
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