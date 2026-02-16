# RecruitDesk AI

**AI-Powered Resume Ranking Web Application**

RecruitDesk AI is a professional intelligent application that uses advanced artificial intelligence to rank resumes based on their match with job descriptions. Now powered by **Hybrid Scoring** (Semantic + Keyword) and **Explainable AI** to provide deep insights into candidate matches.

![RecruitDesk AI](./assets/logo.png)

## 🎯 Features

- **Cinematic Landing Animation**: Professional intro with logo glow effects and smooth transitions
- **Advanced AI Ranking**: Powered by `all-mpnet-base-v2` for superior semantic understanding
- **Hybrid Scoring Algorithm**: Combines deep semantic search (60%) with keyword & skill matching (40%)
- **Entity Extraction**: Automatically identifies Skills, Experience, and Education sections
- **Explainable AI**: Provides "Match Breakdown" and "Why this match?" insights for every candidate
- **Drag & Drop Upload**: Intuitive file upload with support for up to 10 PDF resumes
- **Beautiful UI**: Dark theme with glassmorphism design and smooth animations
- **Responsive Design**: Works seamlessly on desktop and mobile devices

## 🏗 Tech Stack

### Backend
- **Python 3.11+**
- **FastAPI** - Modern, fast web framework
- **spaCy** - NLP for entity extraction (`en_core_web_sm`)
- **sentence-transformers** - State-of-the-art embeddings (`all-mpnet-base-v2`)
- **scikit-learn & NumPy** - Similarity calculations
- **pdfplumber** - Robust PDF text extraction

### Frontend
- **React 18** - UI framework
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first styling
- **Framer Motion** - Smooth animations
- **Axios** - HTTP client

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- Node.js 16 or higher

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # macOS/Linux
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. **(Optional)** Manually download the spaCy model (automatically handled on first run):
   ```bash
   python -m spacy download en_core_web_sm
   ```

5. Start the backend server:
   ```bash
   uvicorn main:app --reload
   ```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

The application will be available at `http://localhost:5173`

## 📖 Usage

1. **Open the application** in your browser at `http://localhost:5173`
2. **Watch the intro animation** featuring the RecruitDesk AI logo
3. **Paste a job description** in the text area
4. **Upload PDF resumes** by dragging and dropping or clicking to browse
5. **Click "Analyze Candidates"** to process the resumes
6. **View ranked results** sorted by match percentage
7. **Click on a result card** to expand "Match Breakdown", "Matched Skills", and "Reasons"

## 🔌 API Endpoints

### `POST /rank-resumes`
Rank resumes based on job description similarity using hybrid scoring.

**Request:**
- `job_description` (form field): Job description text
- `resumes` (files): Multiple PDF files (max 10)

**Response:**
```json
{
  "success": true,
  "total_resumes": 2,
  "ranked_resumes": [
    {
      "filename": "candidate_a.pdf",
      "match_percentage": 92.5,
      "match_details": {
        "semantic_score": 95.2,
        "keyword_score": 88.0,
        "matched_skills": ["python", "react", "aws", "docker"],
        "missing_skills": ["kubernetes"],
        "match_reasons": [
          "High semantic similarity to job description",
          "Matched key skills: python, react, aws, docker",
          "Strong overlap in terminology and domain language"
        ]
      }
    },
    {
      "filename": "candidate_b.pdf",
      "match_percentage": 65.4,
      "match_details": {
       ...
      }
    }
  ]
}
```

### `GET /health`
Health check endpoint to verify API and model status.

## ⚡ Performance

- **Powerful Model**: Uses `all-mpnet-base-v2` (~420MB) for maximum accuracy
- **Fast Processing**: Model loaded once at startup
- **Efficient**: Automatic cleanup of temporary files

## 📁 Project Structure

```
recruitdesk-ai/
├── backend/
│   ├── main.py              # FastAPI application (AI Core)
│   ├── requirements.txt     # Python dependencies
│   └── .gitignore
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── LandingAnimation.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   └── ResultCard.jsx  # Updated with Match Details
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── public/
│   │   └── logo.png
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js
├── assets/
│   └── logo.png
└── README.md
```

## 📝 Notes

- **First Run**: The application will download the AI models (~450MB total) on the first start. This may take 1-2 minutes depending on your internet connection.
- **Privacy**: All processing happens locally. No data is sent to the cloud.
- **MVP**: Uses local processing without a database.

## 🎬 UX Flow

1. User opens website → Cinematic logo animation plays
2. Animation transitions to dashboard
3. User pastes job description
4. User uploads PDF resumes
5. User clicks "Analyze Candidates"
6. AI performs **Hybrid Scoring**:
   - Encodes text into vectors for semantic match
   - Extracts entities and keywords for skill match
7. Results display with **Explainable AI** insights

## 📄 License

This project is for demonstration purposes.

---
