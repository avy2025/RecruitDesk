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
            <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                {/* File info */}
                <div className="flex-1">
                    <h3 className="text-lg font-semibold text-white mb-1 truncate">
                        {filename}
                    </h3>
                    <div className="flex items-center gap-2 mb-3">
                        <span className="text-sm text-gray-400">Education & Experience Analysis</span>
                        {isExpanded ? (
                            <span className="text-xs text-primary-blue bg-primary-blue bg-opacity-10 px-2 py-0.5 rounded-full">Expanded Results</span>
                        ) : (
                            <span className="text-xs text-gray-500 italic">Click for deep insights</span>
                        )}
                    </div>

                    {/* Candidate Summary */}
                    <div className="bg-white bg-opacity-5 p-3 rounded-lg border border-white border-opacity-5 mb-2">
                        <p className="text-sm text-gray-300 leading-relaxed">
                            <span className="text-primary-blue font-semibold">Summary:</span> {matchDetails.summary || `Candidate with ${matchDetails.years_of_experience || 0}+ years of experience and matches across key requirement sections.`}
                        </p>
                    </div>
                </div>

                {/* Match percentage */}
                <div className="flex items-center gap-6">
                    <div className="text-right">
                        <div className={`text-4xl font-bold bg-gradient-to-r from-primary-blue to-primary-green bg-clip-text text-transparent`}>
                            {matchPercentage}%
                        </div>
                        <div className="text-xs text-gray-400 mt-1 uppercase tracking-wider">Match Score</div>
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
                        className="overflow-hidden mt-6 pt-6 border-t border-white border-opacity-10"
                    >
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                            {/* Detailed Scores Breakdown */}
                            <div className="md:col-span-1">
                                <h4 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                                    <span className="w-1.5 h-1.5 bg-primary-blue rounded-full"></span>
                                    Section-Wise Analysis
                                </h4>
                                <div className="space-y-4">
                                    {Object.entries(matchDetails.section_breakdown || {}).map(([section, score]) => (
                                        <div key={section}>
                                            <div className="flex justify-between text-xs mb-1">
                                                <span className="text-gray-400 capitalize">{section}</span>
                                                <span className="text-white font-medium">{score}%</span>
                                            </div>
                                            <div className="w-full bg-white bg-opacity-5 rounded-full h-1">
                                                <motion.div
                                                    className={`h-full rounded-full ${score > 70 ? 'bg-primary-green' : score > 40 ? 'bg-primary-blue' : 'bg-orange-500'}`}
                                                    initial={{ width: 0 }}
                                                    animate={{ width: `${score}%` }}
                                                />
                                            </div>
                                        </div>
                                    ))}

                                    <div className="pt-2 border-t border-white border-opacity-5">
                                        <div className="flex justify-between text-xs mb-1">
                                            <span className="text-gray-300 font-semibold">Skill Match Logic</span>
                                            <span className="text-primary-green font-bold">{matchDetails.skill_score}%</span>
                                        </div>
                                        <div className="flex justify-between text-xs mb-1">
                                            <span className="text-gray-300 font-semibold">Keyword Overlap</span>
                                            <span className="text-primary-blue font-bold">{matchDetails.keyword_score}%</span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Match Reasons & Skills */}
                            <div className="md:col-span-2">
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                                    <div>
                                        <h4 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                                            <span className="w-1.5 h-1.5 bg-primary-green rounded-full"></span>
                                            Match Intelligence
                                        </h4>
                                        <ul className="space-y-3">
                                            {matchDetails.match_reasons && matchDetails.match_reasons.map((reason, i) => (
                                                <li key={i} className="text-xs text-gray-300 flex items-start gap-2 bg-white bg-opacity-5 p-2 rounded-lg">
                                                    <span className="text-primary-green font-bold">●</span>
                                                    {reason}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>

                                    <div>
                                        {matchDetails.matched_skills && matchDetails.matched_skills.length > 0 && (
                                            <div className="mb-6">
                                                <h4 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                                                    <span className="w-1.5 h-1.5 bg-primary-blue rounded-full"></span>
                                                    Matched Domain Skills
                                                </h4>
                                                <div className="flex flex-wrap gap-2">
                                                    {matchDetails.matched_skills.map((skill, i) => (
                                                        <span key={i} className="text-[10px] px-2 py-1 rounded-md bg-primary-blue bg-opacity-10 text-primary-blue border border-primary-blue border-opacity-20 hover:bg-opacity-20 transition-all">
                                                            {skill}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {matchDetails.missing_skills && matchDetails.missing_skills.length > 0 && (
                                            <div>
                                                <h4 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                                                    <span className="w-1.5 h-1.5 bg-red-500 rounded-full"></span>
                                                    Skill Gaps Identified
                                                </h4>
                                                <div className="flex flex-wrap gap-2">
                                                    {matchDetails.missing_skills.map((skill, i) => (
                                                        <span key={i} className="text-[10px] px-2 py-1 rounded-md bg-red-500 bg-opacity-5 text-red-400 border border-red-500 border-opacity-10">
                                                            {skill}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
};

export default ResultCard;
