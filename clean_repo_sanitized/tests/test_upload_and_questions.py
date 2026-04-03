import io
import os
import tempfile
import importlib

import pytest
import app
from flask import url_for

@pytest.fixture

def client():
    # configure testing mode and ensure database tables are available
    app.app.config['TESTING'] = True
    with app.app.app_context():
        # create tables in case they don't exist yet
        app.db.create_all()
    with app.app.test_client() as c:
        yield c


def setup_module(module):
    # ensure application is loaded and database tables are created
    with app.app.app_context():
        app.db.create_all()


def login_test_user(client):
    # create a dummy user directly in database if none exists
    with app.app.app_context():
        user = app.User.query.filter_by(email='test@example.com').first()
        if not user:
            user = app.User(username='test', email='test@example.com', password=app.generate_password_hash('password'))
            app.db.session.add(user)
            app.db.session.commit()
    # perform login via POST
    return client.post('/login', data={'email': 'test@example.com', 'password': 'password'}, follow_redirects=True)


def test_upload_resume_and_certificate(client, tmp_path):
    login_test_user(client)
    # create a tiny resume file
    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("Experienced Python developer")

    response = client.post('/upload', data={
        'document': (open(resume_path, 'rb'), 'resume.txt'),
        'doc_type': 'resume'
    }, content_type='multipart/form-data', follow_redirects=True)
    assert b'Resume uploaded' in response.data
    with client.session_transaction() as sess:
        assert 'resume' in sess['document_analysis']

    # upload certificate
    cert_path = tmp_path / "cert.pdf"
    cert_path.write_text("AWS Certified Solutions Architect")
    response = client.post('/upload', data={
        'document': (open(cert_path, 'rb'), 'cert.pdf'),
        'doc_type': 'certificate'
    }, content_type='multipart/form-data', follow_redirects=True)
    assert b'Certificate uploaded' in response.data
    with client.session_transaction() as sess:
        da = sess['document_analysis']
    assert 'certificates' in da and isinstance(da['certificates'], list)
    assert len(da['certificates']) >= 1

    # check progress page displays certificate count if available
    resp = client.get('/progress')
    assert b'certificates' in resp.data

    # dashboard should include progressCard element and appropriate link
    resp = client.get('/dashboard')
    assert b'id="progressCard"' in resp.data
    assert b'url_for' not in resp.data  # ensure template rendered
    assert b'progress' in resp.data  # link to /progress present


def test_generate_question_with_multiple_documents():
    context = {'document_analysis': {'resume': 'python django javascript', 'certificates': ['aws', 'gcp']}, 'asked_questions': []}
    q = app.generate_question_response('active', context)
    assert isinstance(q, str) and q
