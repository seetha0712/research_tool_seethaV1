import React, { useState } from "react";
import { addSource, uploadFile } from "../api"; // your new API utility

const initialState = {
  name: "",
  url: "",
  type: "rss",
  provider: "",
  query: "",
  file: null, // for PDF
};

const AddSourceModal = ({
  showAddSource,
  setShowAddSource,
  fetchSources, // <-- a callback to refresh the list after adding!
  token,
}) => {
  const [form, setForm] = useState(initialState);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (!showAddSource) return null;

  const handleChange = (e) => {
    const { name, value, files } = e.target;
    if (name === "file") {
      setForm({ ...form, file: files[0] });
    } else {
      setForm({ ...form, [name]: value });
    }
  };

  const handleSubmit = async () => {
    setError("");
    setSubmitting(true);
    try {
      if (form.type === "pdf") {
        // 1. Upload file to backend and register source
        if (!form.file) throw new Error("Please select a PDF file.");
        await uploadFile(form.file, token); // uploadFile in api.js
      } else {
        // 2. Add RSS or API source to backend
        const payload = {
          name: form.name,
          url: form.type === "rss" ? form.url : undefined,
          type: form.type,
          provider: form.type === "api" ? form.provider : undefined,
          query: form.type === "api" ? form.query : undefined,
        };
        await addSource(payload, token); // addSource in api.js
      }
      fetchSources && fetchSources(); // refresh list
      setShowAddSource(false);
      setForm(initialState);
    } catch (err) {
      setError(err.message || "Failed to add source");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h3 className="text-lg font-semibold mb-4">Add Source</h3>

        <div className="space-y-4">
          {/* Source Type Dropdown */}
          <div>
            <label className="block text-sm font-medium mb-1">Source Type</label>
            <select
              name="type"
              value={form.type}
              onChange={handleChange}
              className="w-full px-3 py-2 border rounded-lg"
            >
              <option value="rss">RSS Feed</option>
              <option value="pdf">PDF Upload</option>
              <option value="api">API Search</option>
            </select>
          </div>

          {/* Name */}
          <div>
            <label className="block text-sm font-medium mb-1">Source Name</label>
            <input
              name="name"
              type="text"
              value={form.name}
              onChange={handleChange}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="e.g., Anthropic Blog or Tavily Search"
            />
          </div>

          {/* Conditional fields */}
          {form.type === "rss" && (
            <div>
              <label className="block text-sm font-medium mb-1">RSS Feed URL</label>
              <input
                name="url"
                type="text"
                value={form.url}
                onChange={handleChange}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="https://example.com/feed"
              />
            </div>
          )}

          {form.type === "pdf" && (
            <div>
              <label className="block text-sm font-medium mb-1">PDF File</label>
              <input
                name="file"
                type="file"
                accept="application/pdf"
                onChange={handleChange}
                className="w-full"
              />
            </div>
          )}

          {form.type === "api" && (
            <>
              <div>
                <label className="block text-sm font-medium mb-1">API Provider</label>
                <input
                  name="provider"
                  type="text"
                  value={form.provider}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="e.g., tavily"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Query / Topic</label>
                <input
                  name="query"
                  type="text"
                  value={form.query}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="e.g., GenAI trends"
                />
              </div>
            </>
          )}

          {error && <div className="text-red-600">{error}</div>}
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={() => {
              setShowAddSource(false);
              setForm(initialState);
            }}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            disabled={submitting}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            disabled={submitting}
          >
            {submitting ? "Adding..." : "Add Source"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AddSourceModal;