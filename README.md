# Waste2Cash ♻️

A web application to combat street waste in South Africa by connecting users with recycling centers and incentivizing proper waste disposal through environmental impact tracking and rewards.

## Problem Statement
South Africa faces a growing waste crisis, with over 90% of recyclable materials ending up in landfills or streets. Waste2Cash addresses this by creating a direct link between citizens and recycling facilities while educating users about their environmental impact.

## Key Features
- 📅 Schedule waste collections with certified centers
- 📍 Find recycling centers across all 9 provinces
- 🌱 Real-time Eco Calculator (CO₂ saved, trees preserved)
- 📊 Personal dashboard with achievements & progress tracking
- 🔒 Secure user authentication & data protection

## Tech Stack
- **Backend**: Python, Flask, SQLAlchemy
- **Frontend**: HTML, CSS, Bootstrap, Chart.js
- **Database**: SQLite (Production-ready for PostgreSQL)
- **Auth**: Flask-Login, Werkzeug security

## Installation
```bash
# Clone repository
git clone https://github.com/yourusername/Waste2Cash.git

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
flask shell
>>> from app import db
>>> db.create_all()
>>> exit()

# Run application
python app.py
