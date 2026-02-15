import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';

/**
 * LandingAnimation Component
 * Cinematic intro animation with logo and text reveal
 * Duration: 2-3 seconds, then transitions to dashboard
 */
const LandingAnimation = ({ onComplete }) => {
    const [startTransition, setStartTransition] = useState(false);

    useEffect(() => {
        // Start transition after 2.5 seconds
        const timer = setTimeout(() => {
            setStartTransition(true);
        }, 2500);

        // Complete animation after 3.2 seconds (includes slide-up transition)
        const completeTimer = setTimeout(() => {
            onComplete();
        }, 3200);

        return () => {
            clearTimeout(timer);
            clearTimeout(completeTimer);
        };
    }, [onComplete]);

    return (
        <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center bg-gradient-to-br from-dark-bg via-[#0f1535] to-dark-card overflow-hidden"
            initial={{ opacity: 1 }}
            animate={startTransition ? { y: '-100vh' } : { y: 0 }}
            transition={{ duration: 0.7, ease: 'easeInOut' }}
        >
            {/* Animated background particles */}
            <div className="absolute inset-0 overflow-hidden">
                {[...Array(20)].map((_, i) => (
                    <motion.div
                        key={i}
                        className="absolute w-1 h-1 bg-primary-blue rounded-full"
                        style={{
                            left: `${Math.random() * 100}%`,
                            top: `${Math.random() * 100}%`,
                        }}
                        animate={{
                            opacity: [0.2, 0.8, 0.2],
                            scale: [1, 1.5, 1],
                        }}
                        transition={{
                            duration: 2 + Math.random() * 2,
                            repeat: Infinity,
                            delay: Math.random() * 2,
                        }}
                    />
                ))}
            </div>

            {/* Main content container */}
            <div className="relative z-10 flex flex-col items-center gap-8">
                {/* Logo with glow effect */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.8, ease: 'easeOut' }}
                    className="relative"
                >
                    <motion.img
                        src="/logo.png"
                        alt="RecruitDesk AI Logo"
                        className="w-32 h-32 object-contain animate-glow"
                        animate={{
                            filter: [
                                'drop-shadow(0 0 20px rgba(30, 136, 229, 0.5))',
                                'drop-shadow(0 0 40px rgba(30, 136, 229, 0.8))',
                                'drop-shadow(0 0 20px rgba(30, 136, 229, 0.5))',
                            ],
                        }}
                        transition={{
                            duration: 2,
                            repeat: Infinity,
                            ease: 'easeInOut',
                        }}
                    />
                </motion.div>

                {/* Text with typing reveal effect */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.8, delay: 0.3, ease: 'easeOut' }}
                    className="text-center"
                >
                    <motion.h1
                        className="text-6xl md:text-7xl font-bold bg-gradient-to-r from-primary-blue via-primary-green to-primary-blue bg-clip-text text-transparent"
                        style={{
                            backgroundSize: '200% auto',
                        }}
                        animate={{
                            backgroundPosition: ['0% center', '100% center', '0% center'],
                        }}
                        transition={{
                            duration: 3,
                            repeat: Infinity,
                            ease: 'linear',
                        }}
                    >
                        RecruitDesk AI
                    </motion.h1>

                    <motion.p
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6, delay: 0.8 }}
                        className="text-xl md:text-2xl text-gray-300 mt-4 font-light tracking-wide"
                    >
                        AI-Powered Resume Intelligence
                    </motion.p>
                </motion.div>

                {/* Loading indicator */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 1.2 }}
                    className="flex gap-2 mt-8"
                >
                    {[0, 1, 2].map((i) => (
                        <motion.div
                            key={i}
                            className="w-3 h-3 bg-primary-blue rounded-full"
                            animate={{
                                scale: [1, 1.5, 1],
                                opacity: [0.5, 1, 0.5],
                            }}
                            transition={{
                                duration: 1,
                                repeat: Infinity,
                                delay: i * 0.2,
                            }}
                        />
                    ))}
                </motion.div>
            </div>
        </motion.div>
    );
};

export default LandingAnimation;
