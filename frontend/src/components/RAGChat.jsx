import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';

// ---------------------------------------------------------------------------
// Safe markdown renderer — no dangerouslySetInnerHTML
// Renders **bold**, *italic*, and newlines without raw HTML injection.
// ---------------------------------------------------------------------------
const SafeMarkdown = ({ content }) => {
  if (!content) return null;

  // Split by double newline for paragraphs, single newline for line breaks
  const lines = content.split('\n');
  return (
    <span className="leading-relaxed">
      {lines.map((line, li) => {
        // Parse bold (**text**) and italic (*text*)
        const parts = [];
        let remaining = line;
        let key = 0;

        while (remaining.length > 0) {
          const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
          const italicMatch = remaining.match(/\*(.+?)\*/);

          // Pick the earliest match
          let match = null;
          let isBold = false;
          if (boldMatch && (!italicMatch || boldMatch.index <= italicMatch.index)) {
            match = boldMatch;
            isBold = true;
          } else if (italicMatch) {
            match = italicMatch;
          }

          if (!match) {
            parts.push(<span key={key++}>{remaining}</span>);
            break;
          }

          // Text before match
          if (match.index > 0) {
            parts.push(<span key={key++}>{remaining.slice(0, match.index)}</span>);
          }
          // Styled match
          if (isBold) {
            parts.push(<strong key={key++} className="font-semibold text-white">{match[1]}</strong>);
          } else {
            parts.push(<em key={key++} className="italic text-gray-300">{match[1]}</em>);
          }
          remaining = remaining.slice(match.index + match[0].length);
        }

        return (
          <span key={li}>
            {parts}
            {li < lines.length - 1 && <br />}
          </span>
        );
      })}
    </span>
  );
};

// ---------------------------------------------------------------------------
// Confidence badge
// ---------------------------------------------------------------------------
const ConfidenceBadge = ({ confidence }) => {
  if (!confidence) return null;
  const styles = {
    high:   'bg-emerald-500/15 text-emerald-400 border-emerald-500/25',
    medium: 'bg-amber-500/15 text-amber-400 border-amber-500/25',
    low:    'bg-red-500/15 text-red-400 border-red-500/25',
  };
  const icons = { high: '●', medium: '◐', low: '○' };
  const cls = styles[confidence] || styles.low;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[9px] font-semibold uppercase tracking-wider ${cls}`}>
      <span>{icons[confidence] || '○'}</span>
      {confidence}
    </span>
  );
};

// ---------------------------------------------------------------------------
// Insights panel
// ---------------------------------------------------------------------------
const InsightsPanel = ({ insights }) => {
  const [open, setOpen] = useState(false);
  // Only render when there is meaningful, non-trivial content
  if (!insights || insights.trim().length < 15) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-3 rounded-lg border border-primary-gold/15 bg-primary-gold/5 overflow-hidden"
    >
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-3 py-2 text-left"
      >
        <span className="flex items-center gap-2 text-[10px] uppercase tracking-widest font-bold text-primary-gold/80">
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          Recruiter Insight
        </span>
        <svg
          className={`w-3 h-3 text-primary-gold/60 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="px-3 pb-3"
          >
            <p className="text-[11px] text-gray-300 leading-relaxed">
              <SafeMarkdown content={insights} />
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// ---------------------------------------------------------------------------
// Drift notice toast (shows for 3 seconds on major context change)
// ---------------------------------------------------------------------------
const DriftToast = ({ notice, onDone }) => {
  useEffect(() => {
    if (!notice) return;
    const t = setTimeout(onDone, 3000);
    return () => clearTimeout(t);
  }, [notice, onDone]);

  if (!notice) return null;

  const isReset = notice === 'context_reset';
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className={`mx-4 mb-2 px-3 py-1.5 rounded-lg text-[10px] font-semibold flex items-center gap-2 border
        ${isReset
          ? 'bg-amber-500/10 border-amber-500/25 text-amber-400'
          : 'bg-blue-500/10 border-blue-500/25 text-blue-400'}`}
    >
      <svg className="w-3 h-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d={isReset
            ? "M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            : "M13 10V3L4 14h7v7l9-11h-7z"} />
      </svg>
      {isReset ? 'Context refreshed — previous filters were cleared.' : 'Context merged with previous topic.'}
    </motion.div>
  );
};

// ---------------------------------------------------------------------------
// Main RAGChat component
// ---------------------------------------------------------------------------
const RAGChat = ({ isOpen, onClose, initialMode = 'global', candidateId = null, candidateName = null }) => {
  const getWelcomeMessage = useCallback(() => ({
    role: 'ai',
    content: initialMode === 'specific'
      ? `I'm analyzing **${candidateName}**. How can I help you evaluate them for this role?`
      : "Hello! I'm your **RecruitDesk Intelligence** assistant. Ask me anything about the candidate pool or specific requirements.",
    timestamp: new Date(),
  }), [initialMode, candidateName]);

  const [query, setQuery]               = useState('');
  const [messages, setMessages]         = useState([getWelcomeMessage()]);
  const [isLoading, setIsLoading]       = useState(false);
  const [error, setError]               = useState(null);
  const [mode]                          = useState(initialMode);
  const [sessionId, setSessionId]       = useState(null);
  const [activeFilters, setActiveFilters] = useState({});
  const [driftNotice, setDriftNotice]   = useState(null);

  const messagesEndRef = useRef(null);
  const inputRef       = useRef(null);
  const API_URL        = 'http://localhost:8000';

  // ── LocalStorage restore ──────────────────────────────────────────────
  useEffect(() => {
    if (!isOpen) return;
    try {
      const saved = localStorage.getItem('recruitdesk_chat_v2');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.mode === initialMode && parsed.candidateId === candidateId) {
          if (parsed.messages?.length > 1) setMessages(parsed.messages);
          if (parsed.sessionId) setSessionId(parsed.sessionId);
          if (parsed.activeFilters) setActiveFilters(parsed.activeFilters);
        }
      }
    } catch (e) {
      console.error('LocalStorage decode error', e);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, initialMode, candidateId]);

  // ── LocalStorage sync ────────────────────────────────────────────────
  useEffect(() => {
    if (messages.length > 1) {
      localStorage.setItem('recruitdesk_chat_v2', JSON.stringify({
        sessionId, messages, activeFilters, mode, candidateId,
      }));
    }
  }, [messages, sessionId, activeFilters, mode, candidateId]);

  // ── Scroll to bottom ─────────────────────────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // ── Focus input on open ──────────────────────────────────────────────
  useEffect(() => {
    if (isOpen) setTimeout(() => inputRef.current?.focus(), 300);
  }, [isOpen]);

  // ── New Chat ─────────────────────────────────────────────────────────
  const handleNewChat = async () => {
    if (sessionId) {
      try { await axios.post(`${API_URL}/clear-chat`, { session_id: sessionId }); }
      catch (e) { console.error('Failed to clear backend session', e); }
    }
    setSessionId(null);
    setActiveFilters({});
    setDriftNotice(null);
    setMessages([getWelcomeMessage()]);
    localStorage.removeItem('recruitdesk_chat_v2');
  };

  // ── Suggestions ──────────────────────────────────────────────────────
  const suggestions = mode === 'specific'
    ? [
        `What are ${candidateName}'s top 3 skills?`,
        `Any red flags in ${candidateName}'s resume?`,
        `Compare ${candidateName} to the job requirements.`,
      ]
    : [
        'Summarize the best candidates for this role.',
        'Who has the most experience with Python and React?',
        'Compare the top 3 candidates for me.',
        'Are there any candidates with leadership experience?',
      ];

  // ── Send message ─────────────────────────────────────────────────────
  const handleSend = async (text = query) => {
    if (!text.trim() || isLoading) return;

    setMessages(prev => [...prev, { role: 'user', content: text, timestamp: new Date() }]);
    setQuery('');
    setIsLoading(true);
    setError(null);

    try {
      const { data } = await axios.post(`${API_URL}/rag-query`, {
        query: text,
        candidate_id: mode === 'specific' ? candidateId : null,
        session_id: sessionId,
      });

      // Update session state
      if (data.session_id && !sessionId) setSessionId(data.session_id);
      if (data.active_filters) setActiveFilters(data.active_filters);

      // Context drift notice — only surface "reset" events (major change)
      if (data.drift_notice === 'context_reset') {
        setDriftNotice('context_reset');
      }

      setMessages(prev => [...prev, {
        role:       'ai',
        content:    data.answer,
        sources:    data.top_candidates || [],
        insights:   data.insights || '',
        confidence: data.confidence,
        timestamp:  new Date(),
      }]);
    } catch (err) {
      console.error('RAG Query Error:', err);
      setError('Failed to get a response from AI. Please check your connection.');
    } finally {
      setIsLoading(false);
    }
  };

  // ── Active filter display helpers ─────────────────────────────────────
  const hasActiveFilters =
    (activeFilters?.skills?.length > 0) ||
    (activeFilters?.min_experience > 0);

  // ── Render ────────────────────────────────────────────────────────────
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, scale: 0.92, y: 80 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.92, y: 80 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          className="fixed bottom-24 right-6 w-[460px] max-w-[92vw] h-[660px] max-h-[82vh] z-50 flex flex-col glass-card border-primary-gold/20 shadow-[0_24px_60px_rgba(0,0,0,0.55)] overflow-hidden"
        >
          {/* ── Header ─────────────────────────────────────────────── */}
          <div className="p-4 border-b border-white/10 bg-gradient-to-r from-primary-gold/10 to-transparent shrink-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-gold to-amber-600 flex items-center justify-center shadow-lg">
                  <svg className="w-4 h-4 text-deep-bronze" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    RecruitDesk Intelligence
                  </h3>
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-[10px] text-gray-400 capitalize">{mode} Context Mode</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  id="rag-new-chat-btn"
                  onClick={handleNewChat}
                  className="text-[10px] px-2.5 py-1 bg-white/5 hover:bg-white/10 rounded-lg text-gray-300 transition-all duration-200 flex items-center gap-1.5 border border-white/5 hover:border-white/15"
                >
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M12 4v16m8-8H4" />
                  </svg>
                  New Chat
                </button>
                <button
                  id="rag-close-btn"
                  onClick={onClose}
                  className="text-gray-400 hover:text-white transition-colors ml-1 p-1 rounded-lg hover:bg-white/5"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Active context chips */}
            <AnimatePresence>
              {hasActiveFilters && (
                <motion.div
                  initial={{ opacity: 0, height: 0, marginTop: 0 }}
                  animate={{ opacity: 1, height: 'auto', marginTop: 10 }}
                  exit={{ opacity: 0, height: 0, marginTop: 0 }}
                  className="flex flex-wrap gap-1.5 items-center"
                >
                  <span className="text-[9px] text-gray-500 uppercase tracking-widest mr-1">
                    Active Context:
                  </span>
                  {activeFilters.skills?.map(s => (
                    <span key={s}
                      className="px-2 py-0.5 rounded-full bg-primary-gold/10 text-primary-gold text-[10px] border border-primary-gold/20 font-medium">
                      {s}
                    </span>
                  ))}
                  {activeFilters.min_experience > 0 && (
                    <span className="px-2 py-0.5 rounded-full bg-primary-gold/10 text-primary-gold text-[10px] border border-primary-gold/20 font-medium">
                      {activeFilters.min_experience}+ yrs
                    </span>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* ── Drift notice ────────────────────────────────────────── */}
          <AnimatePresence>
            {driftNotice && (
              <DriftToast notice={driftNotice} onDone={() => setDriftNotice(null)} />
            )}
          </AnimatePresence>

          {/* ── Messages area ───────────────────────────────────────── */}
          <div className="flex-1 overflow-y-auto p-4 space-y-5 scrollbar-thin">
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className="max-w-[86%]">

                  {/* AI avatar dot */}
                  {msg.role === 'ai' && (
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <div className="w-4 h-4 rounded-full bg-gradient-to-br from-primary-gold to-amber-600 flex items-center justify-center">
                        <span className="text-[6px] text-deep-bronze font-bold">AI</span>
                      </div>
                      <span className="text-[9px] text-gray-500">RecruitDesk AI</span>
                    </div>
                  )}

                  <div className={msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai'}>
                    <SafeMarkdown content={msg.content} />

                    {/* Source attribution cards */}
                    {msg.sources?.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-white/5 space-y-2">
                        <p className="text-[9px] uppercase font-bold text-gray-500 tracking-widest">
                          Sources & References
                        </p>
                        <div className="grid grid-cols-1 gap-1.5">
                          {msg.sources.map((src, si) => (
                            <div key={si}
                              className="bg-black/20 p-2 rounded-lg border border-white/5 flex items-center justify-between gap-2">
                              <div className="min-w-0">
                                <div className="text-xs font-semibold text-primary-gold truncate">
                                  {src.name}
                                </div>
                                <div className="flex gap-1 flex-wrap mt-0.5">
                                  {src.matched_skills?.slice(0, 3).map((s, i) => (
                                    <span key={i}
                                      className="text-[8px] bg-white/5 px-1.5 py-0.5 rounded text-gray-400">
                                      {s}
                                    </span>
                                  ))}
                                </div>
                              </div>
                              <div className="shrink-0 text-[10px] font-bold text-primary-gold/60 whitespace-nowrap">
                                {src.score != null ? `${(src.score * 100).toFixed(0)}% match` : '—'}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Insights panel */}
                    {msg.insights && <InsightsPanel insights={msg.insights} />}
                  </div>

                  {/* Timestamp + confidence */}
                  <div className={`flex items-center gap-2 mt-1 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <span className="text-[9px] text-gray-500">
                      {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    {msg.confidence && <ConfidenceBadge confidence={msg.confidence} />}
                  </div>
                </div>
              </div>
            ))}

            {/* Typing indicator */}
            {isLoading && (
              <div className="flex justify-start">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <div className="w-4 h-4 rounded-full bg-gradient-to-br from-primary-gold to-amber-600 flex items-center justify-center">
                    <span className="text-[6px] text-deep-bronze font-bold">AI</span>
                  </div>
                </div>
                <div className="chat-bubble-ai flex items-center gap-1 min-w-[60px] ml-2">
                  <span className="typing-dot w-1.5 h-1.5 bg-gray-400 rounded-full" />
                  <span className="typing-dot w-1.5 h-1.5 bg-gray-400 rounded-full" />
                  <span className="typing-dot w-1.5 h-1.5 bg-gray-400 rounded-full" />
                </div>
              </div>
            )}

            {/* Error state */}
            {error && (
              <div className="mx-1 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs text-center">
                {error}
                <button
                  onClick={() => {
                    const lastUser = [...messages].reverse().find(m => m.role === 'user');
                    if (lastUser) handleSend(lastUser.content);
                  }}
                  className="ml-2 underline hover:text-red-300 transition-colors"
                >
                  Retry
                </button>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* ── Input area ──────────────────────────────────────────── */}
          <div className="p-4 border-t border-white/10 bg-black/20 shrink-0">
            {/* Suggestions chips */}
            {!isLoading && messages.length < 5 && (
              <div className="flex gap-2 overflow-x-auto pb-3 no-scrollbar">
                {suggestions.map((s, i) => (
                  <button key={i} onClick={() => handleSend(s)} className="suggestion-chip">
                    {s}
                  </button>
                ))}
              </div>
            )}

            <div className="relative flex items-center">
              <input
                id="rag-chat-input"
                ref={inputRef}
                type="text"
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyPress={e => e.key === 'Enter' && handleSend()}
                placeholder={mode === 'specific' ? `Ask about ${candidateName}…` : 'Ask AI pool intelligence…'}
                className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-4 pr-12 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-primary-gold/50 focus:bg-white/8 transition-all"
                disabled={isLoading}
              />
              <button
                id="rag-send-btn"
                onClick={() => handleSend()}
                disabled={isLoading || !query.trim()}
                className="absolute right-2 p-2 text-primary-gold disabled:text-gray-600 transition-colors hover:text-amber-400"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                </svg>
              </button>
            </div>

            <p className="text-[9px] text-gray-600 text-center mt-2 tracking-wide">
              AI-generated · Based on your candidate database context
            </p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default RAGChat;
