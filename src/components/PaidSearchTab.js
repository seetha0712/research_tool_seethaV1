import React, { useState,useEffect } from "react";
import { Search, Loader, BookmarkPlus, BookmarkCheck } from "lucide-react";
import { fetchPaidSearchResults, getSavedPaidArticles, savePaidArticles,updatePaidArticle } from "../api";
import { categories } from "../constants/categories";

// Helper to cache & restore
const LS_RESULTS_KEY = "last_paid_search_results";
const LS_QUERY_KEY = "last_paid_search_query";


function mergeResultsWithSaved(results, saved) {
  // Use a set for both link and id for maximum robustness
  const savedLinks = new Set(saved.map(a => a.link));
  const savedIds = new Set(saved.map(a => a.id));
  // Optionally, for debugging:
  console.log("Saved Links:", savedLinks);
  console.log("Saved Ids:", savedIds);

  return results.map(a => {
    const found = saved.find(
      s =>
        (a.id && s.id && a.id === s.id) ||
        (a.link && s.link && a.link === s.link)
    );
    return found
      ? { ...a, ...found, is_saved: true }
      : { ...a, is_saved: false };
  });
}


const PaidSearchTab = ({
  token,
  query,
  setQuery,
  results,
  setResults,
  loading,
  setLoading,
}) => {
  const [selectedProviders, setSelectedProviders] = useState(["tavily"]);
  const [searchMode, setSearchMode] = useState("live"); // "live" | "saved" | "both"
  const [saving, setSaving] = useState(false);
  
  // Cache only "raw" live results
  const cacheResults = (results, query) => {
    localStorage.setItem(LS_RESULTS_KEY, JSON.stringify(results));
    localStorage.setItem(LS_QUERY_KEY, query);
  };
   // On mount or tab revisit, restore cached search and always merge with latest DB-saved state
  useEffect(() => {
    if (searchMode === "live") {
      const cached = localStorage.getItem(LS_RESULTS_KEY);
      const cachedQuery = localStorage.getItem(LS_QUERY_KEY);
      if (cached) {
        const cachedResults = JSON.parse(cached);
        setQuery(cachedQuery || "");
        getSavedPaidArticles(token, "").then(saved => {
          setResults(mergeResultsWithSaved(cachedResults, saved));
        });
        return;
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchMode, token]);// Only when tab is entered/changed

   // --- Status and Category ---
  const handleStatusChange = async (articleId, newStatus) => {
    try {
      await updatePaidArticle(token, articleId, { status: newStatus });
      // After update, re-fetch saved and merge!
      const cached = localStorage.getItem(LS_RESULTS_KEY);
      const baseResults = cached ? JSON.parse(cached) : results;
      const saved = await getSavedPaidArticles(token, "");
      const merged = mergeResultsWithSaved(baseResults, saved);
      setResults(merged);
    } catch (e) {
      alert("Failed to update status");
    }
  };


  const handleCategoryChange = async (articleId, newCategory) => {
    try {
      await updatePaidArticle(token, articleId, { category: newCategory });
      // After update, re-fetch saved and merge!
      const cached = localStorage.getItem(LS_RESULTS_KEY);
      const baseResults = cached ? JSON.parse(cached) : results;
      const saved = await getSavedPaidArticles(token, "");
      const merged = mergeResultsWithSaved(baseResults, saved);
      setResults(merged);
    } catch (e) {
      alert("Failed to update category");
    }
  };
    // --- Save ALL unsaved ---
  const handleSaveAll = async () => {
    setSaving(true);
    try {
      const unsaved = results.filter((a) => !a.is_saved);
      if (!unsaved.length) return alert("All results already saved!");
      await savePaidArticles(token, unsaved);
      // After save all, always re-fetch saved from DB and re-merge!
      //const cached = localStorage.getItem(LS_RESULTS_KEY);
      //const baseResults = cached ? JSON.parse(cached) : results;
      const saved = await getSavedPaidArticles(token, "");
      const merged = mergeResultsWithSaved(results, saved);
      setResults(merged);
       // Do NOT update cache here!
    } catch (e) {
      alert("Save failed");
    }
    setSaving(false);
  };
  // --- Save one article ---
  const handleSaveArticle = async (article) => {
    setSaving(true);
    try {
      await savePaidArticles(token, [article]);
      // After saving, always re-fetch latest saved from DB and re-merge with cached (or current) results!
      //const cached = localStorage.getItem(LS_RESULTS_KEY);
      //const baseResults = cached ? JSON.parse(cached) : results;
      const saved = await getSavedPaidArticles(token, "");
      // Add these logs
      console.log("Just saved this article:", article);
      console.log("Saved articles from DB:", saved);
      console.log("Current results array:", results);
      const merged = mergeResultsWithSaved(results, saved);
      setResults(merged);
      // Cache should still only update with baseResults (raw search), not with is_saved
      // (optional) cacheResults(baseResults, query);
    } catch (e) {
      alert("Save failed",e);
    }
    setSaving(false);
  };
  
  // --- Search handler ---
  const handleSearch = async () => {
    setLoading(true);
    try {
      if (searchMode === "saved") {
        const saved = await getSavedPaidArticles(token, "");
        setResults(saved.map(a => ({ ...a, is_saved: true })));
      } else if (searchMode === "live") {
        const [liveRaw, savedRaw] = await Promise.all([
          fetchPaidSearchResults(token, query, selectedProviders),
          getSavedPaidArticles(token, ""),
        ]);
        const merged = mergeResultsWithSaved(liveRaw, savedRaw);
        setResults(merged);
        cacheResults(liveRaw, query); // Save to cache for tab revisit
      } else if (searchMode === "both") {
        const saved = await getSavedPaidArticles(token, "");
        const liveRaw = await fetchPaidSearchResults(token, query, selectedProviders);
        // Don't show duplicates
        const savedLinks = new Set(saved.map(a => a.link && a.link.trim()));
        const merged = [
          ...saved.map(a => ({ ...a, is_saved: true })),
          ...liveRaw
            .filter(a => !savedLinks.has(a.link && a.link.trim()))
            .map(a => ({ ...a, is_saved: false })),
        ];
        setResults(merged);
      }
    } catch (err) {
      alert("Failed to fetch paid search results.");
    }
    setLoading(false);
  };

  // Show Save All if any results are not saved
  const showSaveAll = results.some((a) => !a.is_saved);

  return (
    <div>
      {/* Query + Provider Selector + Search */}
      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={query}
          placeholder="Enter search query..."
          onChange={(e) => setQuery(e.target.value)}
          className="flex-grow px-3 py-2 border rounded"
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSearch();
          }}
        />
        <select
          multiple
          value={selectedProviders}
          onChange={(e) => {
            const selected = Array.from(
              e.target.selectedOptions,
              (option) => option.value
            );
            setSelectedProviders(selected);
          }}
          className="border rounded px-2 py-1"
        >
          <option value="tavily">Tavily</option>
          <option value="serpapi">SERP API</option>
          {/* Add other providers as needed */}
        </select>
        <button
          onClick={handleSearch}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50 flex items-center gap-2"
        >
          {loading ? (
            <Loader className="animate-spin w-4 h-4" />
          ) : (
            <Search className="w-4 h-4" />
          )}
          Search
        </button>
      </div>

      {/* Search mode toggles */}
      <div className="flex gap-3 mb-4">
        <label>
          <input
            type="radio"
            checked={searchMode === "live"}
            onChange={() => setSearchMode("live")}
          />
          Live API
        </label>
        <label>
          <input
            type="radio"
            checked={searchMode === "saved"}
            onChange={() => setSearchMode("saved")}
          />
          Saved Only
        </label>
        <label>
          <input
            type="radio"
            checked={searchMode === "both"}
            onChange={() => setSearchMode("both")}
          />
          Both
        </label>
      </div>

      {/* Save All Button */}
      {showSaveAll && (
        <button
          onClick={handleSaveAll}
          disabled={saving}
          className="mb-4 px-4 py-2 bg-green-600 text-white rounded flex items-center gap-2"
        >
          {saving ? (
            <Loader className="animate-spin w-4 h-4" />
          ) : (
            <BookmarkPlus className="w-4 h-4" />
          )}
          Save All New
        </button>
      )}

      {/* Results Section */}
      {loading && <div>Loading...</div>}

      {!loading && results.length === 0 && (
        <div>No results found. Try another query.</div>
      )}

      {!loading && results.length > 0 && (
        <ul className="space-y-4">
          {results.map((article, idx) => (
            <li
              key={article.link || article.id || article.title || idx}
              className="border p-4 rounded shadow-sm"
            >
              <div className="flex items-center gap-2">
                <a
                  href={article.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-semibold text-blue-600 hover:underline"
                >
                  {article.title}
                </a>
                {article.is_saved ? (
                <span className="inline-flex items-center text-green-700 ml-2 text-xs">
                  <BookmarkCheck className="w-4 h-4 mr-1" />
                  Saved
                </span>
                  ) : (
                <button
                  className="inline-flex items-center text-gray-500 ml-2 text-xs hover:text-blue-600"
                  disabled={saving}
                  onClick={() => handleSaveArticle(article)}
                  title="Save this article"
                >
                  <BookmarkPlus className="w-4 h-4 mr-1" />
                  Save
                </button>
                )}
              </div>
              <div className="mt-2 flex gap-4 text-xs text-gray-500">
                <span><strong>Status:</strong> {article.status || "new"}</span>
                <span><strong>Category:</strong> {article.category || "uncategorized"}</span>
              </div>
              <p className="text-sm text-gray-700 mt-1">{article.summary}</p>
              <div className="mt-2 text-xs text-gray-500 flex gap-3">
                <span>
                  <strong>Source:</strong> {article.source || "Unknown"}
                </span>
                <span>
                  <strong>Score:</strong>{" "}
                  {article.relevance_score ?? article.score ?? "--"}
                </span>
                {(article.published_date || article.date || article.saved_at) && (
                  <>
                    <span>•</span>
                    <span>
                      <strong>Date:</strong>{" "}
                      {new Date(article.published_date || article.date || article.saved_at).toLocaleDateString()}
                    </span>
                  </>
                )}
              </div>
              {article.is_saved && (
                <div className="flex gap-4 items-center mt-2">
                    <select
                    value={article.status}
                    onChange={e => handleStatusChange(article.id, e.target.value)}
                    className="border px-2 py-1 rounded text-xs"
                    >
                    <option value="new">New</option>
                    <option value="shortlisted">Shortlisted</option>
                    <option value="final">Final</option>
                    </select>
                    
                    <select
                      value={article.category || "uncategorized"}
                      onChange={e => handleCategoryChange(article.id, e.target.value)}
                      className="border px-2 py-1 rounded text-xs"
                    >
                      {categories.map(cat => (
                        <option key={cat.id} value={cat.id}>
                          {cat.name}
                        </option>
                      ))}
                    </select>
                </div>
                )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default PaidSearchTab;