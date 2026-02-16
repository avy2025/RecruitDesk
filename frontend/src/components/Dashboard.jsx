import { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import ResultCard from './ResultCard';

/**
 * Dashboard Component
 * Main application interface for job description input, resume upload, and results display
 */
const Dashboard = () => {
    const [jobDescription, setJobDescription] = useState('');
    const [resumes, setResumes] = useState([]);
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [dragActive, setDragActive] = useState(false);
    const fileInputRef = useRef(null);

    const API_URL = 'http://localhost:8000';

    // Handle file selection
    const handleFileSelect = (files) => {
        const pdfFiles = Array.from(files).filter(file => file.type === 'application/pdf');

        if (pdfFiles.length === 0) {
            setError('Please select PDF files only');
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

        try {
            const formData = new FormData();
            formData.append('job_description', jobDescription);

            resumes.forEach(resume => {
                formData.append('resumes', resume);
            });

            const response = await axios.post(`${API_URL}/rank-resumes`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            if (response.data.success) {
                setResults(response.data.ranked_resumes);
            }
        } catch (err) {
            console.error('Error analyzing resumes:', err);
            setError(err.response?.data?.detail || 'Failed to analyze resumes. Please ensure the backend is running.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-dark-bg via-[#0f1535] to-dark-card">
            {/* Header */}
            <motion.header
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="sticky top-0 z-40 backdrop-blur-lg bg-dark-bg bg-opacity-80 border-b border-white border-opacity-10"
            >
                <div className="container mx-auto px-6 py-4 flex items-center gap-4">
                    <img src="/logo.png" alt="RecruitDesk AI" className="w-12 h-12 object-contain" />
                    <div>
                        <h1 className="text-2xl font-bold text-white">RecruitDesk AI</h1>
                        <p className="text-sm text-gray-400">AI-Powered Resume Intelligence</p>
                    </div>
                </div>
            </motion.header>

            {/* Main Content */}
            <div className="container mx-auto px-6 py-12 max-w-6xl">
                {/* Job Description Section */}
                <motion.section
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.1 }}
                    className="mb-8"
                >
                    <h2 className="text-2xl font-semibold text-white mb-4">Job Description</h2>
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
                                ? 'border-primary-blue bg-primary-blue bg-opacity-10'
                                : 'border-white border-opacity-20 hover:border-primary-blue hover:bg-opacity-10'
                            }`}
                    >
                        <div className="text-center">
                            <svg
                                className="mx-auto h-16 w-16 text-primary-blue mb-4"
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
                                Drag and drop PDF resumes here, or click to browse
                            </p>
                            <p className="text-sm text-gray-400">Maximum 10 files</p>
                        </div>
                        <input
                            ref={fileInputRef}
                            type="file"
                            multiple
                            accept=".pdf"
                            onChange={(e) => handleFileSelect(e.target.files)}
                            className="hidden"
                        />
                    </div>

                    {/* File List */}
                    {resumes.length > 0 && (
                        <div className="mt-6 space-y-2">
                            <h3 className="text-lg font-semibold text-white mb-3">
                                Uploaded Files ({resumes.length}/10)
                            </h3>
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
                                            className="w-6 h-6 text-primary-green"
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
                    className="flex justify-center mb-12"
                >
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
                                <span>Analyzing...</span>
                            </div>
                        ) : (
                            'Analyze Candidates'
                        )}
                    </button>
                </motion.div>

                {/* Results Section */}
                {results.length > 0 && (
                    <motion.section
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.6 }}
                    >
                        <h2 className="text-3xl font-bold text-white mb-6">
                            Ranked Results
                        </h2>
                        <div className="space-y-4">
                            {results.map((result, index) => (
                                <ResultCard
                                    key={index}
                                    filename={result.filename}
                                    matchPercentage={result.match_percentage}
                                    matchDetails={result.match_details}
                                    index={index}
                                />
                            ))}
                        </div>
                    </motion.section>
                )}
            </div>
        </div>
    );
};

export default Dashboard;
