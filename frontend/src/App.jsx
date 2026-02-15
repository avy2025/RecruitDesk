import { useState } from 'react';
import LandingAnimation from './components/LandingAnimation';
import Dashboard from './components/Dashboard';
import './index.css';

/**
 * Main App Component
 * Manages transition from landing animation to dashboard
 */
function App() {
  const [showDashboard, setShowDashboard] = useState(false);

  const handleAnimationComplete = () => {
    setShowDashboard(true);
  };

  return (
    <>
      {!showDashboard && <LandingAnimation onComplete={handleAnimationComplete} />}
      {showDashboard && <Dashboard />}
    </>
  );
}

export default App;
