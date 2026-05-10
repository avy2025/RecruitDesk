import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import ResultCard from './ResultCard';
import RAGChat from './RAGChat';
import DecisionCard from './DecisionCard';

/**
 * Dashboard Component
 * Main application interface for job description input, resume upload, and results display
 */
const Dashboard = () => {
    const [jobDescription, setJobDescription] = useState('');
    const [resumes, setResumes] = useState([]);
    const [results, setResults] = useState([]);
    const [decisionResults, setDecisionResults] = useState([]);
    const [history, setHistory] = useState([]);
    const [projectName, setProjectName] = useState('New Project');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [dragActive, setDragActive] = useState(false);
    const [percentProgress, setPercentProgress] = useState(0);
    const [filterMinScore, setFilterMinScore] = useState(0);
    const [filterSkill, setFilterSkill] = useState('');
    const [sortBy, setSortBy] = useState('match'); // 'match', 'yoe'
    const [statusStage, setStatusStage] = useState(''); // 'Uploading...', 'Parsing...', 'Analyzing...'
    const [decisionLoading, setDecisionLoading] = useState(false);
    const [decisionError, setDecisionError] = useState('');
    const [activeResultsTab, setActiveResultsTab] = useState('ranked'); // 'ranked' | 'decision'
    const [autoOpenDecision, setAutoOpenDecision] = useState(true);
    const [isChatOpen, setIsChatOpen] = useState(false);
    const [chatMode, setChatMode] = useState('global'); // 'global', 'specific'
    const [chatCandidate, setChatCandidate] = useState({ id: null, name: null });
    const [decisionEngineActive, setDecisionEngineActive] = useState(false);
    const fileInputRef = useRef(null);

    const API_URL = 'http://localhost:8000';

    // Load history from localStorage
    useEffect(() => {
        const savedHistory = JSON.parse(localStorage.getItem('recruitdesk_history') || '[]');
        setHistory(savedHistory);
        const savedAutoDecision = localStorage.getItem('recruitdesk_auto_decision');
        if (savedAutoDecision !== null) {
            setAutoOpenDecision(savedAutoDecision === 'true');
        }

        // Dark mode check
        if (localStorage.getItem('recruitdesk_theme') === 'light') {
            document.documentElement.classList.add('light-mode');
        }
    }, []);

    useEffect(() => {
        const checkHealth = async () => {
            try {
                const response = await axios.get(`${API_URL}/health`);
                if (response?.data?.decision_engine === true) {
                    setDecisionEngineActive(true);
                }
            } catch (err) {
                // Fail silently as requested.
            }
        };

        checkHealth();
    }, []);

    const saveToHistory = (newResults) => {
        const project = {
            id: Date.now(),
            name: projectName || `Project ${new Date().toLocaleDateString()}`,
            job_description: jobDescription,
            results: newResults,
            date: new Date().toISOString()
        };
        const updatedHistory = [project, ...history].slice(0, 10);
        setHistory(updatedHistory);
        localStorage.setItem('recruitdesk_history', JSON.stringify(updatedHistory));
    };

    const loadFromHistory = (project) => {
        setJobDescription(project.job_description);
        setResults(project.results);
        setProjectName(project.name);
        setResumes([]); // Clear current uploads as results are loaded
    };
    const handleFileSelect = (files) => {
        const pdfFiles = Array.from(files).filter(file => 
            file.type === 'application/pdf' || 
            file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        );

        if (pdfFiles.length === 0) {
            setError('Please select PDF or DOCX files only');
            return;
        }

        if (resumes.length + pdfFiles.length > 10) {
            setError('Maximum 10 resumes allowed');
            return;
        }

        setResumes(prev => [...prev, ...pdfFiles]);
        setError('');
    };

    // Handle drag and drop
    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files);
        }
    };

    // Remove file from list
    const removeFile = (index) => {
        setResumes(prev => prev.filter((_, i) => i !== index));
    };

    // Analyze resumes
    const handleAnalyze = async () => {
        if (!jobDescription.trim()) {
            setError('Please enter a job description');
            return;
        }

        if (resumes.length === 0) {
            setError('Please upload at least one resume');
            return;
        }

        setLoading(true);
        setError('');
        setResults([]);
        setDecisionResults([]);
        setDecisionError('');
        setActiveResultsTab('ranked');
        setPercentProgress(10); // Start progress

        try {
            const formData = new FormData();
            formData.append('job_description', jobDescription);

            resumes.forEach(resume => {
                formData.append('resumes', resume);
            });

            setStatusStage('Uploading files...');
            setPercentProgress(20);

            const response = await axios.post(`${API_URL}/rank-resumes`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
                onUploadProgress: (progressEvent) => {
                    const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                    if (percentCompleted < 100) {
                        setPercentProgress(20 + (percentCompleted * 0.3)); // Up to 50%
                    } else {
                        setStatusStage('AI is analyzing resumes...');
                        setPercentProgress(60);
                    }
                }
            });

            if (response.data.success) {
                setStatusStage('Finalizing results...');
                setPercentProgress(90);
                await new Promise((resolve) => setTimeout(resolve, 300));
                setResults(response.data.ranked_resumes);
                saveToHistory(response.data.ranked_resumes);
                setPercentProgress(100);

                if (autoOpenDecision) {
                    await fetchDecisionResults(true);
                }
            }
        } catch (err) {
            console.error('Error analyzing resumes:', err);
            setError(err.response?.data?.detail || 'Failed to analyze resumes. Please ensure the backend is running.');
        } finally {
            setTimeout(() => {
                setLoading(false);
                setPercentProgress(0);
                setStatusStage('');
            }, 800);
        }
    };

    // CSV Export Logic
    const handleExportCSV = () => {
        if (results.length === 0) return;

        const headers = ["Rank", "Filename", "Match %", "YoE", "Top Strengths", "Matched Skills", "Missing Skills"];
        const rows = results.map((r, i) => [
            i + 1,
            r.filename,
            `${r.match_percentage}%`,
            r.years_of_experience,
            (r.top_strengths || []).join("; "),
            (r.match_details.matched_skills || []).join("; "),
            (r.match_details.missing_skills || []).join("; ")
        ]);

        const csvContent = [
            headers.join(","),
            ...rows.map(row => row.map(cell => `"${cell}"`).join(","))
        ].join("\n");

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", `recruitdesk_results_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const clearAllResumes = () => {
        setResumes([]);
        setResults([]);
        setDecisionResults([]);
        setDecisionError('');
        setActiveResultsTab('ranked');
        setError('');
        setProjectName('New Project');
    };

    const mapDecisionPayload = (item) => ({
        filename: item.filename,
        composite_score: item.composite_score,
        decision: item.decision,
        confidence: item.confidence,
        confidence_label: item.confidence_label,
        score_breakdown: {
            semantic_score: item.semantic_score ?? 0,
            keyword_score: item.keyword_skill_score ?? 0,
            experience_score: item.experience_fit_score ?? 0,
            education_score: item.education_match_score ?? 0,
            completeness_score: item.resume_completeness_score ?? 0,
        },
        matched_skills: item.matched_skills ?? [],
        skill_gaps: (item.skill_gap_analysis ?? []).map((gap) => ({
            skill: gap.skill,
            priority: gap.severity,
            suggestion: gap.suggestion,
        })),
        reasons: item.reasons ?? [],
        bias_flags: item.bias_warnings ?? [],
        uncertainty_notes: item.uncertainty_notes ?? [],
    });

    const fetchDecisionResults = async (switchTabOnSuccess = false) => {
        if (!jobDescription.trim() || resumes.length === 0) {
            setDecisionError('Please provide a job description and upload resumes before using Decision Engine.');
            return;
        }

        setDecisionLoading(true);
        setDecisionError('');
        try {
            const formData = new FormData();
            formData.append('job_description', jobDescription);
            resumes.forEach((resume) => formData.append('resumes', resume));

            const response = await axios.post(`${API_URL}/hiring-decision`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });

            const sorted = (response.data?.decisions ?? [])
                .map(mapDecisionPayload)
                .sort((a, b) => b.composite_score - a.composite_score);
            setDecisionResults(sorted);
            if (switchTabOnSuccess) {
                setActiveResultsTab('decision');
            }
        } catch (err) {
            console.error('Error generating hiring decisions:', err);
            setDecisionError(err.response?.data?.detail || 'Failed to generate hiring decisions. Please try again.');
        } finally {
            setDecisionLoading(false);
        }
    };

    const handleResultsTabChange = (tab) => {
        setActiveResultsTab(tab);
        if (tab === 'decision' && decisionResults.length === 0 && !decisionLoading) {
            fetchDecisionResults();
        }
    };

    const handleGenerateQuestions = async (data) => {
        try {
            const response = await axios.post(`${API_URL}/generate-questions`, data);
            return response.data.questions;
        } catch (err) {
            console.error("API error generating questions:", err);
            throw err;
        }
    };

    const toggleTheme = () => {
        const isLight = document.documentElement.classList.toggle('light-mode');
        localStorage.setItem('recruitdesk_theme', isLight ? 'light' : 'dark');
    };

    // Filter and Sort results
    const filteredResults = results
        .filter(r => r.match_percentage >= filterMinScore)
        .filter(r => !filterSkill || r.match_details.matched_skills.some(s => s.toLowerCase().includes(filterSkill.toLowerCase())))
        .sort((a, b) => {
            if (sortBy === 'match') return b.match_percentage - a.match_percentage;
            if (sortBy === 'yoe') return b.years_of_experience - a.years_of_experience;
            return 0;
        });

    return (
        <div className="min-h-screen bg-transparent">
            {/* Header */}
            <motion.header
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="sticky top-0 z-40 backdrop-blur-md bg-earth-dark bg-opacity-60 border-b border-earth-cream border-opacity-10"
            >
                <div className="container mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <img src="/logo.png" alt="RecruitDesk AI" className="w-12 h-12 object-contain" />
                        <div>
                            <h1 className="text-2xl font-bold text-white">RecruitDesk AI</h1>
                            <p className="text-sm text-gray-400">AI-Powered Resume Intelligence</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-4">
                        {decisionEngineActive && (
                            <span className="inline-flex items-center rounded-full border border-green-400/30 bg-green-500/15 px-3 py-1 text-xs font-semibold text-green-300">
                                Phase 6 · Decision Engine Active
                            </span>
                        )}
                        <button
                            onClick={toggleTheme}
                            className="p-2 rounded-full hover:bg-white hover:bg-opacity-10 transition-all text-white"
                        >
                            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M16.243 16.243l.707.707M7.757 7.757l.707.707M14 12a2 2 0 11-4 0 2 2 0 014 0z" />
                            </svg>
                        </button>
                        <button
                            onClick={() => { setChatMode('global'); setIsChatOpen(true); }}
                            className="bg-primary-gold/10 hover:bg-primary-gold/20 text-primary-gold px-4 py-2 rounded-lg text-sm font-bold border border-primary-gold/30 transition-all flex items-center gap-2"
                        >
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                            AI Insights
                        </button>
                    </div>
                </div>
            </motion.header>

            {/* Main Content */}
            <div className="container mx-auto px-6 py-12 max-w-6xl">
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
                    {/* Sidebar / History */}
                    <motion.aside
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="lg:col-span-1"
                    >
                        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <svg className="w-5 h-5 text-primary-topaz" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            Recent Projects
                        </h3>
                        <div className="space-y-3">
                            {history.length > 0 ? history.map((proj) => (
                                <button
                                    key={proj.id}
                                    onClick={() => loadFromHistory(proj)}
                                    className="w-full text-left glass-card p-3 hover:bg-opacity-10 transition-all border-none"
                                >
                                    <div className="text-sm font-medium text-white truncate">{proj.name}</div>
                                    <div className="text-[10px] text-gray-400">{new Date(proj.date).toLocaleDateString()}</div>
                                </button>
                            )) : (
                                <p className="text-sm text-gray-500 italic">No previous projects found.</p>
                            )}
                        </div>
                    </motion.aside>

                    <div className="lg:col-span-3">
                        {/* Job Description Section */}
                        <motion.section
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.6, delay: 0.1 }}
                            className="mb-8"
                        >
                            <div className="flex justify-between items-center mb-4">
                                <div className="w-1/2"></div>
                                <input
                                    type="text"
                                    value={projectName}
                                    onChange={(e) => setProjectName(e.target.value)}
                                    className="bg-transparent border-b border-earth-cream border-opacity-20 text-earth-cream text-lg font-medium focus:outline-none focus:border-earth-tan pb-1"
                                    placeholder="Enter project name..."
                                />
                            </div>

                            {/* RAG Quick Action Bar */}
                            <div className="flex gap-4 mb-6">
                                <button
                                    onClick={() => { setChatMode('global'); setIsChatOpen(true); }}
                                    className="flex-1 glass-card p-4 flex items-center justify-between group hover:border-primary-gold/40 transition-all"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 rounded-full bg-primary-gold/10 flex items-center justify-center text-primary-gold group-hover:scale-110 transition-transform">
                                            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                            </svg>
                                        </div>
                                        <div className="text-left">
                                            <div className="text-sm font-bold text-white uppercase tracking-tight">AI Talent Intelligence</div>
                                            <div className="text-[10px] text-gray-500">Ask patterns, comparisons, or summaries</div>
                                        </div>
                                    </div>
                                    <div className="text-primary-gold opacity-0 group-hover:opacity-100 transition-opacity">
                                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                        </svg>
                                    </div>
                                </button>
                            </div>

                            <h2 className="text-sm text-gray-400 mb-2">Job Description</h2>
                            <textarea
                                value={jobDescription}
                                onChange={(e) => setJobDescription(e.target.value)}
                                placeholder="Paste the job description here..."
                                className="input-field w-full min-h-[200px] resize-y"
                                rows={8}
                            />
                        </motion.section>

                        {/* Resume Upload Section */}
                        <motion.section
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.6, delay: 0.2 }}
                            className="mb-8"
                        >
                            <h2 className="text-2xl font-semibold text-white mb-4">Upload Resumes</h2>

                            {/* Drag and Drop Zone */}
                            <div
                                onDragEnter={handleDrag}
                                onDragLeave={handleDrag}
                                onDragOver={handleDrag}
                                onDrop={handleDrop}
                                onClick={() => fileInputRef.current?.click()}
                                className={`glass-card p-12 border-2 border-dashed transition-all duration-300 cursor-pointer
                ${dragActive
                                        ? 'border-primary-topaz bg-primary-topaz bg-opacity-10'
                                        : 'border-white border-opacity-20 hover:border-primary-topaz hover:bg-opacity-10'
                                    } text-topaz-cream`}
                            >
                                <div className="text-center">
                                    <svg
                                        className="mx-auto h-16 w-16 text-primary-topaz mb-4"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        stroke="currentColor"
                                    >
                                        <path
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            strokeWidth={2}
                                            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                                        />
                                    </svg>
                                    <p className="text-lg text-white mb-2">
                                        Drag and drop PDF or DOCX resumes here, or click to browse
                                    </p>
                                    <p className="text-sm text-gray-400">Maximum 10 files</p>
                                </div>
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    multiple
                                    accept=".pdf,.docx"
                                    onChange={(e) => handleFileSelect(e.target.files)}
                                    className="hidden"
                                />
                            </div>

                            {/* File List */}
                            {resumes.length > 0 && (
                                <div className="mt-6 space-y-2">
                                    <div className="flex justify-between items-center mb-3">
                                        <h3 className="text-lg font-semibold text-white">
                                            Uploaded Files ({resumes.length}/10)
                                        </h3>
                                        <button
                                            onClick={clearAllResumes}
                                            className="text-xs text-red-400 hover:text-red-300 flex items-center gap-1 transition-colors"
                                        >
                                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                            </svg>
                                            Clear All
                                        </button>
                                    </div>
                                    {resumes.map((file, index) => (
                                        <motion.div
                                            key={index}
                                            initial={{ opacity: 0, x: -20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ duration: 0.3, delay: index * 0.05 }}
                                            className="glass-card p-4 flex items-center justify-between"
                                        >
                                            <div className="flex items-center gap-3">
                                                <svg
                                                    className={`w-6 h-6 ${file.name.toLowerCase().endsWith('.docx') ? 'text-blue-400' : 'text-primary-green'}`}
                                                    fill="none"
                                                    viewBox="0 0 24 24"
                                                    stroke="currentColor"
                                                >
                                                    <path
                                                        strokeLinecap="round"
                                                        strokeLinejoin="round"
                                                        strokeWidth={2}
                                                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                                                    />
                                                </svg>
                                                <span className="text-white truncate max-w-md">{file.name}</span>
                                            </div>
                                            <button
                                                onClick={() => removeFile(index)}
                                                className="text-red-400 hover:text-red-300 transition-colors"
                                            >
                                                <svg
                                                    className="w-5 h-5"
                                                    fill="none"
                                                    viewBox="0 0 24 24"
                                                    stroke="currentColor"
                                                >
                                                    <path
                                                        strokeLinecap="round"
                                                        strokeLinejoin="round"
                                                        strokeWidth={2}
                                                        d="M6 18L18 6M6 6l12 12"
                                                    />
                                                </svg>
                                            </button>
                                        </motion.div>
                                    ))}
                                </div>
                            )}
                        </motion.section>

                        {/* Error Message */}
                        {error && (
                            <motion.div
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="glass-card p-4 mb-6 border-l-4 border-red-500 bg-red-500 bg-opacity-10"
                            >
                                <p className="text-red-300">{error}</p>
                            </motion.div>
                        )}

                        {/* Analyze Button */}
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.6, delay: 0.3 }}
                            className="flex flex-col items-center mb-12"
                        >
                            {loading && percentProgress > 0 && (
                                <div className="w-64 mb-4">
                                    <div className="flex justify-between text-xs text-gray-400 mb-1">
                                        <span>{statusStage}</span>
                                        <span>{Math.round(percentProgress)}%</span>
                                    </div>
                                    <div className="w-full bg-white bg-opacity-10 rounded-full h-1.5 overflow-hidden">
                                        <motion.div
                                            className="h-full bg-primary-topaz"
                                            initial={{ width: 0 }}
                                            animate={{ width: `${percentProgress}%` }}
                                        />
                                    </div>
                                </div>
                            )}
                            <button
                                onClick={handleAnalyze}
                                disabled={loading}
                                className="glow-button text-xl relative overflow-hidden group"
                            >
                                {loading ? (
                                    <div className="flex items-center gap-3">
                                        <svg className="animate-spin h-6 w-6" viewBox="0 0 24 24">
                                            <circle
                                                className="opacity-25"
                                                cx="12"
                                                cy="12"
                                                r="10"
                                                stroke="currentColor"
                                                strokeWidth="4"
                                                fill="none"
                                            />
                                            <path
                                                className="opacity-75"
                                                fill="currentColor"
                                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                            />
                                        </svg>
                                        <span>Processing...</span>
                                    </div>
                                ) : (
                                    'Analyze Candidates'
                                )}
                            </button>
                            <label className="mt-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-gray-400 backdrop-blur-sm">
                                <input
                                    type="checkbox"
                                    checked={autoOpenDecision}
                                    onChange={(e) => {
                                        const nextValue = e.target.checked;
                                        setAutoOpenDecision(nextValue);
                                        localStorage.setItem('recruitdesk_auto_decision', String(nextValue));
                                    }}
                                    className="h-3.5 w-3.5 accent-primary-gold"
                                />
                                Auto-open Decision Engine after analysis
                            </label>
                        </motion.div>

                        {/* Results Section */}
                        {results.length > 0 && (
                            <motion.section
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ duration: 0.6 }}
                            >
                                <div className="mb-5 inline-flex rounded-xl border border-white/10 bg-white/5 p-1">
                                    <button
                                        onClick={() => handleResultsTabChange('ranked')}
                                        className={`rounded-lg px-4 py-2 text-sm font-semibold transition-all ${activeResultsTab === 'ranked' ? 'bg-primary-topaz/20 text-primary-topaz border border-primary-topaz/30' : 'text-gray-300 hover:text-white'}`}
                                    >
                                        Ranked Results
                                    </button>
                                    <button
                                        onClick={() => handleResultsTabChange('decision')}
                                        className={`rounded-lg px-4 py-2 text-sm font-semibold transition-all ${activeResultsTab === 'decision' ? 'bg-primary-gold/20 text-primary-gold border border-primary-gold/30' : 'text-gray-300 hover:text-white'}`}
                                    >
                                        Decision Engine
                                    </button>
                                </div>

                                {activeResultsTab === 'ranked' && (
                                    <>
                                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
                                    <div className="flex items-center gap-4">
                                        <h2 className="text-3xl font-bold text-white">
                                            Ranked Results
                                        </h2>
                                        <button
                                            onClick={handleExportCSV}
                                            className="bg-primary-topaz bg-opacity-10 text-primary-topaz border border-primary-topaz border-opacity-20 px-3 py-1 rounded-md text-xs font-semibold hover:bg-opacity-20 transition-all flex items-center gap-2"
                                        >
                                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="file:///4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                            </svg>
                                            Export CSV
                                        </button>
                                    </div>

                                    {/* Filtering Controls */}
                                    <div className="flex flex-wrap items-center gap-4 bg-white bg-opacity-5 p-4 rounded-xl border border-white border-opacity-10">
                                        <div className="flex flex-col gap-1">
                                            <label className="text-xs text-gray-400">Min Score: {filterMinScore}%</label>
                                            <input
                                                type="range"
                                                min="0" max="100"
                                                value={filterMinScore}
                                                onChange={(e) => setFilterMinScore(parseInt(e.target.value))}
                                                className="w-32 h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-topaz"
                                            />
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <label className="text-xs text-gray-400">Skill Filter</label>
                                            <input
                                                type="text"
                                                placeholder="JS, React..."
                                                value={filterSkill}
                                                onChange={(e) => setFilterSkill(e.target.value)}
                                                className="bg-dark-bg border border-white border-opacity-10 text-xs px-2 py-1 rounded-md text-white focus:outline-none focus:border-primary-topaz"
                                            />
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <label className="text-xs text-gray-400">Sort By</label>
                                            <select
                                                value={sortBy}
                                                onChange={(e) => setSortBy(e.target.value)}
                                                className="bg-dark-bg border border-white border-opacity-10 text-xs px-2 py-1 rounded-md text-white focus:outline-none"
                                            >
                                                <option value="match">Highest Match</option>
                                                <option value="yoe">Years of Exp</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>

                                {filteredResults.length > 0 ? (
                                    <div className="space-y-4">
                                        {filteredResults.map((result, index) => (
                                            <ResultCard
                                                key={index}
                                                candidate_id={result.candidate_id}
                                                filename={result.filename}
                                                matchPercentage={result.match_percentage}
                                                matchDetails={result.match_details}
                                                summary={result.summary}
                                                yoe={result.years_of_experience}
                                                topStrengths={result.top_strengths}
                                                jobDescription={jobDescription}
                                                _internal={result._internal}
                                                onGenerateQuestions={handleGenerateQuestions}
                                                onOpenChat={(id, name) => {
                                                    setChatCandidate({ id, name });
                                                    setChatMode('specific');
                                                    setIsChatOpen(true);
                                                }}
                                                index={index}
                                            />
                                        ))}
                                    </div>
                                ) : (
                                    <div className="text-center py-20 glass-card">
                                        <p className="text-gray-400 text-lg">No candidates match your current filters.</p>
                                        <button
                                            onClick={() => { setFilterMinScore(0); setFilterSkill(''); }}
                                            className="text-primary-blue mt-2 hover:underline"
                                        >
                                            Reset Filters
                                        </button>
                                    </div>
                                )}
                                    </>
                                )}

                                {activeResultsTab === 'decision' && (
                                    <div className="space-y-4">
                                        <div className="flex items-center justify-between">
                                            <h2 className="text-3xl font-bold text-white">Hiring Decisions</h2>
                                            <button
                                                onClick={fetchDecisionResults}
                                                disabled={decisionLoading}
                                                className="bg-primary-gold/10 text-primary-gold border border-primary-gold/25 px-3 py-1 rounded-md text-xs font-semibold hover:bg-primary-gold/20 transition-all disabled:opacity-60"
                                            >
                                                Refresh Decisions
                                            </button>
                                        </div>

                                        {decisionLoading && (
                                            <div className="glass-card p-8 flex items-center justify-center gap-3">
                                                <svg className="animate-spin h-6 w-6 text-primary-gold" viewBox="0 0 24 24">
                                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.372 0 0 5.372 0 12h4z" />
                                                </svg>
                                                <span className="text-sm text-gray-300">Running hiring decision engine...</span>
                                            </div>
                                        )}

                                        {decisionError && !decisionLoading && (
                                            <div className="glass-card p-4 border-l-4 border-red-500 bg-red-500/10">
                                                <p className="text-red-300 text-sm">{decisionError}</p>
                                            </div>
                                        )}

                                        {!decisionLoading && !decisionError && decisionResults.length > 0 && (
                                            <div className="space-y-4">
                                                {decisionResults.map((item, idx) => (
                                                    <DecisionCard key={`${item.filename}-${idx}`} decisionResult={item} />
                                                ))}
                                            </div>
                                        )}

                                        {!decisionLoading && !decisionError && decisionResults.length === 0 && (
                                            <div className="glass-card p-8 text-center">
                                                <p className="text-gray-400 text-sm">No hiring decisions available yet.</p>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </motion.section>
                        )}
                    </div>
                </div>
            </div>

            {/* RAG Chat Component */}
            <RAGChat 
                isOpen={isChatOpen} 
                onClose={() => setIsChatOpen(false)}
                initialMode={chatMode}
                candidateId={chatCandidate.id}
                candidateName={chatCandidate.name}
            />

            {/* Floating Action Button */}
            <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={() => { setChatMode('global'); setIsChatOpen(!isChatOpen); }}
                className="fixed bottom-6 right-6 w-14 h-14 bg-primary-gold rounded-full shadow-[0_10px_30px_rgba(230,165,32,0.4)] flex items-center justify-center z-50 text-deep-bronze"
            >
                {isChatOpen ? (
                    <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                ) : (
                    <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                    </svg>
                )}
            </motion.button>
        </div>
    );
};

export default Dashboard;
