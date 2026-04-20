import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';

/**
 * RAGChat Component
 * Intelligent recruitment assistant with Global and Specific candidate context modes.
 */
const RAGChat = ({ isOpen, onClose, initialMode = 'global', candidateId = null, candidateName = null }) => {
    const [query, setQuery] = useState('');
    const [messages, setMessages] = useState([
        {
            role: 'ai',
            content: initialMode === 'specific' 
                ? `I'm analyzing **${candidateName}**. How can I help you evaluate them for this role?`
                : "Hello! I'm your RecruitDesk Intelligence assistant. Ask me anything about the candidate pool or specific requirements.",
            timestamp: new Date()
        }
    ]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [mode, setMode] = useState(initialMode);
    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

    const API_URL = 'http://localhost:8000';

    const suggestions = mode === 'specific' 
        ? [
            `What are ${candidateName}'s top 3 skills?`,
            `Any red flags in ${candidateName}'s resume?`,
            `Compare ${candidateName} to the job requirements.`
          ]
        : [
            "Summarize the best candidates for this role.",
            "Who has the most experience with Python and React?",
            "Compare the top 3 candidates for me.",
            "Are there any candidates with leadership experience?"
          ];

    // Scroll to bottom when messages change
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isLoading]);

    // Focus input when opened
    useEffect(() => {
        if (isOpen) {
            setTimeout(() => inputRef.current?.focus(), 300);
        }
    }, [isOpen]);

    const handleSend = async (text = query) => {
        if (!text.trim() || isLoading) return;

        const userMessage = {
            role: 'user',
            content: text,
            timestamp: new Date()
        };

        setMessages(prev => [...prev, userMessage]);
        setQuery('');
        setIsLoading(true);
        setError(null);

        try {
            const response = await axios.post(`${API_URL}/rag-query`, {
                query: text,
                candidate_id: mode === 'specific' ? candidateId : null,
                filters: {} // Can be expanded for skill/exp filtering
            });

            const data = response.data;
            
            // Format AI message with source attribution
            const aiMessage = {
                role: 'ai',
                content: data.answer,
                sources: data.top_candidates || [],
                insights: data.insights,
                confidence: data.confidence,
                timestamp: new Date(),
                isStreaming: true // Used for typing effect
            };

            setMessages(prev => [...prev, aiMessage]);
        } catch (err) {
            console.error("RAG Query Error:", err);
            setError("Failed to get response from AI. Please check your connection.");
        } finally {
            setIsLoading(false);
        }
    };

    const handleSuggestionClick = (suggestion) => {
        handleSend(suggestion);
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0, scale: 0.9, y: 100 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.9, y: 100 }}
                    className="fixed bottom-24 right-6 w-[450px] max-w-[90vw] h-[650px] max-h-[80vh] z-50 flex flex-col glass-card border-primary-gold/20 shadow-[0_20px_50px_rgba(0,0,0,0.5)] overflow-hidden"
                >
                    {/* Header */}
                    <div className="p-4 border-b border-white/10 bg-gradient-to-r from-primary-gold/10 to-transparent flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-primary-gold flex items-center justify-center">
                                <svg className="w-5 h-5 text-deep-bronze" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                                </svg>
                            </div>
                            <div>
                                <h3 className="text-sm font-bold text-white uppercase tracking-wider">RecruitDesk Intelligence</h3>
                                <div className="flex items-center gap-1.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
                                    <span className="text-[10px] text-gray-400 capitalize">{mode} Context Mode</span>
                                </div>
                            </div>
                        </div>
                        <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    {/* Messages Area */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-thin">
                        {messages.map((msg, idx) => (
                            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className="max-w-[85%]">
                                    <div className={msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai'}>
                                        {msg.content}
                                        
                                        {/* Source Attribution Cards */}
                                        {msg.sources && msg.sources.length > 0 && (
                                            <div className="mt-4 pt-4 border-t border-white/5 space-y-2">
                                                <p className="text-[10px] uppercase font-bold text-gray-500 tracking-widest mb-2">Sources & References</p>
                                                <div className="grid grid-cols-1 gap-2">
                                                    {msg.sources.map((source, sIdx) => (
                                                        <div key={sIdx} className="bg-black/20 p-2 rounded-lg border border-white/5 flex items-center justify-between">
                                                            <div>
                                                                <div className="text-xs font-semibold text-primary-gold">{source.name}</div>
                                                                <div className="flex gap-1 flex-wrap mt-1">
                                                                    {source.matched_skills?.slice(0, 3).map((s, i) => (
                                                                        <span key={i} className="text-[8px] bg-white/5 px-1 rounded text-gray-400">{s}</span>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                            <div className="text-[10px] font-bold text-primary-gold/60">{(source.score * 100).toFixed(0)}% Match</div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                    <div className={`text-[9px] mt-1 text-gray-500 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
                                        {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </div>
                                </div>
                            </div>
                        ))}
                        
                        {isLoading && (
                            <div className="flex justify-start">
                                <div className="chat-bubble-ai flex items-center gap-1 min-w-[60px]">
                                    <span className="typing-dot w-1 h-1 bg-gray-400 rounded-full"></span>
                                    <span className="typing-dot w-1 h-1 bg-gray-400 rounded-full"></span>
                                    <span className="typing-dot w-1 h-1 bg-gray-400 rounded-full"></span>
                                </div>
                            </div>
                        )}
                        
                        {error && (
                            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs text-center">
                                {error}
                                <button onClick={() => handleSend(messages[messages.length-1].content)} className="ml-2 underline hover:text-red-300">Retry</button>
                            </div>
                        )}
                        
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Bottom Toolbar & Input */}
                    <div className="p-4 border-t border-white/10 bg-black/20">
                        {/* Dynamic Suggestions */}
                        {!isLoading && messages.length < 5 && (
                            <div className="flex gap-2 overflow-x-auto pb-3 no-scrollbar mb-1">
                                {suggestions.map((s, i) => (
                                    <button
                                        key={i}
                                        onClick={() => handleSuggestionClick(s)}
                                        className="suggestion-chip"
                                    >
                                        {s}
                                    </button>
                                ))}
                            </div>
                        )}

                        <div className="relative flex items-center">
                            <input
                                ref={inputRef}
                                type="text"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                                placeholder={mode === 'specific' ? `Ask about ${candidateName}...` : "Ask AI pool intelligence..."}
                                className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-4 pr-12 text-sm text-white focus:outline-none focus:border-primary-gold/50 transition-all"
                                disabled={isLoading}
                            />
                            <button
                                onClick={() => handleSend()}
                                disabled={isLoading || !query.trim()}
                                className="absolute right-2 p-2 text-primary-gold disabled:text-gray-600 transition-colors"
                            >
                                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                                </svg>
                            </button>
                        </div>
                        <p className="text-[9px] text-gray-500 text-center mt-2">AI-generated response based on candidate database context.</p>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
};

export default RAGChat;
