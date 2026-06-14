import React, { useState } from 'react';
import InTimeTecConsole from './components/InTimeTecConsole';
import AdminPanel from './admin/pages/AdminPanel';

const App: React.FC = () => {
  const [view, setView] = useState<'main' | 'admin'>(
    window.location.hash === '#admin' ? 'admin' : 'main'
  );

  const goAdmin = () => { window.location.hash = 'admin'; setView('admin'); };
  const goMain  = () => { window.location.hash = '';      setView('main');  };

  if (view === 'admin') return <AdminPanel onBack={goMain} />;
  return <InTimeTecConsole onAdminClick={goAdmin} />;
};

export default App;
