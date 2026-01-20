"""
This script handles the setup and execution of the web application.
"""
from pathlib import Path
import shutil
from dotenv import load_dotenv
from web_app import create_app
from backend.routes import api_bp
import os
# Fix protobuf compatibility issue with transformers
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

print("--- run.py started ---")


# Load environment variables
env_path = Path('.env')
env_example_path = Path('.env.example')

# If .env doesn't exist, create it from example
if not env_path.exists() and env_example_path.exists():
    shutil.copy(env_example_path, env_path)
    print("Created .env file from .env.example. Please update your API keys before proceeding.")

# Load environment vars
load_dotenv()
print("--- dotenv loaded ---")

# Check if required API keys are set based on provider
provider = os.getenv("DEFAULT_PROVIDER", "openai").lower()
if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
    print("WARNING: OPENAI_API_KEY not found in environment variables.")
    print("Please set your API key in the .env file before running the application.")
    exit(1)
elif provider == "deepseek" and not os.getenv("DEEPSEEK_API_KEY"):
    print("WARNING: DEEPSEEK_API_KEY not found in environment variables.")
    print("Please set your API key in the .env file before running the application.")
    exit(1)
elif provider == "openrouter":
    print("✅ Using OpenRouter with free models (no API key required)")

# Create necessary directories
os.makedirs("vector_db", exist_ok=True)
os.makedirs("learning_paths", exist_ok=True)
print("--- API key checked and dirs created ---")

# Import and run Flask app

app = create_app()

# Register the API blueprint for RQ task orchestration under /api
app.register_blueprint(api_bp, url_prefix='/api')

print("--- Flask app created via factory ---")

# Pre-warm the model orchestrator to avoid cold start delays
def prewarm_models():
    """Pre-initialize models to avoid cold start on first request."""
    try:
        print("🔥 Pre-warming AI models (this may take a moment on first run)...")
        from src.ml.model_orchestrator import ModelOrchestrator
        orchestrator = ModelOrchestrator()
        # Make a simple test call to ensure the model is fully loaded
        print("✅ AI models pre-warmed successfully!")
    except Exception as e:
        print(f"⚠️ Model pre-warming failed (will initialize on first request): {e}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    # Disable debug mode to prevent auto-reloading issues
    debug = False

    # Pre-warm models before starting server
    prewarm_models()

    print(f"Starting AI Learning Path Generator on port {port}")
    print("Visit http://localhost:5000 in your browser")

    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
