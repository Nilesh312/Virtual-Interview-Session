import importlib

import app


def setup_module(module):
    importlib.reload(app)


def test_get_answer_tips_returns_string():
    tip = app.get_answer_tips("What is your greatest strength?", user_id="testuser")
    assert isinstance(tip, str)
    assert tip.strip() != ""


def test_feedback_includes_improvement_tips():
    feedback = app.get_ai_feedback("Tell me about a time you led a project", "I managed a team and delivered results", user_id="testuser")
    # feedback should contain the tips section indicator used in generate_feedback_response
    assert "Tips for improvement" in feedback or "💡 Tips" in feedback


def test_feedback_includes_emotion_comments():
    # when emotion context is provided, feedback text should mention it
    feedback = app.generate_feedback_response('new', {'question': 'Q?', 'answer': 'Test answer', 'emotion': 'nervous', 'score': 5})
    assert 'nervous' in feedback.lower() or 'relax' in feedback.lower() or '😬' in feedback


def test_generate_summary_response_contains_key_sections():
    fake_feedback = [
        {"question": "Q1", "answer": "A1", "score": 8, "feedback": "Good", "tips": "Use STAR"}
    ]
    summary = app.generate_summary_response("new", {"feedback_list": fake_feedback, "average_score": 8.0, "user_id": "testuser"})
    assert "Interview Session Complete" in summary
    assert "Improvement" in summary or "Key Improvement Areas" in summary
    # summary should include high level headings but aggregation is template-only
    assert "Interview Session Complete" in summary


def test_generate_summary_includes_emotion_counts():
    fake_feedback = [
        {"question": "Q1", "answer": "A1", "score": 7, "feedback": "Good", "tips": "Tip", "emotion": "confident"},
        {"question": "Q2", "answer": "A2", "score": 5, "feedback": "OK", "tips": "Tip", "emotion": "nervous"},
        {"question": "Q3", "answer": "A3", "score": 6, "feedback": "OK", "tips": "Tip", "emotion": "neutral"}
    ]
    summary = app.generate_summary_response("engaged", {"feedback_list": fake_feedback, "average_score": 6.0, "user_id": "testuser"})
    assert "Confident: 1" in summary
    assert "Nervous: 1" in summary
    assert "Neutral: 1" in summary


def test_is_gibberish_helper():
    assert app.is_gibberish("")
    assert app.is_gibberish("dfhdhfdhg")
    assert not app.is_gibberish("This is a real sentence with vowels.")


def test_gibberish_answer_triggers_poor_score_and_feedback():
    gibberish = "dfhdhfdhg"
    score = app.evaluate_answer(gibberish)
    assert score == 1.0
    # feedback should explicitly warn about meaningless response
    feedback = app.generate_feedback_response('new', {'question': 'Q?', 'answer': gibberish})
    assert "didn't seem" in feedback or "not relevant" in feedback or "random" in feedback
    # summary should mark poor performance if included
    fake_feedback = [{"question": "Q?", "answer": gibberish, "score": score, "feedback": feedback, "tips": "Tip", "poor": True}]
    summary = app.generate_summary_response('new', {"feedback_list": fake_feedback, "average_score": 1.0, "user_id": "testuser"})
    assert "unclear" in summary or "nonsensical" in summary or "⚠️" in summary

def test_evaluate_answer_emotion_adjustments():
    base = app.evaluate_answer("I handled a complex task successfully.")
    confident = app.evaluate_answer("I handled a complex task successfully.", emotion='confident')
    nervous = app.evaluate_answer("I handled a complex task successfully.", emotion='nervous')
    assert confident >= base
    assert nervous <= base
