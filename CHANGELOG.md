# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - Hiring Decision Engine (Phase 6)

### Added
- Added `decision_engine.py` with weighted composite scoring across 5 factors.
- Added Hire / Consider / Reject recommendations with configurable thresholds.
- Added skill gap analysis with Critical / Important / Nice-to-have severity levels.
- Added bias-aware checks that detect age, gender, nationality, religion, marital status, and photo indicators; flagged only and never scored.
- Added confidence scoring output as a float, High/Medium/Low label, and uncertainty notes.
- Added `POST /hiring-decision` endpoint.
- Added `DecisionCard.jsx` with animated, collapsible candidate decision UI.
- Added a Decision Engine tab in Dashboard with localStorage-persisted auto-open toggle.
- Added a 17-test `unittest` suite covering thresholding, bias flags, confidence labels, and skill gap severity.

## [1.1.0] - Conversational RAG

### Added
- Added multi-turn recruiter chat with session-based memory.
- Added context-aware follow-ups, filtering, and candidate comparisons.
- Added token-aware memory trimming and summarization.
- Added context drift detection.
- Added smart filter state tracking for active skills, experience filters, and previously viewed candidates.

## [1.0.0] - Core MVP

### Added
- Added resume PDF upload and parsing.
- Added semantic search using `all-mpnet-base-v2` embeddings.
- Added hybrid scoring: semantic similarity (60%) + keyword/skill match (40%).
- Added explainable AI with match breakdown and "Why this match?" reasons.
- Added radar chart visualization per candidate.
- Added CSV export of results.
- Added project history persistence via `localStorage`.
- Added dark/light theme toggle.
- Added cinematic landing animation.
