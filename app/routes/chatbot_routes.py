from flask import Blueprint, request, jsonify, session
from app.services.chatbot import query_gemini

chatbot_bp = Blueprint('chatbot', __name__)

@chatbot_bp.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.json
    message = data.get('message', '')
    
    # Get the analysis context from session
    analysis_context = session.get('analysis_context')
    
    # Send message to Gemini and get response
    response = query_gemini(message, analysis_context)
    
    return jsonify({'response': response})