"""
API endpoints for skill assessment functionality.
Generates MCQ questions based on learning path content and tracks results.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from web_app.models import db, UserLearningPath
from datetime import datetime
import json
import random

assessment_bp = Blueprint('assessment', __name__, url_prefix='/api/assessment')


@assessment_bp.route('/generate', methods=['POST'])
def generate_questions():
    """
    Generate MCQ questions for skill assessment.

    Expects JSON: {
        topic: string,
        expertise_level: string,
        milestones: string[],
        skills: string[],
        num_questions: number (default: 25)
    }

    Returns: { questions: [...] }
    """
    try:
        data = request.get_json() or {}
        topic = data.get('topic', 'General')
        expertise_level = data.get('expertise_level', 'beginner').lower()
        milestones = data.get('milestones', [])
        skills = data.get('skills', [])
        num_questions = min(data.get('num_questions', 25), 50)  # Cap at 50

        # Try AI generation first, fall back to template-based
        try:
            questions = generate_ai_questions(
                topic=topic,
                expertise_level=expertise_level,
                milestones=milestones,
                skills=skills,
                num_questions=num_questions
            )
        except Exception as e:
            current_app.logger.warning(
                f"AI question generation failed: {e}, using fallback")
            questions = generate_template_questions(
                topic=topic,
                expertise_level=expertise_level,
                milestones=milestones,
                skills=skills,
                num_questions=num_questions
            )

        return jsonify({'questions': questions}), 200

    except Exception as e:
        current_app.logger.error(f"Error generating questions: {str(e)}")
        return jsonify({
            'error': 'Failed to generate questions',
            'questions': generate_template_questions(
                topic=data.get('topic', 'General'),
                expertise_level='beginner',
                milestones=[],
                skills=[],
                num_questions=25
            )
        }), 200  # Return 200 with fallback questions


@assessment_bp.route('/result', methods=['POST'])
@login_required
def save_result():
    """
    Save assessment result.

    Expects JSON: {
        path_id: string,
        score: number,
        correct_answers: number,
        total_questions: number,
        answers: object (optional)
    }

    Returns: { success: boolean, result_id: string }
    """
    try:
        data = request.get_json() or {}
        path_id = data.get('path_id')
        score = data.get('score', 0)
        correct_answers = data.get('correct_answers', 0)
        total_questions = data.get('total_questions', 25)

        if not path_id:
            return jsonify({'success': False, 'error': 'path_id is required'}), 400

        # Verify the path belongs to the user
        user_path = UserLearningPath.query.filter_by(
            id=path_id,
            user_id=current_user.id
        ).first()

        if not user_path:
            return jsonify({'success': False, 'error': 'Learning path not found'}), 404

        # Store assessment result in path_data_json
        path_data = user_path.path_data_json or {}

        if 'assessment_results' not in path_data:
            path_data['assessment_results'] = []

        result = {
            'id': f"assess_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            'score': score,
            'correct_answers': correct_answers,
            'total_questions': total_questions,
            'percentage': round((correct_answers / total_questions) * 100, 1) if total_questions > 0 else 0,
            'passed': score >= 70,
            'completed_at': datetime.utcnow().isoformat()
        }

        path_data['assessment_results'].append(result)
        user_path.path_data_json = path_data

        db.session.commit()

        return jsonify({
            'success': True,
            'result_id': result['id'],
            'passed': result['passed']
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error saving assessment result: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to save result'}), 500


@assessment_bp.route('/history/<path_id>', methods=['GET'])
@login_required
def get_history(path_id):
    """
    Get assessment history for a learning path.

    Returns: { attempts: [...] }
    """
    try:
        user_path = UserLearningPath.query.filter_by(
            id=path_id,
            user_id=current_user.id
        ).first()

        if not user_path:
            return jsonify({'attempts': [], 'error': 'Learning path not found'}), 404

        path_data = user_path.path_data_json or {}
        attempts = path_data.get('assessment_results', [])

        return jsonify({'attempts': attempts}), 200

    except Exception as e:
        current_app.logger.error(f"Error getting assessment history: {str(e)}")
        return jsonify({'attempts': [], 'error': str(e)}), 500


def generate_ai_questions(topic, expertise_level, milestones, skills, num_questions):
    """
    Generate questions using AI model.
    """
    from src.ml.model_orchestrator import ModelOrchestrator

    orchestrator = ModelOrchestrator()
    orchestrator.init_language_model()

    # Build context from milestones and skills
    context_items = skills if skills else milestones
    context_str = ", ".join(context_items[:10]) if context_items else topic

    prompt = f"""Generate exactly {num_questions} multiple choice questions to assess knowledge of {topic} at the {expertise_level} level.

Topics to cover: {context_str}

Requirements:
1. Each question should have exactly 4 options (A, B, C, D)
2. Questions should progress from easier to harder
3. Include a mix of conceptual, practical, and scenario-based questions
4. Each question must have exactly one correct answer

Return ONLY valid JSON in this exact format (no markdown, no explanation):
{{
  "questions": [
    {{
      "id": 1,
      "question": "Question text here?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correctAnswer": 0,
      "topic": "Specific topic",
      "difficulty": "{expertise_level}"
    }}
  ]
}}

The correctAnswer is the 0-based index of the correct option.
Generate all {num_questions} questions now:"""

    try:
        response = orchestrator.generate_response(
            prompt=prompt,
            use_cache=False,
            temperature=0.7
        )

        # Clean up response - remove markdown code blocks if present
        response = response.strip()
        if response.startswith('```'):
            # Remove markdown code fence
            lines = response.split('\n')
            response = '\n'.join(
                lines[1:-1] if lines[-1].startswith('```') else lines[1:])

        # Parse JSON
        data = json.loads(response)
        questions = data.get('questions', [])

        # Validate and fix questions
        valid_questions = []
        for i, q in enumerate(questions):
            if all(key in q for key in ['question', 'options', 'correctAnswer']):
                q['id'] = i + 1
                q['topic'] = q.get('topic', topic)
                q['difficulty'] = q.get('difficulty', expertise_level)
                # Ensure correctAnswer is valid index
                if isinstance(q['correctAnswer'], int) and 0 <= q['correctAnswer'] < len(q['options']):
                    valid_questions.append(q)

        if len(valid_questions) >= num_questions * 0.5:  # Accept if at least 50% valid
            return valid_questions[:num_questions]
        else:
            raise ValueError("Not enough valid questions generated")

    except Exception as e:
        current_app.logger.error(f"AI question generation error: {e}")
        raise


def generate_template_questions(topic, expertise_level, milestones, skills, num_questions):
    """
    Generate questions using templates when AI is unavailable.
    Returns diverse, topic-relevant MCQ questions.
    """
    questions = []
    all_concepts = skills if skills else (
        milestones if milestones else [topic])

    # Ensure we have enough concepts to work with
    if len(all_concepts) < 5:
        all_concepts = all_concepts + [topic] * (5 - len(all_concepts))

    # Question templates based on expertise level
    templates = {
        'beginner': [
            ("What is the primary purpose of {concept}?", "definition"),
            ("Which of the following best describes {concept}?",
             "description"),
            ("What is the first step when learning {concept}?", "process"),
            ("Which tool is commonly used for {concept}?", "tool"),
            ("What does {concept} help you achieve?", "benefit"),
            ("Why is {concept} important in this field?", "importance"),
            ("What is a basic example of {concept}?", "example"),
        ],
        'intermediate': [
            ("How does {concept} differ from similar approaches?", "comparison"),
            ("What is a common challenge when implementing {concept}?", "challenge"),
            ("Which best practice should be followed with {concept}?", "practice"),
            ("In what scenario would you use {concept}?", "application"),
            ("What is the relationship between {concept} and related techniques?", "relationship"),
            ("How can you optimize the use of {concept}?", "optimization"),
            ("What are common mistakes when working with {concept}?", "mistakes"),
        ],
        'advanced': [
            ("What is an advanced optimization technique for {concept}?", "advanced_opt"),
            ("How would you troubleshoot complex issues with {concept}?", "debugging"),
            ("What architectural consideration is important for {concept}?", "architecture"),
            ("How does {concept} scale in production environments?", "scaling"),
            ("What security considerations apply to {concept}?", "security"),
            ("How would you integrate {concept} with other systems?",
             "integration"),
            ("What are the trade-offs when using {concept}?", "tradeoffs"),
        ]
    }

    # Get templates for the expertise level
    level_templates = templates.get(expertise_level, templates['beginner'])

    # Option generators for different question types
    def get_options(concept, q_type):
        option_sets = {
            "definition": [
                f"A fundamental technique that enables efficient application of {concept}",
                f"A deprecated method no longer used in modern {concept}",
                f"An unrelated concept from a different field entirely",
                f"A theoretical framework without practical application",
            ],
            "description": [
                f"It provides a structured approach to understanding and applying {concept} effectively",
                f"It is only useful for advanced practitioners with years of experience",
                f"It has been completely replaced by newer methodologies",
                f"It requires specialized hardware that most developers don't have access to",
            ],
            "process": [
                "Understanding the core fundamentals and basic principles first",
                "Jumping directly to advanced topics without any foundation",
                "Memorizing all possible variations before practicing",
                "Avoiding any practical exercises until mastering theory",
            ],
            "tool": [
                f"Industry-standard tools specifically designed for {concept}",
                "Generic text editors without any specialized features",
                "Outdated software from decades ago",
                "Tools designed for completely different purposes",
            ],
            "benefit": [
                "Improved efficiency, better outcomes, and deeper understanding of the domain",
                "No measurable benefits have been documented by researchers",
                "Benefits only apply to large enterprise organizations",
                "The benefits are purely theoretical with no practical value",
            ],
            "importance": [
                f"{concept} is essential for building robust and maintainable solutions",
                f"{concept} is optional and rarely used in professional settings",
                f"{concept} was important historically but is now obsolete",
                f"{concept} only matters for academic research, not real applications",
            ],
            "example": [
                f"Using {concept} to solve common real-world problems efficiently",
                f"A complex edge case that rarely occurs in practice",
                f"An incorrect application that would cause errors",
                f"A fictional scenario that doesn't apply to {concept}",
            ],
            "comparison": [
                f"It offers unique advantages while sharing some principles with alternatives",
                "There are absolutely no differences between any approaches",
                "It is universally inferior to all other alternatives available",
                "Comparisons cannot be made between different approaches",
            ],
            "challenge": [
                "Managing complexity while maintaining code quality and performance",
                "There are no known challenges or difficulties whatsoever",
                "It only works on specific operating systems from the 1990s",
                "Documentation is the only challenge, nothing technical",
            ],
            "practice": [
                "Following established patterns and continuously refactoring for improvement",
                "Avoiding all standard conventions used by the community",
                "Writing as little documentation as possible to save time",
                "Ignoring all community guidelines and best practices",
            ],
            "application": [
                "When dealing with complex problems that require structured, scalable solutions",
                "Only in academic research settings with no commercial value",
                "Never in production environments under any circumstances",
                "Exclusively for small personal hobby projects",
            ],
            "relationship": [
                "They complement each other and can be combined for better results",
                "They are mutually exclusive and can never be used together",
                "There is absolutely no relationship between them at all",
                "One completely replaces the other in all scenarios",
            ],
            "optimization": [
                "Implementing caching, parallel processing, and efficient algorithms",
                "Simply adding more hardware without any code changes",
                "Removing all error handling to improve speed",
                "Using deprecated methods that were faster in old versions",
            ],
            "advanced_opt": [
                "Using profiling tools to identify bottlenecks and optimize critical paths",
                "Randomly changing code until performance improves by chance",
                "Removing all validation and security checks",
                "Rewriting everything in assembly language",
            ],
            "debugging": [
                "Using systematic logging, profiling tools, and step-by-step analysis",
                "Randomly changing code until errors disappear",
                "Ignoring error messages and hoping problems resolve",
                "Rewriting the entire system from scratch every time",
            ],
            "architecture": [
                "Designing for scalability, maintainability, and separation of concerns",
                "Putting all code in a single massive file",
                "Avoiding any design patterns or architectural principles",
                "Ignoring all performance and scalability implications",
            ],
            "scaling": [
                "Through horizontal scaling, load balancing, and efficient resource management",
                "Scaling is fundamentally impossible with this approach",
                "Only vertical scaling with bigger, more expensive servers",
                "By significantly reducing functionality and features",
            ],
            "security": [
                "Input validation, encryption, authentication, and following security best practices",
                "Security is not a concern for modern applications",
                "Only network firewalls are needed, nothing else",
                "Obscuring code is sufficient protection against all threats",
            ],
            "integration": [
                "Using well-defined APIs, standard protocols, and proper abstraction layers",
                "Direct database access from all external systems",
                "Copy-pasting code between different systems manually",
                "Integration is impossible with this technology",
            ],
            "tradeoffs": [
                "Balancing performance, maintainability, complexity, and development time",
                "There are no trade-offs; this approach is perfect in every way",
                "The only trade-off is that it costs money to use",
                "Trade-offs only matter for legacy systems, not modern ones",
            ],
            "mistakes": [
                "Not following best practices, ignoring documentation, and skipping testing",
                "Following the official documentation too closely",
                "Writing too many unit tests for the codebase",
                "Using the recommended tools and frameworks",
            ],
        }

        return option_sets.get(q_type, option_sets["definition"])

    # Generate questions
    for i in range(num_questions):
        concept = all_concepts[i % len(all_concepts)]
        template, q_type = level_templates[i % len(level_templates)]

        question_text = template.replace("{concept}", concept)
        options = get_options(concept, q_type)

        # Shuffle options but track correct answer
        correct_option = options[0]  # First option is always correct
        shuffled_options = options.copy()
        random.shuffle(shuffled_options)
        correct_index = shuffled_options.index(correct_option)

        questions.append({
            "id": i + 1,
            "question": question_text,
            "options": shuffled_options,
            "correctAnswer": correct_index,
            "topic": concept,
            "difficulty": expertise_level
        })

    return questions
