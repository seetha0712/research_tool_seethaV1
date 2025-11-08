// src/components/Sidebar.js
import React from 'react';

const Sidebar = ({ token, activeTab, setActiveTab }) => {
  const tabs = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'articles', label: 'Articles' },
    { id: 'sources', label: 'Sources' },
    { id: 'deck', label: 'Deck Builder' },
  ];

  return (
    <div className="w-64 bg-white shadow-md">
      <div className="p-4 text-lg font-bold">GenAI Tool</div>
      <ul>
        {tabs.map(tab => (
          <li
            key={tab.id}
            className={`p-3 cursor-pointer hover:bg-gray-100 ${activeTab === tab.id ? 'bg-gray-200 font-semibold' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default Sidebar;