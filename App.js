import React, { useState } from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import Register from './components/Register'
import Login from './components/Login'
import Chat from './components/Chat';
import './App.css';

function App() {
  const [user, setUser] = useState(null);

  const handleLogin = (username) => {
    setUser(username);
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('token');
  };

  return (
    <Router>
      <div className="App">
        <h1>Chat Application</h1>
        <Routes>
          <Route path="/register" element={user ? <Chat username={user} onLogout={handleLogout} /> : <Register />} />
          <Route path="/login" element={user ? <Chat username={user} onLogout={handleLogout} /> : <Login onLogin={handleLogin} />} />
          <Route path="/chat" element={user ? <Chat username={user} onLogout={handleLogout} /> : <Navigate to="/login" />} />
          <Route path="/" element={user ? <Chat username={user} onLogout={handleLogout} /> : <Navigate to="/login" />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
