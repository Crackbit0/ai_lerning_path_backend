#!/usr/bin/env python3
"""
Test script for OpenRouter free model integration.
Run this to verify OpenRouter is working with your project.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_openrouter_config():
    """Test 1: Verify OpenRouter configuration is loaded"""
    print("=" * 60)
    print("Test 1: Verifying OpenRouter Configuration")
    print("=" * 60)
    
    from src.utils.config import OPENROUTER_API_KEY, OPENROUTER_FREE_MODEL
    
    print(f"✅ OPENROUTER_API_KEY: {OPENROUTER_API_KEY[:20]}..." if OPENROUTER_API_KEY else "❌ OPENROUTER_API_KEY not set")
    print(f"✅ OPENROUTER_FREE_MODEL: {OPENROUTER_FREE_MODEL}")
    
    return True

def test_openrouter_provider():
    """Test 2: Initialize ModelOrchestrator with OpenRouter provider"""
    print("\n" + "=" * 60)
    print("Test 2: Initializing OpenRouter Provider")
    print("=" * 60)
    
    try:
        from src.ml.model_orchestrator import ModelOrchestrator
        
        print("Creating ModelOrchestrator with OpenRouter provider...")
        orchestrator = ModelOrchestrator(provider='openrouter')
        
        print(f"✅ Provider: {orchestrator.provider}")
        print(f"✅ API Key loaded: {len(orchestrator.api_key) > 0}")
        print(f"✅ ModelOrchestrator initialized successfully")
        
        return orchestrator
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def test_openrouter_language_model(orchestrator):
    """Test 3: Initialize language model with OpenRouter"""
    print("\n" + "=" * 60)
    print("Test 3: Initializing Language Model (OpenRouter)")
    print("=" * 60)
    
    if not orchestrator:
        print("❌ Skipping: No orchestrator available")
        return False
    
    try:
        print("Initializing language model with free Mistral 7B...")
        orchestrator.init_language_model()
        
        print(f"✅ Language model initialized")
        print(f"✅ Model name: {orchestrator.model_name}")
        print(f"✅ Provider: {orchestrator.provider}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_openrouter_response(orchestrator):
    """Test 4: Generate a response using OpenRouter"""
    print("\n" + "=" * 60)
    print("Test 4: Generating Response (OpenRouter Free Model)")
    print("=" * 60)
    
    if not orchestrator:
        print("❌ Skipping: No orchestrator available")
        return False
    
    try:
        print("Generating response using OpenRouter free model...")
        prompt = "What is the best way to learn programming as a beginner?"
        
        print(f"Prompt: {prompt}\n")
        
        response = orchestrator.generate_response(
            prompt,
            use_cache=False
        )
        
        print(f"✅ Response received ({len(response)} characters):")
        print("-" * 60)
        print(response[:200] + "..." if len(response) > 200 else response)
        print("-" * 60)
        
        return True
    
    except Exception as e:
        print(f"⚠️  Note: Response generation requires OpenRouter API")
        print(f"Error details: {str(e)}")
        return False

def test_learning_path_generation():
    """Test 5: Generate learning path with OpenRouter"""
    print("\n" + "=" * 60)
    print("Test 5: Learning Path Generation (OpenRouter Free Model)")
    print("=" * 60)
    
    try:
        from src.learning_path import LearningPathGenerator
        
        print("Creating LearningPathGenerator...")
        path_gen = LearningPathGenerator(api_key=None)
        
        print("✅ LearningPathGenerator created")
        print("Generating learning path with OpenRouter provider...")
        
        path = path_gen.generate_path(
            topic="Python Programming",
            expertise_level="Beginner",
            learning_style="Visual",
            time_commitment="5-7 hours/week",
            duration_weeks=4,
            ai_provider="openrouter",
            ai_model=None  # Will use free model
        )
        
        print(f"✅ Learning path generated successfully")
        print(f"✅ Path ID: {path.id}")
        print(f"✅ Title: {path.title}")
        print(f"✅ Duration: {path.duration_weeks} weeks")
        print(f"✅ Total hours: {path.total_hours}")
        
        return True
    
    except Exception as e:
        print(f"⚠️  Note: Full learning path generation may require more setup")
        print(f"Error details: {str(e)}")
        return False

def print_summary(results):
    """Print test summary"""
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    tests = [
        ("Configuration", results.get('config', False)),
        ("Provider Init", results.get('provider', False)),
        ("Language Model Init", results.get('language_model', False)),
        ("Response Generation", results.get('response', False)),
        ("Learning Path Gen", results.get('learning_path', False)),
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<40} {status}")
    
    print("-" * 60)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! OpenRouter is ready to use!")
    elif passed >= 3:
        print("\n✅ Core functionality working! Some optional tests may have failed.")
    else:
        print("\n⚠️  Some tests failed. Check configuration and logs above.")

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("OpenRouter Free Model Integration - Test Suite")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Configuration
    try:
        results['config'] = test_openrouter_config()
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        results['config'] = False
    
    # Test 2: Provider initialization
    orchestrator = test_openrouter_provider()
    results['provider'] = orchestrator is not None
    
    # Test 3: Language model initialization
    if orchestrator:
        results['language_model'] = test_openrouter_language_model(orchestrator)
    else:
        results['language_model'] = False
    
    # Test 4: Response generation
    if orchestrator:
        results['response'] = test_openrouter_response(orchestrator)
    else:
        results['response'] = False
    
    # Test 5: Learning path generation (optional)
    results['learning_path'] = test_learning_path_generation()
    
    # Print summary
    print_summary(results)

if __name__ == "__main__":
    main()
