import importlib
import random

import app


def setup_module(module):
    importlib.reload(app)
    random.seed(0)


def test_generate_question_response_no_context():
    # Should not raise and should return a string
    out = app.generate_question_response('new', None)
    assert isinstance(out, str)
    assert out


def test_generate_question_response_empty_context_appends_question():
    ctx = {'asked_questions': []}
    out = app.generate_question_response('new', ctx)
    assert isinstance(out, str)
    assert ctx['asked_questions']
    assert ctx['asked_questions'][-1] == out


def test_generate_question_response_preserves_existing_list():
    ctx = {'asked_questions': ["preexisting question"]}
    out = app.generate_question_response('new', ctx)
    assert isinstance(out, str)
    # ensure we appended the new selected question
    assert ctx['asked_questions'][-1] == out
