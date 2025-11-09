import React, { useEffect, useState, useCallback } from "react";
import {
  Search, RefreshCw, FileText, Edit, Tag
} from "lucide-react";
import { getSources,getArticles, updateArticleStatus, updateArticleNote,getDeepInsights } from "../api";

//const token = process.env.REACT_APP_JWT_TOKEN || "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzZWV0aGEiLCJ1c2VyX2lkIjoxLCJleHAiOjE3NTMyNjg0MDN9.PcS3-Zdg54v6IZIvCNTqCEI-E4v0YdkvmTDu-l7S1xk"

const Articles = ({
  token, filters, setFilters, searchQuery, setSearchQuery,
  categories, getStatusColor, getStatusIcon
}) => {
  const [sources, setSources] = useState([]);
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editingNote, setEditingNote] = useState(null);
  const [notes, setNotes] = useState({});
  const [page, setPage] = useState(1); // Start at page 1
  const pageSize = 10; // Articles per page
  useEffect(() => {
    setPage(1);
  }, [filters, searchQuery]);
  // Fetch all sources when the component mounts
  useEffect(() => {
    async function fetchSources() {
        const data = await getSources(token);
        setSources(data);  // [{id, name}, ...]
    }
    fetchSources();
  }, [token]);
  const [deepInsights, setDeepInsights] = useState({});
  const [loadingInsight, setLoadingInsight] = useState(null);

  const handleGetDeepInsights = async (articleId) => {
    setLoadingInsight(articleId);
    try {
        const result = await getDeepInsights(token, articleId);
        setDeepInsights((prev) => ({ ...prev, [articleId]: result }));
    } catch (e) {
        alert("Failed to get deep insights");
    }
    setLoadingInsight(null);
  };
  // Fetch Articles from API
  const fetchArticles = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filters.category && filters.category !== "all")
        params.category = filters.category;
      if (filters.status && filters.status !== "all")
        params.status = filters.status;
      if (filters.fromDate)
        params.from_date = filters.fromDate; 
      if (searchQuery)
        params.search = searchQuery;
      if (filters.score)
        params.score = filters.score;
      if (filters.source_name && filters.source_name !== "all") 
        params.source_name = filters.source_name;
      params.limit = pageSize;
      params.offset = (page - 1) * pageSize;
      const data = await getArticles(token, params);
      setArticles(data || []);
      let notesObj = {};
      (data || []).forEach(article => {
        if (article.note) notesObj[article.id] = article.note;
      });
      setNotes(notesObj);
    } catch (err) {
      console.error("Error fetching articles", err);
    }
    setLoading(false);
  }, [filters, searchQuery,token,page]);

  useEffect(() => {
    fetchArticles();
  }, [fetchArticles,searchQuery, page]);
  useEffect(() => {
    setPage(1);
  }, [filters.source_name]);
  const handleStatusChange = async (articleId, newStatus) => {
    try {
      await updateArticleStatus(articleId, newStatus, token);
      fetchArticles();
    } catch (err) {
      alert("Failed to update status.");
    }
  };

  const handleNoteSave = async (articleId, note) => {
    try {
      await updateArticleNote(articleId, note, token);
      setNotes((prev) => ({ ...prev, [articleId]: note }));
      setEditingNote(null);
    } catch (err) {
      alert("Failed to save note.");
    }
  };

  // UI
  return (
    <div className="p-6 space-y-4">
      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="Search articles..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <input
            type="date"
            value={filters.fromDate}
            onChange={(e) => setFilters({ ...filters, fromDate: e.target.value })}
            className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <select
            value={filters.score}
            onChange={e => setFilters({ ...filters, score: e.target.value })}
            className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
            <option value="">All Scores</option>
            <option value="90-100">90-100%</option>
            <option value="80-89">80-89%</option>
            <option value="70-79">70-79%</option>
            <option value="60-69">60-69%</option>
            <option value="0-59">0-59%</option>
          </select>
          <select
            value={filters.source_name}
            onChange={e => setFilters({ ...filters, source_name: e.target.value })}
            >
            <option value="all">All Sources</option>
            {sources.map(src => (
                <option key={src.id} value={src.name}>{src.name}</option>
            ))}
          </select>
          <select
            value={filters.category}
            onChange={(e) => setFilters({ ...filters, category: e.target.value })}
            className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Categories</option>
            {categories.map(cat => (
              <option key={cat.id} value={cat.name}>{cat.name}</option>
            ))}
          </select>
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Status</option>
            <option value="new">New</option>
            <option value="reviewed">Reviewed</option>
            <option value="shortlisted">Shortlisted</option>
            <option value="final">Final</option>
          </select>
          <button
            onClick={fetchArticles}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>
      {/* Article List */}
      <div className="space-y-4">
        {loading ? (
          <div className="text-center py-8 text-gray-500">
            <span className="animate-spin inline-block mr-2"><RefreshCw className="w-5 h-5" /></span>
            Loading articles...
          </div>
        ) : articles.length === 0 ? (
          <div className="text-center py-8 text-gray-400">No articles found.</div>
        ) : (
          articles.map(article => (
            <div key={article.id} className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow">
              <div className="p-6">
                {/* HEADER */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">{article.title}</h3>
                    <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500 mb-3">
                      {/* Category */}
                      {article.category && (
                        <span className="flex items-center gap-1 px-2 py-1 bg-gray-100 rounded text-xs font-medium">
                          <Tag className="w-3 h-3 text-blue-400" />
                          {article.category}
                        </span>
                      )}
                      {/* Source Name - only show if available */}
                      {article.source_name && (
                        <>
                          <span>•</span>
                          <span className="inline-block bg-blue-100 text-blue-800 text-xs font-bold px-3 py-1 rounded-full">
                            {article.source_name}
                          </span>
                        </>
                      )}
                      {/* Date */}
                      <span>•</span>
                      <span>{article.date ? new Date(article.date).toLocaleDateString() : ""}</span>
                      {/* Score */}
                      <span>•</span>
                      <span className="text-blue-600 font-medium">
                        Score: {article.relevance_score ?? "—"}%
                      </span>
                    </div>
                    {/* Summary */}
                    <p className="text-gray-600 mb-3">{article.summary}</p>
                    {/* LLM Summary (if available) */}
                    {article.llm_summary && (
                    <div className="mb-3 p-3 bg-gray-50 rounded border-l-4 border-blue-400">
                        <div className="font-semibold text-blue-700 mb-1">AI-Generated Summary:</div>
                        <div className="text-gray-800">{article.llm_summary}</div>
                    </div>
                    )}

                    {/* Key Insights (if available) */}
                    {article.key_insights && (
                    <div className="mb-3 p-3 bg-yellow-50 rounded border-l-4 border-yellow-400">
                        <div className="font-semibold text-yellow-700 mb-1">Key Insights:</div>
                        <ul className="list-disc pl-5 text-gray-800">
                        {Array.isArray(article.key_insights)
                            ? article.key_insights.map((ins, idx) => <li key={idx}>{ins}</li>)
                            : <li>{article.key_insights}</li>}
                        </ul>
                    </div>
                    )}

                    {/* Deep Insights Button & Section */}
                    <div className="mt-4">
                    <button
                        disabled={loadingInsight === article.id}
                        onClick={() => handleGetDeepInsights(article.id)}
                        className="px-3 py-1 bg-blue-200 rounded hover:bg-blue-300"
                    >
                        {loadingInsight === article.id ? "Loading..." : "Deep Insights"}
                    </button>

                    {/* Show Deep Insights if present */}
                    {deepInsights[article.id] && (
                        <div className="mt-2 p-3 bg-gray-50 rounded border">
                        <strong>Deep Summary:</strong>
                        <div className="mb-2">{deepInsights[article.id].summary}</div>
                        <strong>Key Insights:</strong>
                        <ul className="list-disc ml-5 mb-2">
                            {(Array.isArray(deepInsights[article.id].key_insights)
                            ? deepInsights[article.id].key_insights
                            : [deepInsights[article.id].key_insights]
                            ).map((ins, i) => <li key={i}>{ins}</li>)}
                        </ul>
                        <details>
                            <summary className="cursor-pointer text-blue-600">Show Full Scraped Text</summary>
                            <pre className="whitespace-pre-wrap max-h-40 overflow-auto">{deepInsights[article.id].full_text?.slice(0, 2000)}...</pre>
                        </details>
                        </div>
                    )}
                    </div>
                 </div>
                </div>
                {/* ACTIONS */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`px-3 py-1 rounded-full text-sm font-medium flex items-center gap-1 ${getStatusColor(article.status)}`}>
                      {getStatusIcon(article.status)}
                      {article.status}
                    </span>
                    <select
                      value={article.status}
                      onChange={(e) => handleStatusChange(article.id, e.target.value)}
                      className="px-3 py-1 border rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="new">New</option>
                      <option value="reviewed">Reviewed</option>
                      <option value="shortlisted">Shortlisted</option>
                      <option value="final">Final</option>
                    </select>
                  </div>
                  <div className="flex items-center gap-2">
                    {/* View Full = Article Link */}
                    {article.meta_data && article.meta_data.link && (
                      <a
                        href={article.meta_data.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-3 py-1 text-blue-600 hover:bg-blue-50 rounded flex items-center gap-1"
                      >
                        <FileText className="w-4 h-4" />
                        View Full
                      </a>
                    )}
                    {/* Note Button */}
                    <button
                      onClick={() => setEditingNote(article.id)}
                      className="px-3 py-1 text-gray-600 hover:bg-gray-50 rounded flex items-center gap-1"
                    >
                      <Edit className="w-4 h-4" />
                      {notes[article.id] ? "Edit Note" : "Add Note"}
                    </button>
                  </div>
                </div>
                {/* NOTE INPUT */}
                {editingNote === article.id && (
                  <div className="mt-4 p-3 bg-gray-50 rounded">
                    <textarea
                      className="w-full p-2 border rounded text-sm"
                      placeholder="Add a note..."
                      rows="3"
                      defaultValue={notes[article.id] || ""}
                      onBlur={(e) => {
                        handleNoteSave(article.id, e.target.value);
                      }}
                    />
                  </div>
                )}
                {/* NOTE DISPLAY */}
                {notes[article.id] && (
                  <div className="mt-4 p-3 bg-blue-50 rounded">
                    <p className="text-sm text-gray-700">
                      <span className="font-medium">Note:</span> {notes[article.id]}
                    </p>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
      <div className="flex justify-center mt-6 gap-2">
        <button
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
            className="px-3 py-1 rounded bg-gray-200 hover:bg-gray-300 disabled:opacity-50"
        >
            Prev
        </button>
        <span className="px-3 py-1">{page}</span>
        <button
            disabled={articles.length < pageSize}
            onClick={() => setPage(page + 1)}
            className="px-3 py-1 rounded bg-gray-200 hover:bg-gray-300 disabled:opacity-50"
        >
            Next
        </button>
      </div>
    </div>
  );
};

export default Articles;