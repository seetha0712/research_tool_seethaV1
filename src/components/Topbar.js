// src/components/Topbar.js
import React from 'react';

const Topbar = (token) => (
  <div className="h-14 bg-white shadow flex items-center justify-between px-4">
    <div className="text-lg font-medium">GenAI Research Dashboard</div>
    <div className="text-sm text-gray-500">Logged in</div>
  </div>
);

export default Topbar;