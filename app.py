import os
import random
from datetime import datetime, timezone

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from dotenv import load_dotenv, dotenv_values

from pypdf import PdfReader
from docx import Document
from textblob import TextBlob

# Load environment variables from .env file
load_dotenv(override=True)

# Get values directly from .env file (empty dict if file missing)
try:
    env_values = dotenv_values('.env') if os.path.isfile('.env') else {}
except Exception:
    env_values = {}

# ==================================
# CONFIGURATION
# ==================================

app = Flask(__name__)
app.config['SECRET_KEY'] = env_values.get("SECRET_KEY") or os.getenv(
    "SECRET_KEY", "virtual_hire_secret_development"
)
db_url = os.environ.get('DATABASE_URL', 'sqlite:///users.db')
if db_url and db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+pg8000://")
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['UPLOAD_FOLDER'] = "uploads"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 
db = SQLAlchemy(app)

if not os.path.exists("uploads"):
    os.makedirs("uploads")


def ensure_db_schema():
    """Perform lightweight schema migrations on startup.

    Currently this just ensures the `doc_type` column exists on
    DocumentUpload for older databases created before the feature was added.
    """
    from sqlalchemy import inspect
    insp = inspect(db.engine)
    if insp.has_table('document_upload'):
        cols = [c['name'] for c in insp.get_columns('document_upload')]
        if 'doc_type' not in cols:
            try:
                # SQLite supports ALTER TABLE ADD COLUMN
                from sqlalchemy import text
                db.session.execute(
                    text("ALTER TABLE document_upload ADD COLUMN doc_type VARCHAR(50) DEFAULT 'resume'")
                )
                db.session.commit()
                print('Added missing doc_type column to document_upload table')
            except Exception as e:
                print('Failed to add doc_type column:', e)

# run schema update right away
with app.app_context():
    try:
        ensure_db_schema()
    except Exception as schema_err:
        print('Schema check error:', schema_err)


# Inject current time helper into all templates to support {{ now.year }} usage
@app.context_processor
def inject_now():
    from datetime import datetime
    return {'now': datetime.now(timezone.utc)}

# ==================================
# DATABASE MODELS
# ==================================


class User(db.Model):
    """User model for storing user account information."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(256))


class DocumentUpload(db.Model):
    """Document upload model for storing uploaded files, type, and extracted text."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    file_path = db.Column(db.String(300))
    doc_type = db.Column(db.String(50), default='resume')  # 'resume' or 'certificate'
    extracted_text = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


# ==================================
# FILE EXTRACTION
# ==================================


def extract_text(file_path: str) -> str:
    """Extract text content from various file formats.

    Args:
        file_path: Path to the file to extract text from

    Returns:
        Extracted text content as a string

    Supports: PDF, DOCX, TXT files
    """
    text = ""

    if file_path.endswith(".pdf"):
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() or ""

    elif file_path.endswith(".docx"):
        doc = Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"

    elif file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

    return text.strip()


# ==================================
# ACTIVITY-BASED AI SYSTEM
# ==================================

# Activity tracking for personalized responses
user_activity = {}


def track_user_activity(user_id: str, activity_type: str, data=None) -> None:
    """Track user activity for personalized AI responses.

    Args:
        user_id: Unique identifier for the user
        activity_type: Type of activity ('interaction', 'question_answered', etc.)
        data: Optional additional data for the activity
    """
    if user_id not in user_activity:
        user_activity[user_id] = {
            'interactions': 0,
            'questions_answered': 0,
            'time_spent': 0,
            'last_activity': datetime.now(timezone.utc),
            'response_quality': 'medium',
            'topics_discussed': set()
        }

    activity = user_activity[user_id]
    activity['interactions'] += 1
    activity['last_activity'] = datetime.now(timezone.utc)

    if activity_type == 'question_answered':
        activity['questions_answered'] += 1
    elif activity_type == 'time_update':
        activity['time_spent'] += data.get('duration', 0)
    elif activity_type == 'topic':
        activity['topics_discussed'].add(data.get('topic', ''))

def get_activity_level(user_id: str) -> str:
    """Determine user activity level based on tracked data.

    Args:
        user_id: Unique identifier for the user

    Returns:
        Activity level: 'new', 'engaged', 'active', or 'experienced'
    """
    if user_id not in user_activity:
        return 'new'

    activity = user_activity[user_id]
    interactions = activity['interactions']
    questions = activity['questions_answered']
    time_spent = activity['time_spent']

    if interactions > 20 or time_spent > 1800:  # 30+ minutes
        return 'experienced'
    elif interactions > 10 or time_spent > 600:  # 10+ minutes
        return 'active'
    elif interactions > 3:
        return 'engaged'
    else:
        return 'new'

def activity_based_ai(user_id: str, request_type: str, context=None) -> str:
    """Free AI system that responds based on user activity patterns.

    Args:
        user_id: Unique identifier for the user
        request_type: Type of request ('document_analysis', 'interview_question', etc.)
        context: Optional context data for the request

    Returns:
        AI-generated response based on user activity level
    """
    activity_level = get_activity_level(user_id)

    # Track this interaction
    track_user_activity(user_id, 'interaction')

    if request_type == 'document_analysis':
        return generate_document_analysis_response(activity_level, context)

    elif request_type == 'interview_question':
        return generate_question_response(activity_level, context)

    elif request_type == 'feedback':
        return generate_feedback_response(activity_level, context)

    elif request_type == 'session_summary':
        return generate_summary_response(activity_level, context)

    elif request_type == 'answer_tip':
        return generate_answer_tip_response(activity_level, context)

    else:
        return "I'm here to help with your virtual interview preparation!"

def generate_document_analysis_response(activity_level: str, context) -> str:
    """Generate document analysis based on user activity.

    Args:
        activity_level: User's activity level ('new', 'engaged', 'active', 'experienced')
        context: Context data containing document information

    Returns:
        Personalized document analysis response
    """
    base_responses = {
        'new': (
            "Welcome! I've analyzed your document. You appear to be starting "
            "your career journey. Focus on building practical experience and "
            "highlighting your learning potential."
        ),
        'engaged': (
            "Good progress! Your document shows solid foundation. Consider "
            "emphasizing specific achievements and measurable results from "
            "your projects."
        ),
        'active': (
            "Excellent engagement! Your profile demonstrates growing expertise. "
            "Highlight leadership experiences and complex problem-solving skills."
        ),
        'experienced': (
            "Impressive experience level! Your document reflects deep expertise. "
            "Focus on strategic contributions and mentoring others."
        )
    }

    response = base_responses.get(activity_level, base_responses['new'])

    # Add personalized suggestions based on activity
    if activity_level in ['active', 'experienced']:
        response += "\n\nBased on your activity, I recommend focusing on advanced technical skills and leadership qualities."

    return response


def generate_question_response(activity_level: str, context=None) -> str:
    """Generate interview questions based on user activity and document analysis.

    Args:
        activity_level: User's activity level ('new', 'engaged', 'active', 'experienced')
        context: Context data including document_analysis and asked_questions

    Returns:
        Interview question appropriate for the user's level and document content
    """
    document_analysis = context.get('document_analysis') if context else None
    asked_questions = context.get('asked_questions', []) if context else []

    # support nested analysis (resume + certificates)
    if isinstance(document_analysis, dict):
        # join all text pieces into one string for keyword scanning
        pieces = []
        for v in document_analysis.values():
            if isinstance(v, str):
                pieces.append(v)
            elif isinstance(v, list):
                pieces.extend([str(x) for x in v])
        document_analysis = "\n".join(pieces)

    # Base question categories
    question_categories = {
        'technical_skills': [
            "Can you walk me through your experience with {skill}? What specific projects have you used it for?",
            "How do you stay current with {skill} best practices and new developments?",
            "Describe a challenging technical problem you solved using {skill}. What was your approach?",
            "How would you explain {skill} concepts to someone without technical background?"
        ],
        'projects_experience': [
            "Tell me about the most complex project you've worked on. What were the biggest challenges?",
            "How do you approach project planning and timeline estimation?",
            "Describe a project where you had to learn something new quickly. How did you adapt?",
            "How do you handle changing requirements or scope creep in projects?"
        ],
        'problem_solving': [
            "Describe your debugging process when you encounter a difficult technical issue.",
            "How do you approach optimizing code performance or system efficiency?",
            "Tell me about a time when you had to make a difficult technical decision. How did you evaluate options?",
            "How do you balance technical debt with feature development?"
        ],
        'team_collaboration': [
            "How do you handle disagreements with team members about technical approaches?",
            "Describe your experience with code reviews. What do you look for?",
            "How do you mentor junior developers or share knowledge with your team?",
            "Tell me about a successful collaboration experience. What made it work well?"
        ],
        'leadership_growth': [
            "How do you approach leading a technical team or project?",
            "Describe your experience with architectural decisions. How do you evaluate trade-offs?",
            "How do you measure and improve team productivity and quality?",
            "Tell me about your experience with hiring or interviewing technical candidates."
        ],
        'behavioral_questions': [
            "Tell me about a time when you failed at something. How did you handle it?",
            "Describe a situation where you had to work under pressure. How did you manage?",
            "How do you handle constructive criticism or feedback on your work?",
            "Tell me about a time when you went above and beyond for a project or team."
        ]
    }

    # Activity-level specific question sets
    activity_questions = {
        'new': question_categories['technical_skills'][:2] + question_categories['projects_experience'][:2] + [
            "What programming languages are you most comfortable with?",
            "Describe a school or personal project that you're proud of.",
            "Why are you interested in software development?",
            "How do you approach learning new technologies?"
        ],
        'engaged': question_categories['technical_skills'][:3] + question_categories['problem_solving'][:2] + question_categories['team_collaboration'][:2] + [
            "Tell me about a challenging problem you solved recently.",
            "How do you stay updated with technology trends?",
            "Describe your experience working in a team environment.",
            "What are your career goals for the next few years?"
        ],
        'active': question_categories['problem_solving'] + question_categories['team_collaboration'] + question_categories['leadership_growth'][:2] + [
            "How do you handle conflicting priorities in a project?",
            "What strategies do you use for debugging complex issues?",
            "How do you approach system design and architecture?",
            "Describe your experience with agile development methodologies."
        ],
        'experienced': question_categories['leadership_growth'] + question_categories['problem_solving'][2:] + question_categories['team_collaboration'][2:] + [
            "How do you mentor junior developers on your team?",
            "What metrics do you use to measure development team performance?",
            "How do you handle technical debt in long-term projects?",
            "Describe your approach to technology strategy and roadmap planning."
        ]
    }

    # Get available questions for this activity level
    available_questions = activity_questions.get(activity_level, activity_questions['new'])

    # If document analysis is available, prioritize file-based questions
    if document_analysis:
        # Extract skills and technologies from document analysis
        doc_text = document_analysis.lower()

        # Common tech skills to look for
        tech_skills = [
            'python', 'javascript', 'java', 'c++', 'c#', 'php', 'ruby', 'go', 'rust',
            'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring',
            'sql', 'mysql', 'postgresql', 'mongodb', 'redis',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'git', 'linux'
        ]

        found_skills = [skill for skill in tech_skills if skill in doc_text]

        # Generate file-specific questions
        file_based_questions = []

        if found_skills:
            # Use template questions with found skills
            for skill in found_skills[:3]:  # Limit to 3 skills to avoid too many questions
                skill_questions = [
                    f"Can you elaborate on your experience with {skill}? What specific projects or challenges have you encountered?",
                    f"How have you applied {skill} in your work? Can you give a concrete example?",
                    f"What do you consider your strongest skills in {skill}? Where do you see room for improvement?"
                ]
                file_based_questions.extend(skill_questions)

        # Add project-specific questions if projects are mentioned
        if 'project' in doc_text or 'developed' in doc_text or 'built' in doc_text:
            file_based_questions.extend([
                "Can you walk me through a specific project from your experience? What was your role and the outcome?",
                "Tell me about the technologies and tools you used in your most recent project.",
                "What was the most challenging aspect of a project you've worked on, and how did you overcome it?"
            ])

        # Add experience-level questions based on document content
        if 'team' in doc_text or 'collaborat' in doc_text:
            file_based_questions.extend([
                "Describe your experience working in teams. How do you contribute to team success?",
                "How do you handle communication and collaboration in distributed or remote teams?"
            ])

        if 'lead' in doc_text or 'manag' in doc_text or 'senior' in doc_text:
            file_based_questions.extend([
                "What leadership experiences have you had in technical roles?",
                "How do you approach mentoring and knowledge sharing with junior team members?"
            ])

        # Combine file-based and general questions, prioritizing file-based ones
        if file_based_questions:
            available_questions = file_based_questions + available_questions

    # Filter out already asked questions
    unasked_questions = [q for q in available_questions if q not in asked_questions]

    # If all questions have been asked, reset or use general pool
    if not unasked_questions:
        # Reset asked questions if we've exhausted the pool
        if context is not None and 'asked_questions' in context:
            context['asked_questions'].clear()
        unasked_questions = available_questions

    # Select random question from available ones
    selected_question = random.choice(unasked_questions)

    # Ensure we can track asked questions in the provided context
    if context is not None:
        context.setdefault('asked_questions', asked_questions)
        context['asked_questions'].append(selected_question)

    return selected_question


def generate_feedback_response(activity_level: str, context=None) -> str:
    """Generate clear, understandable feedback based on user activity.

    Args:
        activity_level: User's activity level ('new', 'engaged', 'active', 'experienced')
        context: Optional context data containing user information

    Returns:
        Clear, actionable feedback message
    """
    context = context or {}
    question = context.get('question', '')
    answer = context.get('answer', '')
    user_id = context.get('user_id', '')

    # Analyze the answer quality
    # flag gibberish separately to provide explicit poor feedback
    if is_gibberish(answer):
        return (
            "Your response didn't seem relevant or understandable. "
            "Please provide a clear answer to the question rather than random text. "
            "This will ensure you get useful feedback and a better score next time."
        )

    answer_words = len(answer.split()) if answer else 0
    has_structure = any(word in answer.lower() for word in ['situation', 'task', 'action', 'result', 'because', 'first', 'then', 'finally'])
    has_examples = any(word in answer.lower() for word in ['example', 'instance', 'project', 'experience', 'worked', 'developed'])

    # Base feedback based on activity level
    feedback_templates = {
        'new': "You're just getting started - that's great! Focus on speaking clearly and sharing what you know. Every answer helps you improve.",
        'engaged': "You're building good habits! Try to give specific examples from your work. Interviewers love hearing real stories.",
        'active': "You're doing well! Add more details about your thinking process. Explain why you made certain choices.",
        'experienced': "Your experience shows through! Share how your work impacted others. Talk about what you learned and taught others."
    }

    feedback = feedback_templates.get(activity_level, feedback_templates['new'])

    # add comments based on detected emotion (if available)
    emotion = context.get('emotion')
    if emotion:
        if emotion == 'nervous':
            feedback += (
                "\n\n🤔 You seemed a bit nervous during this answer. "
                "Try to relax and maintain steady eye contact to appear more confident."
            )
        elif emotion == 'confident':
            feedback += (
                "\n\n😊 You appeared confident which enhances your delivery. Keep up the poise!"
            )
        elif emotion == 'neutral':
            feedback += (
                "\n\n😐 Your expression was fairly neutral. Adding slight enthusiasm "
                "can make your answers more engaging."
            )

    # Add specific, actionable advice
    suggestions = []

    if answer_words < 20:
        suggestions.append("Try to give longer answers with more details about your experience.")
    elif answer_words > 150:
        suggestions.append("Your answer is detailed! In a real interview, you might want to be more concise while keeping the key points.")

    if not has_structure:
        suggestions.append("Use simple structure: explain the situation, what you did, and what happened.")
    else:
        suggestions.append("Good structure! You clearly explained the situation, actions, and results.")

    if not has_examples:
        suggestions.append("Include specific examples from your work to make your answer more convincing.")
    else:
        suggestions.append("Great examples! Specific stories make your answers much stronger.")

    # Add score-based encouragement
    score = context.get('score', 5)
    if score >= 8:
        feedback += " Excellent work! This is a strong answer that would impress interviewers."
    elif score >= 6:
        feedback += " Good job! This shows solid understanding and communication skills."
    elif score >= 4:
        feedback += " You're on the right track! Keep practicing to build confidence."
    else:
        feedback += " Unfortunately, this answer scored low. Try to focus on clear, structured responses next time."

    # Add 1-2 specific suggestions
    if suggestions:
        feedback += "\n\n💡 Tips for improvement:\n• " + "\n• ".join(suggestions[:2])

    return feedback

def generate_summary_response(activity_level, context=None):
    """Generate clear, understandable session summary"""
    context = context or {}
    feedback_list = context.get('feedback_list', [])
    average_score = context.get('average_score', 0)
    user_id = context.get('user_id', '')

    activity = user_activity.get(user_id, {})
    interactions = activity.get('interactions', 0)
    questions = activity.get('questions_answered', 0)
    time_spent = activity.get('time_spent', 0)

    # Calculate improvement areas
    total_questions = len(feedback_list)
    strong_answers = sum(1 for f in feedback_list if (f.get('score', 0) >= 7))
    good_answers = sum(1 for f in feedback_list if 5 <= f.get('score', 0) < 7)
    needs_work = total_questions - strong_answers - good_answers

    # compute emotion distribution from feedback entries
    emotion_counts = {'confident': 0, 'neutral': 0, 'nervous': 0}
    for f in feedback_list:
        emo = f.get('emotion')
        if emo in emotion_counts:
            emotion_counts[emo] += 1

    summary = f"""
## 🎯 Interview Session Complete!

**Your Performance:**
• Total Questions: {total_questions}
• Average Score: {average_score:.1f}/10
• Strong Answers: {strong_answers}
• Good Answers: {good_answers}
• Areas to Improve: {needs_work}

**Session Stats:**
• Time Practiced: {time_spent // 60} minutes
• Activity Level: {activity_level.title()}

**Emotion Summary:**
• Confident: {emotion_counts['confident']}
• Neutral: {emotion_counts['neutral']}
• Nervous: {emotion_counts['nervous']}

"""

    if average_score >= 8:
        summary += "### 🌟 Excellent Performance!\nYou're well-prepared for interviews. Focus on maintaining this high standard."
    elif average_score >= 6:
        summary += "### ✅ Good Progress!\nYou're showing solid interview skills. Keep practicing to reach expert level."
    elif average_score >= 4:
        summary += "### 📈 Getting Better!\nYou're improving with each session. Keep building confidence."
    else:
        summary += "### 🎯 Keep Practicing!\nEvery session makes you stronger. Focus on clear, detailed answers."

    # call-out any poor answers explicitly
    if any(f.get('score', 0) <= 1 or f.get('poor') for f in feedback_list):
        summary += "\n\n⚠️ Some of your responses were unclear or nonsensical. "
        summary += "Please review the detailed Q&A below and focus on providing meaningful answers."

    summary += """

### 💡 Key Improvement Areas:

**Communication Skills:**
• Speak clearly and confidently
• Use simple, direct language
• Show enthusiasm for your work

**Answer Structure:**
• Explain the situation first
• Describe what you did
• Share the results achieved

**Content Quality:**
• Include specific examples
• Quantify your impact when possible
• Connect your experience to the job

### 🎯 Next Steps:
1. Practice 2-3 more sessions this week
2. Record yourself answering questions
3. Review your strong answers for patterns
4. Work on your improvement areas

Keep practicing - you're building valuable skills! 🚀
"""

    return summary


def generate_answer_tip_response(activity_level: str, context=None) -> str:
    """Provide generic advice on how to answer a particular interview question.

    The tip is independent of the candidate's own answer, offering guidance on
    structure, content, and style appropriate for the question.
    """
    context = context or {}
    question = context.get('question', '')

    # Basic tip template - we keep it general and adapt wording by activity level
    base_tip = (
        f"For the question \"{question}\", try using the STAR method: describe the "
        "Situation, explain the Task, outline the Actions you took, and finish with "
        "the Results. Be specific, give real examples, and quantify your impact when "
        "possible."
    )

    if activity_level == 'new':
        return base_tip + " Start simple and focus on communicating clearly."
    elif activity_level == 'engaged':
        return base_tip + " Add a bit more detail and reflect briefly on what you learned."
    elif activity_level == 'active':
        return base_tip + " Emphasize your thought process and any collaboration involved."
    else:  # experienced
        return (base_tip + " Highlight strategic decisions and outcomes, and how you "
                "mentored others or scaled the solution.")


# ==================================
# DOCUMENT ANALYSIS
# ==================================

def analyze_document(text: str, user_id=None) -> str:
    """Analyze uploaded document content.

    Args:
        text: Extracted text from the document
        user_id: User identifier for activity tracking

    Returns:
        Analysis of the document content
    """
    if not text or len(text.strip()) == 0:
        return "No text content to analyze."

    # Use activity-based AI for document analysis
    return activity_based_ai(user_id, 'document_analysis', {'text': text})


# ==================================
# QUESTION GENERATOR
# ==================================


def generate_question(history, document_analysis=None, difficulty="medium", user_id=None, asked_questions=None) -> str:
    """Generate an interview question based on user activity and context.

    Args:
        history: Conversation history
        document_analysis: Optional document analysis context
        difficulty: Question difficulty level ('easy', 'medium', 'hard')
        user_id: User identifier for activity tracking
        asked_questions: List of previously asked questions to avoid repeats

    Returns:
        Generated interview question
    """
    # Use activity-based AI for question generation
    context = {
        'history': history,
        'document_analysis': document_analysis,
        'difficulty': difficulty,
        'asked_questions': asked_questions or []
    }
    return activity_based_ai(user_id, 'interview_question', context)


# ==================================
# ANSWER EVALUATION
# ==================================

def is_gibberish(text: str) -> bool:
    """Detect if the provided text appears to be nonsensical or random.

    This heuristic checks for a lack of vowels or alphabetic characters which
    typically indicates the user entered garbage (e.g. "dfhdhfdhg").
    """
    if not text or not text.strip():
        return True
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return True
    vowel_count = sum(1 for c in letters if c.lower() in 'aeiou')
    # fewer than 10% vowels suggests gibberish
    if vowel_count / len(letters) < 0.1:
        return True
    return False


def evaluate_answer(answer: str, emotion: str = None) -> float:
    """Evaluate the quality of an interview answer.

    Args:
        answer: The user's answer text
        emotion: Optional emotion label detected during the answer
                 ('confident', 'nervous', 'neutral')

    Returns:
        Score from 1-10 based on multiple quality factors, adjusted by emotion
    """
    # immediate poor score for gibberish
    if is_gibberish(answer):
        return 1.0

    if not answer.strip():
        return 1.0  # Changed from 0 to 1

    # Enhanced scoring algorithm with more generous thresholds
    text = answer.strip()
    words = text.split()
    word_count = len(words)

    # Sentiment analysis (0-1 scale, converted to 0-2 points)
    sentiment = TextBlob(text).sentiment.polarity
    sentiment_score = max(0, (sentiment + 1) / 2) * 2  # Convert -1/+1 to 0-2

    # Length score (0-2 points) - optimal range 30-200 words (made more generous)
    if word_count < 10:
        length_score = 0.5
    elif word_count < 30:
        length_score = 1.0
    elif word_count <= 200:
        length_score = 2.0
    elif word_count <= 300:
        length_score = 1.5
    else:
        length_score = 1.0

    # Keyword analysis (0-2 points) - expanded keyword list with more common terms
    technical_keywords = [
        "project", "team", "challenge", "solution", "result", "experience",
        "learned", "implemented", "developed", "created", "managed", "led",
        "problem", "issue", "resolved", "fixed", "improved", "achieved",
        "technology", "tool", "framework", "language", "code", "system",
        "work", "job", "role", "responsibility", "task", "goal", "success",
        "time", "process", "approach", "method", "strategy", "plan"
    ]

    keyword_matches = sum(1 for keyword in technical_keywords if keyword in text.lower())
    keyword_score = min(keyword_matches / 3, 2)  # Max 2 points for 3+ keywords (easier)

    # Structure analysis (0-2 points) - check for STAR format elements
    star_elements = ["situation", "task", "action", "result"]
    star_score = sum(1 for element in star_elements if element in text.lower()) / 2

    # Specificity check (0-1 point) - look for concrete details (more indicators)
    specific_indicators = ["%", "$", "specific", "particular", "exact", "precisely",
                          "first", "then", "next", "after", "before", "during",
                          "I", "we", "my", "our", "the"]
    specificity_score = 1 if any(indicator in text.lower() for indicator in specific_indicators) else 0.5

    # Grammar and completeness (0-1 point)
    completeness_score = 1 if text.endswith(('.', '!', '?')) and word_count > 5 else 0.5

    # Calculate final score (max 10 points) with base score boost
    total_score = (
        sentiment_score +      # 0-2
        length_score +         # 0-2
        keyword_score +        # 0-2
        star_score +           # 0-2
        specificity_score +    # 0-1
        completeness_score     # 0-1
    )

    # Apply activity level bonus (experienced users get slight boost)
    final_score = min(round(total_score + 1.0, 2), 10.0)  # Added +1.0 base boost

    # Adjust based on emotion detection
    if emotion == 'confident':
        final_score = min(final_score + 0.5, 10.0)
    elif emotion == 'nervous':
        final_score = max(final_score - 0.5, 1.0)

    return max(final_score, 2.0)  # Minimum score of 2.0


def get_ai_feedback(question: str, answer: str, history=None, user_id=None) -> str:
    """Get AI-powered feedback on user's answer.

    Args:
        question: The interview question asked
        answer: The user's answer
        history: Optional conversation history
        user_id: User identifier for activity tracking

    Returns:
        AI-generated feedback on the answer
    """
    # Use activity-based AI for feedback generation
    return activity_based_ai(user_id, 'feedback', {
        'question': question,
        'answer': answer,
        'history': history,
        'user_id': user_id
    })


def get_answer_tips(question: str, user_id=None) -> str:
    """Generate generic tips for how the user should answer a given question.

    This is used at the end of a session to show the user constructive advice
    about structuring and framing their response for future attempts.

    Args:
        question: The interview question text
        user_id: Optional user identifier for activity-based personalization

    Returns:
        A short tip string related to the question
    """
    return activity_based_ai(user_id, 'answer_tip', {
        'question': question,
        'user_id': user_id
    })


def update_difficulty(answer: str) -> str:
    """Update question difficulty based on answer length.

    Args:
        answer: The user's answer text

    Returns:
        New difficulty level ('easy', 'medium', 'hard')
    """
    words = len(answer.split())

    if words > 120:
        return "hard"
    elif words < 40:
        return "easy"
    return "medium"


# ==================================
# ROUTES
# ==================================

@app.route('/')
def landing() -> str:
    """Render the landing page."""
    return render_template("landing.html")


@app.route('/register', methods=['GET', 'POST'])
def register() -> str:
    """Handle user registration.

    GET: Display registration form
    POST: Process registration and create new user account
    """
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not email or not password:
            flash("All fields are required")
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash("Email already registered")
            return redirect(url_for('register'))

        try:
            user = User(
                username=username,
                email=email,
                password=generate_password_hash(password)
            )
            db.session.add(user)
            db.session.commit()
            flash("Registration successful! Please login.")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash("Registration failed. Please try again.")
            print(f"Registration error: {e}")

    return render_template("register.html")


@app.route('/login', methods=['GET', 'POST'])
def login() -> str:
    """Handle user login.

    GET: Display login form
    POST: Authenticate user and start session
    """
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['history'] = []
            session['difficulty'] = "medium"
            session['document_analysis'] = None
            session['asked_questions'] = []  # Track asked questions to avoid repeats
            session['interview_feedback'] = []  # Store feedback for each answer
            session['total_score'] = 0
            session['answer_count'] = 0
            return redirect(url_for('dashboard'))

        flash("Invalid credentials")
        return redirect(url_for('login'))

    return render_template("login.html")


@app.route('/dashboard')
def dashboard() -> str:
    """Display user dashboard.

    Requires authentication.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template("dashboard.html")


@app.route('/interview')
def interview() -> str:
    """Start or continue an interview session.

    Requires authentication.
    Initializes interview tracking and generates welcome message with first question.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Initialize interview tracking
    if 'interview_feedback' not in session:
        session['interview_feedback'] = []
        session['total_score'] = 0
        session['answer_count'] = 0
        session['asked_questions'] = []  # Reset asked questions

    username = session.get('username', 'User')
    history = session.get('history', [])

    if not history:
        # Create welcome message
        welcome_message = f"Hello {username}! Welcome to your virtual interview session. I'm excited to chat with you today. Let's begin with our first question."
        history = [{"role": "assistant", "content": welcome_message}]

        # Generate first question
        document_analysis = session.get('document_analysis')
        difficulty = session.get('difficulty', 'medium')
        asked_questions = session.get('asked_questions', [])
        first_question = generate_question([], document_analysis, difficulty, session.get('user_id'), asked_questions)
        history.append({"role": "assistant", "content": first_question})

        # Track the asked question
        session['asked_questions'] = asked_questions + [first_question]
        session['history'] = history

    return render_template("chat.html", conversation_history=history)


@app.route('/upload', methods=['POST'])
def upload():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        file = request.files.get('document')
        doc_type = request.form.get('doc_type', 'resume')  # allow resume or certificate

        if not file or file.filename == "":
            flash("No file selected")
            return redirect(url_for('dashboard'))

        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)

        try:
            text = extract_text(path)
        except Exception as extract_exc:
            # extraction may fail for malformed PDFs; continue with empty text
            print(f"Text extraction warning: {extract_exc}")
            text = ""
        
        # if we couldn't pull any text, we still save the upload but analysis will be empty
        if not text:
            # flash a warning but don't abort; user may have uploaded an image or non-text file
            flash("Could not extract text from file; uploaded for record")

        # if the model doesn't yet have doc_type (older DB), omit it
        doc_kwargs = {
            'user_id': session['user_id'],
            'file_path': path,
            'extracted_text': text
        }
        if hasattr(DocumentUpload, 'doc_type'):
            doc_kwargs['doc_type'] = doc_type
        doc = DocumentUpload(**doc_kwargs)
        db.session.add(doc)
        db.session.commit()

        analysis = analyze_document(text, session.get('user_id'))
        # store analysis by type in session for question generation
        existing = session.get('document_analysis', {}) or {}
        if doc_type == 'resume':
            existing['resume'] = analysis
        else:
            existing.setdefault('certificates', []).append(analysis)
        session['document_analysis'] = existing

        flash(f"{doc_type.capitalize()} uploaded and analyzed successfully!")

        return redirect(url_for('dashboard'))
    except Exception as e:
        db.session.rollback()
        flash("Error uploading file. Please try again.")
        print(f"Upload error: {e}")
        return redirect(url_for('dashboard'))


@app.route('/upload_video', methods=['POST'])
def upload_video():
    """Accept uploaded video blob or multipart file from the client and save it to uploads/.

    Returns JSON with saved filename and path on success.
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Prefer multipart form upload under the key 'video'
        if 'video' in request.files:
            file = request.files['video']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
        else:
            # Fallback: raw binary POST (fetch with blob arrayBuffer)
            raw = request.get_data()
            if not raw:
                return jsonify({'error': 'No video data received'}), 400
            timestamp = int(datetime.now(timezone.utc).timestamp())
            filename = f"video_{session.get('user_id')}_{timestamp}.webm"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            with open(save_path, 'wb') as f:
                f.write(raw)

        # Return relative info for client to reference
        return jsonify({'status': 'ok', 'filename': filename, 'path': save_path}), 200

    except Exception as e:
        print(f"Video upload error: {e}")
        return jsonify({'error': f'Failed to save video: {str(e)[:120]}'}), 500


@app.route('/ask', methods=['POST'])
def ask():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    history = session.get('history', [])
    document_analysis = session.get('document_analysis')
    difficulty = session.get('difficulty', "medium")
    asked_questions = session.get('asked_questions', [])

    question = generate_question(history, document_analysis, difficulty, session.get('user_id'), asked_questions)

    history.append({"role": "assistant", "content": question})
    session['history'] = history

    # Track the asked question
    session['asked_questions'] = asked_questions + [question]

    return jsonify({"question": question})


@app.route('/answer', methods=['POST'])
def answer():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request"}), 400

        user_answer = data.get("answer", "").strip()
        emotion = data.get("emotion", None)  # may be 'confident', 'nervous', 'neutral'

        if not user_answer:
            return jsonify({"error": "Answer cannot be empty"}), 400

        history = session.get('history', [])
        
        # Get the last question asked to provide context
        last_question = None
        for msg in reversed(history):
            if msg.get('role') == 'assistant':
                last_question = msg.get('content')
                break
        
        history.append({"role": "user", "content": user_answer})
        
        # Evaluate answer (accounting for emotion if available)
        score = evaluate_answer(user_answer, emotion)
        
        # Get AI-powered feedback on the answer
        ai_feedback = get_ai_feedback(last_question or "Interview Question", user_answer, user_id=session.get('user_id'))
        
        session['difficulty'] = update_difficulty(user_answer)
        
        # Store feedback for session summary
        interview_feedback = session.get('interview_feedback', [])
        total_score = session.get('total_score', 0)
        answer_count = session.get('answer_count', 0)
        
        # determine if the answer was meaningless
        poor_flag = is_gibberish(user_answer)

        # also generate a general tip for answering this question
        answer_tip = get_answer_tips(last_question or "", user_id=session.get('user_id'))

        feedback_entry = {
            "question": last_question,
            "answer": user_answer,
            "score": score,
            "feedback": ai_feedback,
            "tips": answer_tip,
            "emotion": emotion
        }
        if poor_flag:
            feedback_entry["poor"] = True
        interview_feedback.append(feedback_entry)
        total_score += score
        answer_count += 1
        
        session['interview_feedback'] = interview_feedback
        session['total_score'] = total_score
        session['answer_count'] = answer_count
        
        # Generate next question with error handling
        document_analysis = session.get('document_analysis')
        asked_questions = session.get('asked_questions', [])
        next_question = generate_question(history, document_analysis, session['difficulty'], session.get('user_id'), asked_questions)
        
        # Check if there was an error generating the question
        if "Error" in next_question or "error" in next_question.lower():
            # Still add to history but use a fallback
            fallback_q = "Based on your experience, can you tell me about a project where you made a significant impact?"
            history.append({"role": "assistant", "content": fallback_q})
            session['history'] = history
            # Track the fallback question too
            session['asked_questions'] = asked_questions + [fallback_q]
            return jsonify({
                "score": score,
                "ai_feedback": ai_feedback,
                "next_question": fallback_q,
                "difficulty": session['difficulty'],
                "warning": "Using fallback question due to API issues"
            })
        
        # Add next question to history
        history.append({"role": "assistant", "content": next_question})
        session['history'] = history

        # Track the asked question
        session['asked_questions'] = asked_questions + [next_question]

        return jsonify({
            "score": score,
            "ai_feedback": ai_feedback,
            "next_question": next_question,
            "difficulty": session['difficulty']
        })
    except Exception as e:
        print(f"Error processing answer: {e}")
        return jsonify({"error": f"Failed to process answer: {str(e)[:100]}"}), 500


@app.route('/end-interview', methods=['GET'])
def end_interview():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    interview_feedback = session.get('interview_feedback', [])
    total_score = session.get('total_score', 0)
    answer_count = session.get('answer_count', 0)
    
    # Calculate average score
    average_score = round(total_score / answer_count, 2) if answer_count > 0 else 0
    
    # Generate overall summary and tips using AI
    overall_tips = generate_session_summary(interview_feedback, average_score, session.get('user_id'))
    
    return render_template("session_summary.html", 
                         feedback_list=interview_feedback,
                         average_score=average_score,
                         total_answers=answer_count,
                         overall_tips=overall_tips)


@app.route('/progress')
def progress():
    """Display user progress and analytics.

    Requires authentication.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get user's past sessions from database
    user_id = session['user_id']
    past_uploads = DocumentUpload.query.filter_by(user_id=user_id).all()
    
    # Calculate some basic stats
    total_sessions = len(past_uploads)  # Using uploads as proxy for sessions
    total_uploads = len(past_uploads)
    # count certificates separately (guard against missing column)
    try:
        certificate_count = sum(1 for u in past_uploads if getattr(u, 'doc_type', '') == 'certificate')
    except Exception as e:
        # most likely OperationalError from missing column
        certificate_count = 0
        print('Warning: could not count certificates, defaulting to 0 (', e, ')')
    
    # Get session data if available
    interview_feedback = session.get('interview_feedback', [])
    total_score = session.get('total_score', 0)
    answer_count = session.get('answer_count', 0)
    
    average_score = round(total_score / answer_count, 2) if answer_count > 0 else 0
    
    # Determine improvement trend (mock logic)
    improvement_trend = 'stable'
    if average_score > 7.0:
        improvement_trend = 'up'
    elif average_score < 5.0:
        improvement_trend = 'down'
    
    # Skills practiced (based on uploaded documents)
    skills_practiced = ['Communication', 'Problem Solving', 'Technical Skills']
    if past_uploads:
        skills_practiced.append('Resume Analysis')
    
    # Recent activity
    recent_activity = []
    for upload in past_uploads[-3:]:  # Last 3 uploads
        recent_activity.append({
            'date': upload.timestamp.strftime('%Y-%m-%d'),
            'type': 'Resume Upload',
            'score': None
        })
    
    # Add current session if exists
    if interview_feedback:
        recent_activity.append({
            'date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
            'type': 'Interview Session',
            'score': average_score
        })
    
    progress_data = {
        'total_sessions': total_sessions,
        'total_uploads': total_uploads,
        'certificate_count': certificate_count,
        'average_score': average_score if average_score > 0 else 7.5,  # Default if no sessions
        'improvement_trend': improvement_trend,
        'skills_practiced': skills_practiced,
        'recent_activity': recent_activity[-5:]  # Last 5 activities
    }
                            
    return render_template("progress.html", progress_data=progress_data)


def generate_session_summary(feedback_list, average_score: float, user_id=None) -> str:
    """Generate comprehensive summary and improvement tips for the session.

    Args:
        feedback_list: List of feedback entries from the interview
        average_score: Average score across all answers
        user_id: User identifier for activity tracking

    Returns:
        Formatted session summary with tips
    """
    # Use activity-based AI for session summary
    return activity_based_ai(user_id, 'session_summary', {
        'feedback_list': feedback_list,
        'average_score': average_score,
        'user_id': user_id
    })


@app.route('/logout')
def logout() -> str:
    """Clear user session and redirect to landing page."""
    session.clear()
    return redirect(url_for('landing'))


# ==================================
# MAIN
# ==================================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    # Print startup information
    print("\n" + "="*60)
    print("🚀 VIRTUAL JOB INTERVIEW SYSTEM STARTING...")
    print("="*60)
    print("✅ Activity-Based AI System is ready!")
    print("   - Personalized responses based on user activity")
    print("   - No API keys required - completely free!")
    print("   - Adapts to user experience level automatically")
    print("📱 App will be available at: http://127.0.0.1:5000")
    print("="*60 + "\n")

    app.run(debug=True)