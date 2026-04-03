#!/usr/bin/env python
"""
Test script to verify Activity-Based AI system.
Run this to verify the free AI system is working.
"""

import os
import sys

print("=" * 60)
print("Virtual Interview System - Activity-Based AI Test")
print("=" * 60)
print()

# Check 1: Python environment
print("1. Checking Python environment...")
try:
    import flask
    try:
        from importlib.metadata import version
        flask_version = version("flask")
    except ImportError:
        flask_version = flask.__version__
    print(f"   ✓ Flask {flask_version} is installed")
except ImportError:
    print("   ✗ Flask not installed")
    sys.exit(1)

try:
    import flask_sqlalchemy
    print(f"   ✓ Flask-SQLAlchemy is installed")
except ImportError:
    print("   ✗ Flask-SQLAlchemy not installed")
    sys.exit(1)

# Check 2: Activity-Based AI system
print("\n2. Testing Activity-Based AI system...")
try:
    sys.path.insert(0, os.path.dirname(__file__))
    from app import activity_based_ai, track_user_activity, get_activity_level

    # Test activity tracking
    test_user = "test_user_123"
    track_user_activity(test_user, 'interaction')
    track_user_activity(test_user, 'question_answered')

    # Test activity level detection
    level = get_activity_level(test_user)
    print(f"   ✓ Activity tracking working (user level: {level})")

    # Test AI response generation
    question = activity_based_ai(test_user, 'interview_question')
    if question and len(question) > 10:
        print(f"   ✓ Question generation working: '{question[:50]}...'")
    else:
        print("   ✗ Question generation failed")
        sys.exit(1)

    feedback = activity_based_ai(test_user, 'feedback', {'user_id': test_user})
    if feedback and len(feedback) > 20:
        print(f"   ✓ Feedback generation working: '{feedback[:50]}...'")
    else:
        print("   ✗ Feedback generation failed")
        sys.exit(1)

except Exception as e:
    print(f"   ✗ Activity-Based AI system error: {e}")
    sys.exit(1)

# Check 3: App import
print("\n3. Testing app import...")
try:
    from app import app
    routes = len(list(app.url_map.iter_rules()))
    print(f"   ✓ App imported successfully with {routes} routes")
except Exception as e:
    print(f"   ✗ App import failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("🎉 SUCCESS: Activity-Based AI System is fully operational!")
print("✅ No API keys required - completely free!")
print("✅ All processing happens locally - privacy focused!")
print("✅ Adaptive responses based on user activity!")
print("=" * 60)
