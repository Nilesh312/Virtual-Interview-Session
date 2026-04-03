# Virtual Interview System - Setup Guide

## Prerequisites

- Python 3.8+
- pip (Python package manager)

## Key Features

✨ **Free Activity-Based AI System**
- No API keys required
- Personalized responses based on user behavior
- Adapts to experience level automatically
- Tracks interaction patterns for better recommendations

## Installation Steps

### 1. Create Virtual Environment
```bash
python -m venv venv
```

### 2. Activate Virtual Environment

**On Windows (PowerShell):**
```bash
.\venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt):**
```bash
venv\Scripts\activate.bat
```

**On macOS/Linux:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python app.py
```

### 5. Verify Your Setup

When you start the app, you should see:
```
🚀 VIRTUAL JOB INTERVIEW SYSTEM STARTING...
✅ Activity-Based AI System is ready!
📱 App will be available at: http://127.0.0.1:5000
```

## How the Activity-Based AI Works

The system now uses a **free, intelligent activity-tracking system** instead of external AI APIs:

### 🎯 **Personalized Responses**
- **New Users**: Get basic, encouraging feedback and simple questions
- **Engaged Users**: Receive intermediate-level questions and constructive feedback
- **Active Users**: Get advanced questions and detailed improvement suggestions
- **Experienced Users**: Receive senior-level questions and strategic career advice

### 📊 **Activity Tracking**
The system tracks:
- Number of interactions
- Questions answered
- Time spent in sessions
- Response quality patterns
- Topics discussed

### 🔄 **Adaptive Difficulty**
- Questions automatically adjust based on user performance
- Feedback becomes more specific as users progress
- Session summaries provide personalized improvement plans

## Features

✅ **Completely Free** - No API keys or subscriptions required
✅ **Privacy-Focused** - All processing happens locally
✅ **Adaptive Learning** - Improves responses based on user activity
✅ **Personalized Experience** - Tailored to individual user patterns

## Facial Detection Setup

The facial detection feature uses face-api.js which automatically loads from a CDN. 

**First time you use it:**
- The browser will ask for camera permission
- Click "Allow" to enable facial detection
- The system will download detection models (~4MB) on first use
- You'll see status updates in real-time

**Requirements:**
- Webcam/camera device
- HTTPS connection (or localhost for testing)
- Modern browser (Chrome, Firefox, Edge, Safari)

## Troubleshooting

### Facial Detection Issues

**"Initializing camera..." gets stuck:**
- Check if another app is using your camera
- Refresh the page and try again
- Ensure browser has camera permissions

**Border doesn't turn red when no face detected:**
- Make sure JavaScript is enabled
- Refresh the page
- Check browser console for errors (F12)

### API Key Issues

**"Error: Invalid or expired OPENAI_API_KEY"**

Check these steps:

1. **Verify the API key is set:**
   ```bash
   # Windows (PowerShell)
   Write-Host $env:OPENAI_API_KEY
   
   # Windows (Command Prompt)
   echo %OPENAI_API_KEY%
   
   # macOS/Linux
   echo $OPENAI_API_KEY
   ```

2. **If nothing shows, set it again:**
   - Windows (PowerShell): `$env:OPENAI_API_KEY = "sk-..."`
   - Windows (CMD): `set OPENAI_API_KEY=sk-...`
   - Use .env file method instead

3. **Restarted the app after setting the key:**
   - Changes to environment variables require restart
   - Close Flask and run `python app.py` again

4. **API key is valid:**
   - Go to https://platform.openai.com/api-keys
   - Verify your key is in the list
   - Check you haven't hit your usage quota
   - Ensure your account has billing set up

### "I apologize, but I couldn't generate a response at this time"

This means the AI can't generate a response. Check:

1. **Is OPENAI_API_KEY set?** (See above)

## Development Notes

- The system uses GPT-4o-mini model for cost efficiency
- Each interview generates multiple API calls (document analysis, question generation, etc.)
- API usage will count towards your OpenAI account

## Running Tests

After setup, test the API key:
```python
python -c "from app import generate_ai; print(generate_ai([{'role': 'user', 'content': 'Say hello'}]))"
```

If you see "hello" (or similar response), your setup is correct!
