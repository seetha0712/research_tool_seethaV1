import React, { useState, useEffect } from "react";
import { Trash2, RefreshCw, Database, AlertTriangle } from "lucide-react";
import axios from "axios";

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";

const Admin = ({ token }) => {
  const [stats, setStats] = useState(null);
  const [selectedTable, setSelectedTable] = useState("articles");
  const [tableData, setTableData] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [loading, setLoading] = useState(false);

  const tables = [
    { key: "articles", label: "Articles" },
    { key: "sources", label: "Sources" },
    { key: "paid_articles", label: "Paid Articles" },
    { key: "users", label: "Users" },
    { key: "files", label: "Files" },
    { key: "notes", label: "Notes" },
  ];

  // Fetch stats
  const fetchStats = async () => {
    try {
      const res = await axios.get(`${API_BASE}/admin/stats`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setStats(res.data);
    } catch (err) {
      console.error("Error fetching stats:", err);
    }
  };

  // Fetch table data
  const fetchTableData = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/admin/table/${selectedTable}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setTableData(res.data);
      setSelectedIds([]);
    } catch (err) {
      console.error("Error fetching table data:", err);
      alert("Failed to load table data");
    }
    setLoading(false);
  };

  // Delete selected items
  const handleDelete = async () => {
    if (selectedIds.length === 0) {
      alert("No items selected");
      return;
    }

    if (!window.confirm(`Delete ${selectedIds.length} items from ${selectedTable}?`)) {
      return;
    }

    setLoading(true);
    try {
      await axios.delete(`${API_BASE}/admin/delete`, {
        headers: { Authorization: `Bearer ${token}` },
        data: {
          table: selectedTable,
          ids: selectedIds,
        },
      });

      alert(`Deleted ${selectedIds.length} items successfully`);
      fetchStats();
      fetchTableData();
    } catch (err) {
      console.error("Error deleting:", err);
      alert("Delete failed: " + (err.response?.data?.detail || "Unknown error"));
    }
    setLoading(false);
  };

  // Toggle selection
  const toggleSelection = (id) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter((i) => i !== id));
    } else {
      setSelectedIds([...selectedIds, id]);
    }
  };

  // Select all
  const selectAll = () => {
    setSelectedIds(tableData.map((item) => item.id));
  };

  // Deselect all
  const deselectAll = () => {
    setSelectedIds([]);
  };

  useEffect(() => {
    fetchStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (selectedTable) {
      fetchTableData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTable]);

  return (
    <div className="p-6 space-y-6">
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
        <AlertTriangle className="w-5 h-5 text-red-600" />
        <div>
          <h3 className="font-semibold text-red-800">Admin Panel</h3>
          <p className="text-sm text-red-700">
            Warning: Deletions are permanent and cannot be undone!
          </p>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {Object.entries(stats).map(([key, value]) => (
            <div key={key} className="bg-white p-4 rounded-lg shadow">
              <div className="flex items-center gap-2 mb-2">
                <Database className="w-4 h-4 text-blue-600" />
                <span className="text-sm text-gray-600 capitalize">
                  {key.replace("_", " ")}
                </span>
              </div>
              <div className="text-2xl font-bold">{value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Table selector */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <label className="font-medium">Select Table:</label>
            <select
              value={selectedTable}
              onChange={(e) => setSelectedTable(e.target.value)}
              className="px-3 py-2 border rounded"
            >
              {tables.map((t) => (
                <option key={t.key} value={t.key}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={fetchTableData}
            disabled={loading}
            className="px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        {/* Selection controls */}
        {tableData.length > 0 && (
          <div className="flex items-center justify-between mb-4 pb-4 border-b">
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-600">
                {selectedIds.length} of {tableData.length} selected
              </span>
              <button
                onClick={selectAll}
                className="text-sm text-blue-600 hover:underline"
              >
                Select All
              </button>
              <button
                onClick={deselectAll}
                className="text-sm text-blue-600 hover:underline"
              >
                Deselect All
              </button>
            </div>

            <button
              onClick={handleDelete}
              disabled={selectedIds.length === 0 || loading}
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 flex items-center gap-2"
            >
              <Trash2 className="w-4 h-4" />
              Delete Selected ({selectedIds.length})
            </button>
          </div>
        )}

        {/* Table data */}
        {loading ? (
          <div className="text-center py-8">Loading...</div>
        ) : tableData.length === 0 ? (
          <div className="text-center py-8 text-gray-500">No data in this table</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Select
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    ID
                  </th>
                  {tableData[0] &&
                    Object.keys(tableData[0])
                      .filter((k) => k !== "id" && k !== "hashed_password")
                      .slice(0, 5)
                      .map((key) => (
                        <th
                          key={key}
                          className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase"
                        >
                          {key}
                        </th>
                      ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {tableData.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(item.id)}
                        onChange={() => toggleSelection(item.id)}
                        className="rounded"
                      />
                    </td>
                    <td className="px-4 py-3 text-sm font-medium">{item.id}</td>
                    {Object.entries(item)
                      .filter(([k]) => k !== "id" && k !== "hashed_password")
                      .slice(0, 5)
                      .map(([key, value]) => (
                        <td key={key} className="px-4 py-3 text-sm text-gray-900">
                          {typeof value === "object"
                            ? JSON.stringify(value).substring(0, 50) + "..."
                            : String(value).substring(0, 100)}
                        </td>
                      ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default Admin;
