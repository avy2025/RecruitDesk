import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';

/**
 * ResultCard Component
 * Displays individual resume ranking result with glassmorphism design and AI insights
 */
const ResultCard = ({ filename, matchPercentage, matchDetails, index }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    // Color coding based on score
    const getScoreColor = (score) => {
        if (score >= 80) return "text-green-400";
        if (score >= 60) return "text-yellow-400";
        return "text-red-400";
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: index * 0.1 }}
            className="glass-card-hover p-6 mb-4 cursor-pointer transition-all duration-300"
            onClick={() => setIsExpanded(!isExpanded)}
        >
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                {/* File info */}
                <div className="flex-1">
                    <h3 className="text-lg font-semibold text-white mb-1 truncate">
                        {filename}
                    </h3>
                    <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-400">Resume Analysis</span>
                        {isExpanded ? (
                            <span className="text-xs text-primary-blue bg-primary-blue bg-opacity-10 px-2 py-0.5 rounded-full">Expanded</span>
                        ) : (
                            <span className="text-xs text-gray-500">Click to expand</span>
                        )}
                    </div>
                </div>

                {/* Match percentage */}
                <div className="flex items-center gap-6">
                    <div className="text-right">
                        <div className={`text-4xl font-bold bg-gradient-to-r from-primary-blue to-primary-green bg-clip-text text-transparent`}>
                            {matchPercentage}%
                        </div>
                        <div className="text-xs text-gray-400 mt-1">Match Score</div>
                    </div>
                </div>
            </div>

            {/* Progress bar */}
            <div className="mt-4 w-full bg-white bg-opacity-10 rounded-full h-3 overflow-hidden">
                <motion.div
                    className="h-full rounded-full bg-gradient-to-r from-primary-blue to-primary-green"
                    initial={{ width: 0 }}
                    animate={{ width: `${matchPercentage}%` }}
                    transition={{ duration: 1, delay: index * 0.1 + 0.3, ease: 'easeOut' }}
                />
            </div>

            {/* Expanded Details */}
            <AnimatePresence>
                {isExpanded && matchDetails && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.3 }}
                        className="overflow-hidden mt-4 pt-4 border-t border-white border-opacity-10"
                    >
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Scores Breakdown */}
                            <div>
                                <h4 className="text-sm font-semibold text-gray-300 mb-2">Score Breakdown</h4>
                                <div className="space-y-2">
                                    <div className="flex justify-between text-sm">
                                        <span className="text-gray-400">Semantic Match</span>
                                        <span className="text-white">{matchDetails.semantic_score}%</span>
                                    </div>
                                    <div className="w-full bg-white bg-opacity-5 rounded-full h-1.5">
                                        <div
                                            className="h-full rounded-full bg-purple-500"
                                            style={{ width: `${matchDetails.semantic_score}%` }}
                                        />
                                    </div>

                                    <div className="flex justify-between text-sm mt-2">
                                        <span className="text-gray-400">Keyword & Skills</span>
                                        <span className="text-white">{matchDetails.keyword_score}%</span>
                                    </div>
                                    <div className="w-full bg-white bg-opacity-5 rounded-full h-1.5">
                                        <div
                                            className="h-full rounded-full bg-orange-500"
                                            style={{ width: `${matchDetails.keyword_score}%` }}
                                        />
                                    </div>
                                </div>
                            </div>

                            {/* Match Reasons */}
                            <div>
                                <h4 className="text-sm font-semibold text-gray-300 mb-2">Why this match?</h4>
                                <ul className="space-y-1">
                                    {matchDetails.match_reasons && matchDetails.match_reasons.map((reason, i) => (
                                        <li key={i} className="text-sm text-gray-400 flex items-start gap-2">
                                            <span className="text-primary-green mt-1">✓</span>
                                            {reason}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>

                        {/* Matched Skills Badges */}
                        {matchDetails.matched_skills && matchDetails.matched_skills.length > 0 && (
                            <div className="mt-4">
                                <h4 className="text-sm font-semibold text-gray-300 mb-2">Matched Skills</h4>
                                <div className="flex flex-wrap gap-2">
                                    {matchDetails.matched_skills.map((skill, i) => (
                                        <span key={i} className="text-xs px-2 py-1 rounded-md bg-green-500 bg-opacity-20 text-green-300 border border-green-500 border-opacity-30">
                                            {skill}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Missing Skills Badges (if any) */}
                        {matchDetails.missing_skills && matchDetails.missing_skills.length > 0 && (
                            <div className="mt-4">
                                <h4 className="text-sm font-semibold text-gray-300 mb-2">Missing Skills</h4>
                                <div className="flex flex-wrap gap-2">
                                    {matchDetails.missing_skills.map((skill, i) => (
                                        <span key={i} className="text-xs px-2 py-1 rounded-md bg-red-500 bg-opacity-20 text-red-300 border border-red-500 border-opacity-30">
                                            {skill}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
};

export default ResultCard;
