"""
API Routes for task management
"""
import os
import uuid
import json
from flask import Blueprint, request, jsonify
from datetime import datetime

api_bp = Blueprint('rq_api', __name__)

# Redis connection - optional for local development
# Note: decode_responses=False is required for RQ (job results are pickled bytes, not strings)
redis_client = None
REDIS_URL = os.getenv('REDIS_URL')


def get_redis_client():
    """Lazy load Redis client to avoid errors if Redis is not available"""
    global redis_client
    if redis_client is not None:
        return redis_client

    try:
        import redis
        if REDIS_URL and REDIS_URL.startswith(('redis://', 'rediss://')):
            if REDIS_URL.startswith('rediss://'):
                redis_client = redis.from_url(
                    REDIS_URL, decode_responses=False, ssl_cert_reqs=None)
            else:
                redis_client = redis.from_url(
                    REDIS_URL, decode_responses=False)
        else:
            redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                db=int(os.getenv('REDIS_DB', 0)),
                decode_responses=False
            )
        # Test connection
        redis_client.ping()
        return redis_client
    except Exception as e:
        print(f"Redis not available: {e}")
        redis_client = None
        return None


# In-memory storage for synchronous task results (for local dev without Redis)
sync_task_results = {}


@api_bp.route('/generate', methods=['POST'])
def generate_path():
    """
    Generate a learning path. Uses RQ queue if Redis is available,
    otherwise runs synchronously for local development.
    Returns the job ID immediately (async) or result directly (sync).
    """
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['topic', 'expertise_level',
                           'duration_weeks', 'time_commitment']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Try to use Redis/RQ for async processing
        redis_conn = get_redis_client()
        if redis_conn:
            try:
                from rq import Queue
                q = Queue('learning-paths', connection=redis_conn)
                job = q.enqueue(
                    'worker.tasks.generate_learning_path_for_worker', data)

                return jsonify({
                    "task_id": job.id,
                    "status": "queued",
                    "message": "Learning path generation started"
                }), 202
            except Exception as rq_error:
                print(f"RQ error, falling back to sync: {rq_error}")

        # Fallback: Run synchronously for local development
        task_id = str(uuid.uuid4())
        sync_task_results[task_id] = {"status": "processing"}

        try:
            # Import and run the generation function directly
            from src.learning_path import LearningPathGenerator

            generator = LearningPathGenerator()

            # Normalize goals
            goals_raw = data.get('goals')
            if isinstance(goals_raw, list):
                goals = goals_raw
            elif isinstance(goals_raw, str) and goals_raw.strip():
                goals = [goals_raw.strip()]
            else:
                goals = None

            learning_path = generator.generate_path(
                topic=data['topic'],
                expertise_level=data['expertise_level'],
                learning_style=None,
                time_commitment=data.get('time_commitment', '5-10 hours/week'),
                duration_weeks=int(data['duration_weeks']),
                goals=goals,
                ai_provider=data.get('ai_provider', 'openrouter'),
                ai_model=data.get('ai_model')
            )

            result = learning_path.dict() if hasattr(
                learning_path, 'dict') else learning_path

            sync_task_results[task_id] = {
                "status": "finished",
                "result": result
            }

            return jsonify({
                "task_id": task_id,
                "status": "finished",
                "message": "Learning path generated successfully",
                "result": result
            }), 200

        except Exception as gen_error:
            sync_task_results[task_id] = {
                "status": "failed",
                "error": str(gen_error)
            }
            return jsonify({
                "task_id": task_id,
                "status": "failed",
                "error": str(gen_error)
            }), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/status/<task_id>', methods=['GET'])
def get_status(task_id):
    """
    Get the current status of a task (RQ job or sync task)
    """
    try:
        # Check sync task results first
        if task_id in sync_task_results:
            task = sync_task_results[task_id]
            resp = {
                "task_id": task_id,
                "status": task["status"]
            }
            if task["status"] == "finished":
                resp["result"] = task.get("result")
            if task["status"] == "failed":
                resp["error"] = task.get("error")
            return jsonify(resp), 200

        # Try Redis/RQ
        redis_conn = get_redis_client()
        if redis_conn:
            from rq import Queue
            q = Queue('learning-paths', connection=redis_conn)
            job = q.fetch_job(task_id)
            if job is None:
                return jsonify({"error": "Task not found"}), 404

            resp = {
                "task_id": job.id,
                "status": job.get_status()
            }
            if job.is_finished:
                resp["result"] = job.result
            if job.is_failed:
                resp["error"] = str(job.exc_info)
            return jsonify(resp), 200

        return jsonify({"error": "Task not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/result/<task_id>', methods=['GET'])
def get_result(task_id):
    """
    Get the final result of a task (RQ job or sync task)
    """
    try:
        # Check sync task results first
        if task_id in sync_task_results:
            task = sync_task_results[task_id]
            if task["status"] == "finished":
                return jsonify(task.get("result", {})), 200
            elif task["status"] == "failed":
                return jsonify({"error": task.get("error")}), 500
            else:
                return jsonify({
                    "error": "Task not yet complete",
                    "status": task["status"]
                }), 202

        # Try Redis/RQ
        redis_conn = get_redis_client()
        if redis_conn:
            from rq import Queue
            q = Queue('learning-paths', connection=redis_conn)
            job = q.fetch_job(task_id)
            if job is None:
                return jsonify({"error": "Task not found"}), 404

            if not job.is_finished:
                return jsonify({
                    "error": "Task not yet complete",
                    "status": job.get_status()
                }), 202

            return jsonify(job.result), 200

        return jsonify({"error": "Task not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
