"""
API endpoints for chat and milestone tracking functionality.
Supports both session-based auth (web) and JWT token auth (mobile).
"""
from flask import Blueprint, request, jsonify, current_app, g
from flask_login import login_required, current_user
from web_app.models import db, User, UserLearningPath, MilestoneProgress, LearningProgress
from src.data.document_store import DocumentStore
from datetime import datetime
from functools import wraps
import jwt

api_bp = Blueprint('api', __name__, url_prefix='/api')


def get_current_user_from_token():
    """Extract user from JWT token in Authorization header"""
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(
                token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload.get('user_id')
            if user_id:
                return User.query.get(user_id)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            pass
    return None


def api_auth_required(f):
    """
    Decorator that supports both session-based and JWT token authentication.
    For mobile apps using JWT tokens and web apps using session cookies.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        user = None

        # First try JWT token auth (for mobile)
        user = get_current_user_from_token()

        # If no token, fall back to session auth (for web)
        if not user and current_user.is_authenticated:
            user = current_user

        if not user:
            return jsonify({'error': 'Authentication required'}), 401

        # Store user in g for access in the route
        g.current_user = user
        return f(*args, **kwargs)

    return decorated


@api_bp.route('/save-path', methods=['POST'])
@api_auth_required
def save_path_json():
    """
    Save or update a learning path for the current user.
    Expects JSON: { path: <LearningPath dict> }
    Returns: { success, path_id }
    """
    try:
        payload = request.get_json(silent=True) or {}
        path_data = payload.get('path') or {}
        if not path_data or not isinstance(path_data, dict):
            return jsonify({'success': False, 'message': 'Invalid payload'}), 400

        path_id = path_data.get('id')
        if not path_id:
            import uuid as _uuid
            path_id = str(_uuid.uuid4())
            path_data['id'] = path_id

        # Upsert user path
        user_path = UserLearningPath.query.filter_by(
            id=path_id,
            user_id=g.current_user.id
        ).first()

        if user_path:
            user_path.path_data_json = path_data
            user_path.title = path_data.get('title', 'Untitled Path')
            user_path.topic = path_data.get('topic', 'General')
        else:
            user_path = UserLearningPath(
                id=path_id,
                user_id=g.current_user.id,
                path_data_json=path_data,
                title=path_data.get('title', 'Untitled Path'),
                topic=path_data.get('topic', 'General')
            )
            db.session.add(user_path)

        db.session.commit()

        # Ensure progress rows exist
        try:
            milestones = path_data.get('milestones', [])
            for i, _ in enumerate(milestones):
                exists = LearningProgress.query.filter_by(
                    user_learning_path_id=path_id,
                    milestone_identifier=str(i)
                ).first()
                if not exists:
                    db.session.add(LearningProgress(
                        user_learning_path_id=path_id,
                        milestone_identifier=str(i),
                        status='not_started'
                    ))
            db.session.commit()
        except Exception as _e:
            current_app.logger.warning(
                f"Failed to seed LearningProgress rows: {_e}")
            db.session.rollback()

        return jsonify({'success': True, 'path_id': path_id}), 200
    except Exception as e:
        current_app.logger.error(f"Error saving path: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to save path'}), 500


@api_bp.route('/paths', methods=['GET'])
@api_auth_required
def get_all_paths():
    """
    Get all learning paths for the current user.
    Returns: { paths: [...] }
    """
    try:
        user_paths = UserLearningPath.query.filter_by(
            user_id=g.current_user.id).all()
        paths = []
        for up in user_paths:
            path_data = up.path_data_json or {}
            path_data['id'] = up.id
            path_data['title'] = up.title
            path_data['topic'] = up.topic
            path_data['created_at'] = up.created_at.isoformat(
            ) if up.created_at else None

            # Include milestone completion progress
            progress_entries = LearningProgress.query.filter_by(
                user_learning_path_id=up.id
            ).all()
            completed_milestones = {}
            for progress in progress_entries:
                completed_milestones[progress.milestone_identifier] = (
                    progress.status == 'completed'
                )
            path_data['completedMilestones'] = completed_milestones

            paths.append(path_data)
        return jsonify({'paths': paths}), 200
    except Exception as e:
        current_app.logger.error(f"Error getting paths: {str(e)}")
        return jsonify({'paths': [], 'error': str(e)}), 500


@api_bp.route('/paths/<path_id>', methods=['GET'])
@api_auth_required
def get_path_by_id(path_id):
    """
    Get a specific learning path by ID.
    Returns: Learning path data
    """
    try:
        user_path = UserLearningPath.query.filter_by(
            id=path_id,
            user_id=g.current_user.id
        ).first()

        if not user_path:
            return jsonify({'error': 'Learning path not found'}), 404

        path_data = user_path.path_data_json or {}
        path_data['id'] = user_path.id
        path_data['title'] = user_path.title
        path_data['topic'] = user_path.topic
        path_data['created_at'] = user_path.created_at.isoformat(
        ) if user_path.created_at else None

        # Include milestone completion progress
        progress_entries = LearningProgress.query.filter_by(
            user_learning_path_id=path_id
        ).all()
        completed_milestones = {}
        for progress in progress_entries:
            completed_milestones[progress.milestone_identifier] = (
                progress.status == 'completed'
            )
        path_data['completedMilestones'] = completed_milestones

        return jsonify(path_data), 200
    except Exception as e:
        current_app.logger.error(f"Error getting path: {str(e)}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/paths/<path_id>', methods=['DELETE'])
@api_auth_required
def delete_path(path_id):
    """
    Delete a learning path by ID.
    Returns: { success: boolean }
    """
    try:
        user_path = UserLearningPath.query.filter_by(
            id=path_id,
            user_id=g.current_user.id
        ).first()

        if not user_path:
            return jsonify({'success': False, 'error': 'Learning path not found'}), 404

        db.session.delete(user_path)
        db.session.commit()

        return jsonify({'success': True}), 200
    except Exception as e:
        current_app.logger.error(f"Error deleting path: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/paths/<path_id>/milestone', methods=['POST'])
@api_auth_required
def update_milestone_status(path_id):
    """
    Update milestone completion status for a learning path.
    Expects JSON: { milestone_index: number, completed: boolean }
    """
    try:
        data = request.get_json()
        milestone_index = data.get('milestone_index')
        completed = data.get('completed', False)

        if milestone_index is None:
            return jsonify({'success': False, 'error': 'milestone_index is required'}), 400

        user_path = UserLearningPath.query.filter_by(
            id=path_id,
            user_id=g.current_user.id
        ).first()

        if not user_path:
            return jsonify({'success': False, 'error': 'Learning path not found'}), 404

        # Find or create progress entry
        progress = LearningProgress.query.filter_by(
            user_learning_path_id=path_id,
            milestone_identifier=str(milestone_index)
        ).first()

        if not progress:
            progress = LearningProgress(
                user_learning_path_id=path_id,
                milestone_identifier=str(milestone_index),
                status='completed' if completed else 'not_started'
            )
            db.session.add(progress)
        else:
            progress.status = 'completed' if completed else 'not_started'

        db.session.commit()

        return jsonify({'success': True}), 200
    except Exception as e:
        current_app.logger.error(f"Error updating milestone: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/track-milestone', methods=['POST'])
@api_auth_required
def track_milestone():
    """
    Track milestone completion status.
    Expects JSON: {path_id, milestone_index, completed}
    """
    try:
        data = request.get_json()
        path_id = data.get('path_id')
        milestone_index = data.get('milestone_index')
        completed = data.get('completed', False)

        if not path_id or milestone_index is None:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        # Verify the path belongs to the user
        user_path = UserLearningPath.query.filter_by(
            id=path_id,
            user_id=g.current_user.id
        ).first()

        if not user_path:
            return jsonify({'success': False, 'message': 'Learning path not found or access denied'}), 404

        # Find or create milestone progress entry
        progress = MilestoneProgress.query.filter_by(
            user_id=g.current_user.id,
            learning_path_id=path_id,
            milestone_index=milestone_index
        ).first()

        if not progress:
            progress = MilestoneProgress(
                user_id=g.current_user.id,
                learning_path_id=path_id,
                milestone_index=milestone_index,
                completed=completed
            )
            db.session.add(progress)
        else:
            progress.completed = completed
            progress.completed_at = datetime.utcnow() if completed else None

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Milestone status updated successfully'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error tracking milestone: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to update milestone status'}), 500


@api_bp.route('/ask', methods=['POST'])
@api_auth_required
def ask_question():
    """
    Chat endpoint for asking questions about the learning path.
    Uses advanced RAG search to provide contextual answers.
    Expects JSON: {question, path_id}
    """
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        path_id = data.get('path_id')

        if not question:
            return jsonify({
                'success': False,
                'message': 'Question cannot be empty'
            }), 400

        if not path_id:
            return jsonify({
                'success': False,
                'message': 'Path ID is required'
            }), 400

        # Verify the path belongs to the user
        user_path = UserLearningPath.query.filter_by(
            id=path_id,
            user_id=g.current_user.id
        ).first()

        if not user_path:
            return jsonify({
                'success': False,
                'message': 'Learning path not found or access denied'
            }), 404

        # Get the learning path data
        path_data = user_path.path_data_json
        topic = path_data.get('topic', 'this topic')

        # Use DocumentStore's advanced RAG search
        document_store = DocumentStore()

        # Search for relevant documents
        relevant_docs = document_store.advanced_rag_search(
            query=f"{topic}: {question}",
            collection_name="learning_resources",
            top_k=3,
            use_cache=True
        )

        # Build context from retrieved documents
        context = "\n\n".join(
            [doc.page_content for doc in relevant_docs]) if relevant_docs else ""

        # Generate answer using the model orchestrator
        from src.ml.model_orchestrator import ModelOrchestrator
        orchestrator = ModelOrchestrator()
        orchestrator.init_language_model()

        prompt = f"""You are a helpful AI tutor for a learning path about {topic}.

User's question: {question}

Context from learning resources:
{context}

Please provide a clear, concise, and helpful answer to the user's question. Focus on being educational and encouraging. If the context doesn't contain relevant information, use your general knowledge about {topic} to provide a helpful response.

Answer:"""

        answer = orchestrator.generate_response(
            prompt=prompt,
            use_cache=False,
            temperature=0.7
        )

        return jsonify({
            'success': True,
            'data': {
                'answer': answer.strip(),
                'sources_count': len(relevant_docs)
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error processing question: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing your question'
        }), 500
