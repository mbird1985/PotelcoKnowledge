from flask import Blueprint, request, jsonify, render_template  # Add render_template
from flask_login import login_required
from services.rag_chat import generate_rag_response

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")

@chat_bp.route('/', methods=['GET'])
@login_required
def chat_interface():
    return render_template('chat.html')

@chat_bp.route('/ask', methods=['POST'])
@login_required
def ask():
    data = request.json
    query = data.get('query')
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    response = generate_rag_response(query)
    return jsonify({'response': response})