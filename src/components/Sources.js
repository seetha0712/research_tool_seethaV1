import React, { useEffect, useState, useRef } from "react";
import { Plus, Trash2 } from "lucide-react";
import {
  getSources,
  addSource,
  uploadFile,
  deleteSource,
  toggleSource
} from "../api";

//const token = process.env.REACT_APP_JWT_TOKEN;
//const token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzZWV0aGEiLCJ1c2VyX2lkIjoxLCJleHAiOjE3NTMyNjg0MDN9.PcS3-Zdg54v6IZIvCNTqCEI-E4v0YdkvmTDu-l7S1xk"
//console.log("TOKEN in sources:", token)

const groupBy = (arr, key) =>
  arr.reduce((acc, item) => {
    (acc[item[key]] = acc[item[key]] || []).push(item);
    return acc;
  }, {});

const Sources = ({ token }) => {
  const [sources, setSources] = useState([]);

  const [showAddSource, setShowAddSource] = useState(false);
  const [addSourceType, setAddSourceType] = useState("rss");
  const [addSourceName, setAddSourceName] = useState("");
  const [addSourceUrl, setAddSourceUrl] = useState("");
  const [addSourceProvider, setAddSourceProvider] = useState("");
  const [addSourceQuery, setAddSourceQuery] = useState("");
  const [addSourceFile, setAddSourceFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const fileInputRef = useRef();

  useEffect(() => {
    fetchSources();
    // eslint-disable-next-line
  }, []);

  const fetchSources = async () => {
    setLoading(true);
    setErrorMsg("");
    try {
      const data = await getSources(token);
      setSources(data);
    } catch (err) {
      setErrorMsg("Could not load sources.");
      setSources([]);
    }
    setLoading(false);
  };

  const handleAddSource = async (e) => {
    e.preventDefault();
    setErrorMsg("");
    try {
      if (addSourceType === "pdf") {
        if (!addSourceFile) {
          alert("Please select a PDF file.");
          return;
        }
        await uploadFile(addSourceFile, token);
      } else {
        const payload = {
          name: addSourceName,
          type: addSourceType,
          url: addSourceType === "rss" || addSourceType === "api" ? addSourceUrl : undefined,
          provider: addSourceType === "api" ? addSourceProvider : undefined,
          query: addSourceType === "api" ? addSourceQuery : undefined,
        };
        await addSource(payload, token);
      }
      // Reset modal state
      setShowAddSource(false);
      setAddSourceType("rss");
      setAddSourceName("");
      setAddSourceUrl("");
      setAddSourceProvider("");
      setAddSourceQuery("");
      setAddSourceFile(null);
      if (fileInputRef.current) fileInputRef.current.value = null;
      fetchSources();
    } catch (err) {
      setErrorMsg("Error adding source: " + (err?.response?.data?.detail || err.message));
    }
  };

  const handleDeleteSource = async (id) => {
    if (window.confirm("Are you sure you want to delete this source?")) {
      try {
        await deleteSource(id, token);
        fetchSources();
      } catch (err) {
        setErrorMsg("Delete failed.");
      }
    }
  };

  const handleToggleActive = async (id) => {
    try {
      await toggleSource(id, token);
      fetchSources();
    } catch (err) {
      setErrorMsg("Could not toggle active state.");
    }
  };

  // Group sources by type
  const { rss = [], pdf = [], api = [] } = groupBy(sources, "type");

  return (
    <div className="p-6 space-y-6">
      {/* Error Display */}
      {errorMsg && (
        <div className="bg-red-100 text-red-700 px-4 py-2 rounded">{errorMsg}</div>
      )}
      {/* Loading Display */}
      {loading && (
        <div className="bg-blue-50 text-blue-600 px-4 py-2 rounded">Loading...</div>
      )}

      {/* RSS SOURCES */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold">Sources</h3>
          <button
            onClick={() => setShowAddSource(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Add Source
          </button>
        </div>
        <div className="space-y-3">
          {rss.length === 0 && (
            <p className="text-gray-500">No RSS feeds added yet.</p>
          )}
          {rss.map((source) => (
            <div key={source.id} className="flex items-center justify-between p-4 border rounded-lg">
              <div>
                <p className="font-medium text-gray-900">{source.name}</p>
                <p className="text-sm text-gray-500">{source.url}</p>
                {source.last_synced && (
                  <p className="text-xs text-gray-400 mt-1">
                    Last sync: {new Date(source.last_synced).toLocaleString()}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={source.active}
                    onChange={() => handleToggleActive(source.id)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
                <button
                  className="p-2 text-red-600 hover:bg-red-50 rounded"
                  onClick={() => handleDeleteSource(source.id)}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* PDF UPLOADS */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Uploaded PDFs</h3>
        {pdf.length === 0 ? (
          <p className="text-gray-500">No files uploaded yet.</p>
        ) : (
          pdf.map((source) => (
            <div key={source.id} className="flex items-center justify-between p-4 border rounded-lg">
              <div>
                <p className="font-medium text-gray-900">{source.name}</p>
                <p className="text-sm text-gray-500">{source.file_path}</p>
              </div>
            </div>
          ))
        )}
      </div>

      {/* PAID/API INTEGRATION */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Paid Sources Integration</h3>
        {api.length === 0 ? (
          <p className="text-gray-500">No API sources added.</p>
        ) : (
          api.map((source) => (
            <div key={source.id} className="flex items-center justify-between p-4 border rounded-lg">
              <div>
                <p className="font-medium">{source.name}</p>
                <p className="text-sm text-gray-500">{source.provider} - {source.query}</p>
              </div>
              <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm">
                Connected
              </span>
              <button
                className="p-2 text-red-600 hover:bg-red-50 rounded"
                onClick={() => handleDeleteSource(source.id)}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))
        )}
      </div>

      {/* ADD SOURCE MODAL */}
      {showAddSource && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-4">Add Source</h3>
            <form className="space-y-4" onSubmit={handleAddSource}>
              <div>
                <label className="block text-sm font-medium mb-1">Source Type</label>
                <select
                  value={addSourceType}
                  onChange={e => setAddSourceType(e.target.value)}
                  className="w-full px-3 py-2 border rounded"
                >
                  <option value="rss">RSS Feed</option>
                  <option value="pdf">PDF Upload</option>
                  <option value="api">API Integration</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Name</label>
                <input
                  value={addSourceName}
                  onChange={e => setAddSourceName(e.target.value)}
                  required
                  placeholder="e.g. Forrester, OpenAI Blog"
                  className="w-full px-3 py-2 border rounded"
                />
              </div>
              {(addSourceType === "rss" || addSourceType === "api") && (
                <div>
                  <label className="block text-sm font-medium mb-1">Feed URL or API Endpoint</label>
                  <input
                    value={addSourceUrl}
                    onChange={e => setAddSourceUrl(e.target.value.trim())}
                    required={addSourceType !== "pdf"}
                    placeholder="https://example.com/feed"
                    className="w-full px-3 py-2 border rounded"
                  />
                </div>
              )}
              {addSourceType === "api" && (
                <>
                  <div>
                    <label className="block text-sm font-medium mb-1">Provider (e.g. tavily)</label>
                    <input
                      value={addSourceProvider}
                      onChange={e => setAddSourceProvider(e.target.value)}
                      placeholder="tavily"
                      className="w-full px-3 py-2 border rounded"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Query (for API search)</label>
                    <input
                      value={addSourceQuery}
                      onChange={e => setAddSourceQuery(e.target.value)}
                      placeholder="GenAI, Finance, etc"
                      className="w-full px-3 py-2 border rounded"
                    />
                  </div>
                </>
              )}
              {addSourceType === "pdf" && (
                <div>
                  <label className="block text-sm font-medium mb-1">PDF File</label>
                  <input
                    type="file"
                    accept="application/pdf"
                    ref={fileInputRef}
                    onChange={e => setAddSourceFile(e.target.files[0])}
                    className="w-full"
                  />
                </div>
              )}
              <div className="flex justify-end gap-3 mt-6">
                <button
                  onClick={() => setShowAddSource(false)}
                  type="button"
                  className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Add Source
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};

export default Sources;