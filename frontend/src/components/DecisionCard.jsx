import { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer } from 'recharts';

const DecisionCard = ({ decisionResult }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    const decisionColor = useMemo(() => {
        if (decisionResult.decision === 'Hire') {
            return {
                badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-400/30',
                chip: {
                    High: 'bg-emerald-500/10 text-emerald-200 border-emerald-300/20',
                    Medium: 'bg-amber-500/10 text-amber-200 border-amber-300/20',
                    Low: 'bg-slate-500/10 text-slate-300 border-slate-300/20',
                },
                progress: 'from-emerald-500 to-emerald-400',
            };
        }
        if (decisionResult.decision === 'Consider') {
            return {
                badge: 'bg-amber-500/20 text-amber-300 border-amber-400/30',
                chip: {
                    High: 'bg-amber-500/10 text-amber-200 border-amber-300/20',
                    Medium: 'bg-amber-500/10 text-amber-200 border-amber-300/20',
                    Low: 'bg-slate-500/10 text-slate-300 border-slate-300/20',
                },
                progress: 'from-amber-500 to-amber-400',
            };
        }
        return {
            badge: 'bg-red-500/20 text-red-300 border-red-400/30',
            chip: {
                High: 'bg-red-500/10 text-red-200 border-red-300/20',
                Medium: 'bg-amber-500/10 text-amber-200 border-amber-300/20',
                Low: 'bg-slate-500/10 text-slate-300 border-slate-300/20',
            },
            progress: 'from-red-500 to-red-400',
        };
    }, [decisionResult.decision]);

    const radarData = [
        { subject: 'Semantic', score: decisionResult.score_breakdown.semantic_score, fullMark: 100 },
        { subject: 'Keywords', score: decisionResult.score_breakdown.keyword_score, fullMark: 100 },
        { subject: 'Experience', score: decisionResult.score_breakdown.experience_score, fullMark: 100 },
        { subject: 'Education', score: decisionResult.score_breakdown.education_score, fullMark: 100 },
        { subject: 'Completeness', score: decisionResult.score_breakdown.completeness_score, fullMark: 100 },
    ];

    const hasWarnings = decisionResult.uncertainty_notes.length > 0 || decisionResult.bias_flags.length > 0;

    return (
        <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            className="cursor-pointer rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md p-5 transition-all hover:border-white/20"
            onClick={() => setIsExpanded(prev => !prev)}
        >
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div className="flex-1 min-w-0">
                    <h3 className="truncate text-lg font-bold text-white">{decisionResult.filename}</h3>
                    <div className="mt-2 flex items-center gap-2">
                        <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${decisionColor.badge}`}>
                            {decisionResult.decision}
                        </span>
                        <span className={`rounded-full border px-2.5 py-1 text-xs ${decisionColor.chip[decisionResult.confidence_label]}`}>
                            Confidence: {decisionResult.confidence_label}
                        </span>
                    </div>
                </div>

                <div className="text-right">
                    <div className="text-4xl font-extrabold text-white">{Math.round(decisionResult.composite_score)}</div>
                    <div className="text-xs uppercase tracking-wide text-gray-400">Composite Score</div>
                </div>
            </div>

            <div className="mt-4 h-3 w-full overflow-hidden rounded-full bg-white/10">
                <motion.div
                    className={`h-full rounded-full bg-gradient-to-r ${decisionColor.progress}`}
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.max(0, Math.min(decisionResult.composite_score, 100))}%` }}
                    transition={{ duration: 0.8, ease: 'easeOut' }}
                />
            </div>

            <AnimatePresence>
                {isExpanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.25 }}
                        className="overflow-hidden"
                    >
                        <div className="mt-5 space-y-6 border-t border-white/10 pt-5">
                            <div>
                                <h4 className="mb-3 text-sm font-semibold text-white">Score Breakdown</h4>
                                <div className="h-64 rounded-xl border border-white/5 bg-black/10 p-2">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <RadarChart cx="50%" cy="50%" outerRadius="75%" data={radarData}>
                                            <PolarGrid stroke="rgba(255,255,255,0.15)" />
                                            <PolarAngleAxis dataKey="subject" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                                            <Radar
                                                dataKey="score"
                                                stroke="#d6a62a"
                                                fill="#d6a62a"
                                                fillOpacity={0.4}
                                            />
                                        </RadarChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>

                            <div>
                                <h4 className="mb-3 text-sm font-semibold text-white">Matched Skills</h4>
                                <div className="flex flex-wrap gap-2">
                                    {decisionResult.matched_skills.length > 0 ? (
                                        decisionResult.matched_skills.map((skill, idx) => (
                                            <span key={`${skill}-${idx}`} className="rounded-full border border-emerald-400/25 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-200">
                                                {skill}
                                            </span>
                                        ))
                                    ) : (
                                        <span className="text-xs text-gray-400">No matched skills extracted.</span>
                                    )}
                                </div>
                            </div>

                            {decisionResult.skill_gaps.length > 0 && (
                                <div>
                                    <h4 className="mb-3 text-sm font-semibold text-white">Skill Gaps</h4>
                                    <div className="overflow-x-auto rounded-xl border border-white/10">
                                        <table className="min-w-full text-left text-xs">
                                            <thead className="bg-white/5 text-gray-300">
                                                <tr>
                                                    <th className="px-3 py-2 font-medium">Skill</th>
                                                    <th className="px-3 py-2 font-medium">Priority</th>
                                                    <th className="px-3 py-2 font-medium">Recruiter Suggestion</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {decisionResult.skill_gaps.map((gap, idx) => {
                                                    const priorityClass =
                                                        gap.priority === 'Critical'
                                                            ? 'bg-red-500/15 text-red-300 border-red-400/30'
                                                            : gap.priority === 'Important'
                                                                ? 'bg-amber-500/15 text-amber-300 border-amber-400/30'
                                                                : 'bg-slate-500/15 text-slate-300 border-slate-400/30';
                                                    return (
                                                        <tr key={`${gap.skill}-${idx}`} className="border-t border-white/10">
                                                            <td className="px-3 py-2 text-gray-100">{gap.skill}</td>
                                                            <td className="px-3 py-2">
                                                                <span className={`rounded-full border px-2 py-0.5 ${priorityClass}`}>
                                                                    {gap.priority}
                                                                </span>
                                                            </td>
                                                            <td className="px-3 py-2 text-gray-300">{gap.suggestion}</td>
                                                        </tr>
                                                    );
                                                })}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}

                            <div>
                                <h4 className="mb-2 text-sm font-semibold text-white">Reasons</h4>
                                <ul className="space-y-2">
                                    {decisionResult.reasons.map((reason, idx) => (
                                        <li key={`reason-${idx}`} className="text-sm text-gray-300">
                                            • {reason}
                                        </li>
                                    ))}
                                </ul>
                            </div>

                            {hasWarnings && (
                                <div className="space-y-2">
                                    {decisionResult.uncertainty_notes.map((note, idx) => (
                                        <div key={`u-${idx}`} className="rounded-lg border border-amber-400/25 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
                                            {note}
                                        </div>
                                    ))}
                                    {decisionResult.bias_flags.map((_, idx) => (
                                        <div key={`b-${idx}`} className="rounded-lg border border-red-400/25 bg-red-500/10 px-3 py-2 text-xs text-red-200">
                                            ⚠️ Bias-sensitive field detected — excluded from scoring
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
};

export default DecisionCard;
