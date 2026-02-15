import { motion } from 'framer-motion';

/**
 * ResultCard Component
 * Displays individual resume ranking result with glassmorphism design
 */
const ResultCard = ({ filename, matchPercentage, index }) => {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: index * 0.1 }}
            className="glass-card-hover p-6 mb-4"
        >
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                {/* File info */}
                <div className="flex-1">
                    <h3 className="text-lg font-semibold text-white mb-1 truncate">
                        {filename}
                    </h3>
                    <p className="text-sm text-gray-400">Resume Analysis</p>
                </div>

                {/* Match percentage */}
                <div className="flex items-center gap-6">
                    <div className="text-right">
                        <div className="text-4xl font-bold bg-gradient-to-r from-primary-blue to-primary-green bg-clip-text text-transparent">
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
        </motion.div>
    );
};

export default ResultCard;
