/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: {
                    blue: '#1E88E5',
                    'blue-dark': '#0D47A1',
                    green: '#4CAF50',
                },
                dark: {
                    bg: '#0a0e27',
                    card: '#1a1f3a',
                }
            },
            animation: {
                'fade-in': 'fadeIn 0.8s ease-in-out',
                'scale-in': 'scaleIn 0.8s ease-in-out',
                'slide-up': 'slideUp 0.6s ease-out',
                'glow': 'glow 2s ease-in-out infinite alternate',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
                scaleIn: {
                    '0%': { transform: 'scale(0.9)', opacity: '0' },
                    '100%': { transform: 'scale(1)', opacity: '1' },
                },
                slideUp: {
                    '0%': { transform: 'translateY(0)' },
                    '100%': { transform: 'translateY(-100vh)' },
                },
                glow: {
                    '0%': {
                        boxShadow: '0 0 20px rgba(30, 136, 229, 0.5), 0 0 40px rgba(30, 136, 229, 0.3)',
                        filter: 'drop-shadow(0 0 20px rgba(30, 136, 229, 0.5))'
                    },
                    '100%': {
                        boxShadow: '0 0 30px rgba(30, 136, 229, 0.8), 0 0 60px rgba(30, 136, 229, 0.5)',
                        filter: 'drop-shadow(0 0 30px rgba(30, 136, 229, 0.8))'
                    },
                },
            },
        },
    },
    plugins: [],
}
