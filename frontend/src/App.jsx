import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Login from './pages/admin/Login/Login.jsx';
import PanelAdmin from './pages/admin//PanelAdmin/PanelAdmin.jsx';
import HomePage from './pages/Home/HomePage.jsx';
import './App.css'

function App() {
  return (
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/admin" element={<Login />} />
        <Route path="/adminPanel" element={<PanelAdmin />} />
      </Routes>
  );
}

export default App;