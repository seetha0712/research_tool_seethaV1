import React, { useState, useEffect } from "react";

import {
  FolderOpen, BarChart3,Globe,TrendingUp, Building2, Cpu, Users, FileText, RefreshCw, Download, Brain, AlertCircle, Clock, Star, Check, Shield, Activity, Server, AlertTriangle
} from "lucide-react";

import Login from "./components/Login";
import Register from "./components/Register";
import Dashboard from "./components/Dashboard";
import Articles from "./components/Articles";
import Sources from "./components/Sources";
import DeckBuilder from "./components/DeckBuilder";
import PaidSearchTab from "./components/PaidSearchTab";
import Admin from "./components/Admin";
import AuditLogs from "./components/AuditLogs";
import Infrastructure from "./components/Infrastructure";

import { syncSources, getSources, checkBackendHealth } from "./api";
import { getArticles, getSavedPaidArticles } from "./api"; 

const categories = [
  { id: "uncategorized", name: "Uncategorized", icon: FolderOpen }, // always first

  { id: "strategic-overview", name: "AI & GenAI Trends", icon: BarChart3 },
  { id: "ai-finance", name: "AI in Financial Institutions", icon: Building2 },
  { id: "company-profiles", name: "Leading AI Innovators", icon: Users },
  { id: "agentic", name: "Agentic AI", icon: Brain },
  { id: "broader-ai", name: "Broader AI Topics", icon: TrendingUp },
  { id: "tech-corner", name: "Tech Corner", icon: Cpu },
  { id: "beyond-finance", name: "AI Beyond Finance", icon: Globe }
];


const getStatusColor = (status) => {
  const colors = {
    new: "bg-gray-100 text-gray-700",
    reviewed: "bg-blue-100 text-blue-700",
    shortlisted: "bg-yellow-100 text-yellow-700",
    final: "bg-green-100 text-green-700",
  };
  return colors[status] || "bg-gray-100 text-gray-700";
};
const getStatusIcon = (status) => {
  const icons = {
    new: <AlertCircle className="w-4 h-4" />,
    reviewed: <Clock className="w-4 h-4" />,
    shortlisted: <Star className="w-4 h-4" />,
    final: <Check className="w-4 h-4" />
  };
  return icons[status] || null;
};


const App = () => {
  // --- Auth ---
  const [token, setToken] = useState(() => localStorage.getItem("jwt_token") || "");
  const [showRegister, setShowRegister] = useState(false);
  const [removedFromDeck, setRemovedFromDeck] = useState([]);
  // --- Main App state ---
  const [activeTab, setActiveTab] = useState("dashboard");

  // Get admin status from localStorage
  const isAdmin = localStorage.getItem("is_admin") === "true";
  const [maintenanceMode, setMaintenanceMode] = useState(false);
  const [articles, setArticles] = useState([]);
  const [sources, setSources] = useState([]);
  const [selectedArticles, setSelectedArticles] = useState([]);


  const [filters, setFilters] = useState({
    dateRange: "30days",
    category: "all",
    source: "all",
    status: "all",
    relevanceMin: 0,
    fromDate: "",
    score: "",
  });
  const [searchQuery, setSearchQuery] = useState("");
  const [editingNote, setEditingNote] = useState(null);
  const [notes, setNotes] = useState({});

  const [syncLimit, setSyncLimit] = useState(10);
  const [syncFromDate, setSyncFromDate] = useState(""); // format: YYYY-MM-DD
  const [syncing, setSyncing] = useState(false);


  // Paid Search tab specific state
  const [paidSearchQuery, setPaidSearchQuery] = useState("");
  const [paidSearchResults, setPaidSearchResults] = useState([]);
  const [paidSearchLoading, setPaidSearchLoading] = useState(false);

  // --- Deck Builder state ---
  const [finalMainArticles, setFinalMainArticles] = useState([]);
  const [finalPaidArticles, setFinalPaidArticles] = useState([]);


  // Load sources on mount/login
  const fetchSources = async () => {
      if (!token) return;
      try {
        const res = await getSources(token);
        setSources(res);
      } catch (err) {
        setSources([]);
      }
    };

    // Load sources on mount/login
    useEffect(() => {
      if (!token) return;
      fetchSources();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token]);

    // Check backend health periodically (for maintenance mode detection)
    useEffect(() => {
      if (!token || isAdmin) return;

      const checkHealth = async () => {
        const result = await checkBackendHealth();
        setMaintenanceMode(!result.healthy);
      };

      checkHealth();
      const interval = setInterval(checkHealth, 30000);
      return () => clearInterval(interval);
    }, [token, isAdmin]);


  // Load ALL articles & paid search results on mount/login
  useEffect(() => {
    if (!token) return;

    async function fetchMainArticles() {
      try {
        const mainArticles = await getArticles(token, { limit: 500 });
        setArticles(mainArticles);
      } catch (err) {
        setArticles([]);
      }
    }

    async function fetchPaidArticles() {
      try {
        const paidArticles = await getSavedPaidArticles(token, "");
        setPaidSearchResults(paidArticles);
      } catch (err) {
        setPaidSearchResults([]);
      }
    }

    fetchMainArticles();
    fetchPaidArticles();
  }, [token]);
  
    // DeckBuilder: Fetch only "final" articles (main + paid) when that tab is active
  useEffect(() => {
    if (!token) return;
    if (activeTab === "deck-builder") {
       getArticles(token, { status: "final", limit: 500 }).then(res => {
            console.log("DeckBuilder Fetched MAIN FINAL articles:", res); // DEBUG
            setFinalMainArticles(res);
        });
      getSavedPaidArticles(token, "").then(res => {
            console.log("DeckBuilder Fetched PAID FINAL articles:", res.filter(a => (a.status || '').toLowerCase() === "final")); // DEBUG
            setFinalPaidArticles(res.filter(a => (a.status || '').toLowerCase() === "final"));
        });
    }
  }, [activeTab, token]);

  const categoriesByName = Object.fromEntries(categories.map(cat => [cat.name, cat.id]));

  const mainArticlesWithCategoryId = finalMainArticles.map(a => ({
        ...a,
    category: categoriesByName[a.category] || a.category // convert name to id if needed
  }));
  // Sync handler
  const handleSync = async () => {
    setSyncing(true);
    try {
      await syncSources(token, { limit: syncLimit, from_date: syncFromDate });
      // Optionally reload articles/sources here!
      alert("Sync complete!");
    } catch (err) {
      alert("Sync failed: " + (err?.response?.data?.detail || err.message));
    }
    setSyncing(false);
  };

  const handleStatusChange = (articleId, newStatus) => {
    setArticles(articles.map(article =>
      article.id === articleId ? { ...article, status: newStatus } : article
    ));
    if (newStatus === "final") {
      const article = articles.find(a => a.id === articleId);
      if (article && !selectedArticles.find(a => a.id === articleId)) {
        setSelectedArticles([...selectedArticles, article]);
      }
    } else {
      setSelectedArticles(selectedArticles.filter(a => a.id !== articleId));
    }
  };

  // Logout
  const handleLogout = () => {
    setToken("");
    localStorage.removeItem("jwt_token");
    localStorage.removeItem("is_admin");
  };

  // --- Auth: pass correct props to Login/Register ---
  if (!token) {
    return showRegister
      ? <Register
          onRegisterSuccess={() => setShowRegister(false)} // Optional: auto switch to login on success
          onSwitchToLogin={() => setShowRegister(false)}
        />
      : <Login
          onLoginSuccess={(token) => {
            setToken(token);
            localStorage.setItem("jwt_token", token);
          }}
          onSwitchToRegister={() => setShowRegister(true)}
        />;
  }
  
  // --- DeckBuilder: Combine "final" main and paid articles for the deck ---
  const deckBuilderArticles = [
    ...mainArticlesWithCategoryId,
    ...finalPaidArticles.filter(
      pa => !mainArticlesWithCategoryId.find(a =>
        (a.id && pa.id && a.id === pa.id) ||
        (a.link && pa.link && a.link === pa.link)
      )
    ),
  ]
  // FILTER OUT articles whose id OR link is in removedFromDeck
  .filter(a =>
    !(removedFromDeck.includes(a.id) || removedFromDeck.includes(a.link))
  );

  // --- Main UI ---
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <Brain className="w-8 h-8 text-blue-600" />
              <h1 className="text-xl font-bold text-gray-900">
                Gen AI Research Tool
              </h1>
            </div>
            <div className="flex items-center gap-4">
             <span className="text-sm text-gray-600">Research Division</span>
               {isAdmin && (
                <>
                  <label>
                      # Articles:
                      <input
                      type="number"
                      value={syncLimit}
                      min={1}
                      max={100}
                      onChange={e => setSyncLimit(parseInt(e.target.value, 10))}
                      className="ml-2 px-2 py-1 border rounded w-20"
                      />
                  </label>
                  <label>
                      From date:
                      <input
                      type="date"
                      value={syncFromDate}
                      onChange={e => setSyncFromDate(e.target.value)}
                      className="ml-2 px-2 py-1 border rounded"
                      />
                  </label>
                  <button
                      onClick={handleSync}
                      className="px-4 py-2 bg-blue-600 text-white rounded"
                      disabled={syncing}
                  >
                      {syncing ? "Syncing..." : "Sync Now"}
                  </button>
                </>
               )}
               {!isAdmin && (
                 <span className="text-sm text-gray-600 bg-gray-100 px-3 py-2 rounded">
                   View Mode (Admin-only sync)
                 </span>
               )}
                <button onClick={handleLogout} className="ml-4 px-3 py-1 bg-gray-200 rounded">
                    Logout
                </button>
            </div>
          </div>
        </div>
      </header>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <nav className="flex space-x-8 mb-8 border-b">
          {[
            { id: "dashboard", label: "Dashboard", icon: TrendingUp },
            { id: "articles", label: "Articles", icon: FileText },
            { id: "sources", label: "Sources", icon: RefreshCw },
            { id: "paid-search", label: "Paid Search", icon: Brain },
            { id: "deck-builder", label: "Deck Builder", icon: Download },
            ...(isAdmin ? [
              { id: "admin", label: "Admin", icon: Shield },
              { id: "audit-logs", label: "Audit Logs", icon: Activity },
              { id: "infrastructure", label: "Infrastructure", icon: Server }
            ] : []),
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`pb-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors ${
                  activeTab === tab.id
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>
        {activeTab === "dashboard" && (
          <Dashboard
            token={token}
            categories={categories}
            getStatusColor={getStatusColor}
            isAdmin={isAdmin}
          />
        )}
        {activeTab === "articles" && (
          <Articles
            token={token}
            articles={articles}
            setArticles={setArticles}
            filters={filters}
            setFilters={setFilters}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            selectedArticles={selectedArticles}
            setSelectedArticles={setSelectedArticles}
            editingNote={editingNote}
            setEditingNote={setEditingNote}
            notes={notes}
            setNotes={setNotes}
            getStatusColor={getStatusColor}
            getStatusIcon={getStatusIcon}
            handleStatusChange={handleStatusChange}
            categories={categories}
          />
        )}
        {activeTab === "sources" && (
          <Sources
            token={token}
            sources={sources}
            fetchSources={fetchSources}
            isAdmin={isAdmin}
          />
        )}
        {activeTab === "paid-search" && (
        <PaidSearchTab
            token={token}
            query={paidSearchQuery}
            setQuery={setPaidSearchQuery}
            results={paidSearchResults}
            setResults={setPaidSearchResults}
            loading={paidSearchLoading}
            setLoading={setPaidSearchLoading}
        />
        )}
   
        {activeTab === "deck-builder" && (
        (() => {
            // Debug log for DeckBuilder props
            console.log("Rendering DeckBuilder:");
            console.log("selectedArticles:", selectedArticles);
            console.log("categories:", categories);
            // Return the actual component to render
            return (
            <DeckBuilder
                token={token}
                categories={categories}
                selectedArticles={deckBuilderArticles}
                setSelectedArticles={setSelectedArticles}
                removedFromDeck={removedFromDeck}
                setRemovedFromDeck={setRemovedFromDeck}
                handleStatusChange={handleStatusChange}
            />
            );
        })()
        )}

        {activeTab === "admin" && isAdmin && (
          <Admin token={token} />
        )}

        {activeTab === "audit-logs" && isAdmin && (
          <AuditLogs token={token} />
        )}

        {activeTab === "infrastructure" && isAdmin && (
          <Infrastructure token={token} />
        )}
      </div>

      {/* Maintenance Mode Banner for non-admins */}
      {maintenanceMode && !isAdmin && (
        <div className="fixed inset-0 bg-gray-900 bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4 p-8 text-center">
            <div className="flex justify-center mb-4">
              <div className="p-4 bg-yellow-100 rounded-full">
                <AlertTriangle className="w-12 h-12 text-yellow-600" />
              </div>
            </div>
            <h2 className="text-2xl font-bold text-gray-800 mb-2">Maintenance Mode</h2>
            <p className="text-gray-600 mb-6">
              The application is currently undergoing maintenance. Please try again later.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
            >
              Refresh Page
            </button>
          </div>
        </div>
      )}
      {/* If you want AddSourceModal as a separate popup, can integrate here */}
      {/* <AddSourceModal ... /> */}
    </div>
  );
};

export default App;