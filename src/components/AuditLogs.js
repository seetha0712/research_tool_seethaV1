import React, { useState, useEffect } from "react";
import { Activity, Filter, RefreshCw, User, Clock, Database } from "lucide-react";
import { getAuditLogs, getAuditStats } from "../api";

const AuditLogs = ({ token }) => {
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    action: "",
    username: "",
    resource_type: "",
  });
  const [limit, setLimit] = useState(100);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params = {
        limit,
        ...Object.fromEntries(Object.entries(filters).filter(([_, v]) => v !== "")),
      };
      const data = await getAuditLogs(token, params);
      setLogs(data);
    } catch (err) {
      console.error("Error fetching audit logs:", err);
      alert("Failed to load audit logs");
    }
    setLoading(false);
  };

  const fetchStats = async () => {
    try {
      const data = await getAuditStats(token);
      setStats(data);
    } catch (err) {
      console.error("Error fetching audit stats:", err);
    }
  };

  useEffect(() => {
    fetchLogs();
    fetchStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const formatDate = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  const getActionColor = (action) => {
    const colors = {
      LOGIN: "bg-green-100 text-green-700",
      LOGOUT: "bg-gray-100 text-gray-700",
      CREATE: "bg-blue-100 text-blue-700",
      UPDATE: "bg-yellow-100 text-yellow-700",
      DELETE: "bg-red-100 text-red-700",
      SYNC: "bg-purple-100 text-purple-700",
    };
    return colors[action] || "bg-gray-100 text-gray-700";
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Activity className="w-6 h-6 text-blue-600" />
          <h2 className="text-2xl font-bold">Audit Logs</h2>
        </div>
        <button
          onClick={() => {
            fetchLogs();
            fetchStats();
          }}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
          disabled={loading}
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="flex items-center gap-2 mb-2">
              <Database className="w-4 h-4 text-blue-600" />
              <span className="text-sm text-gray-600">Total Logs</span>
            </div>
            <div className="text-2xl font-bold">{stats.total_logs}</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-4 h-4 text-purple-600" />
              <span className="text-sm text-gray-600">Actions</span>
            </div>
            <div className="text-sm space-y-1">
              {Object.entries(stats.actions || {}).map(([action, count]) => (
                <div key={action} className="flex justify-between">
                  <span className={`px-2 py-0.5 rounded text-xs ${getActionColor(action)}`}>
                    {action}
                  </span>
                  <span className="font-medium">{count}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="flex items-center gap-2 mb-2">
              <User className="w-4 h-4 text-green-600" />
              <span className="text-sm text-gray-600">Active Users</span>
            </div>
            <div className="text-sm space-y-1 max-h-32 overflow-y-auto">
              {Object.entries(stats.users || {}).map(([username, count]) => (
                <div key={username} className="flex justify-between">
                  <span className="text-gray-700">{username}</span>
                  <span className="font-medium">{count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center gap-2 mb-3">
          <Filter className="w-4 h-4 text-gray-600" />
          <h3 className="font-semibold">Filters</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div>
            <label className="block text-sm font-medium mb-1">Action</label>
            <select
              value={filters.action}
              onChange={(e) => setFilters({ ...filters, action: e.target.value })}
              className="w-full px-3 py-2 border rounded"
            >
              <option value="">All</option>
              <option value="LOGIN">Login</option>
              <option value="SYNC">Sync</option>
              <option value="CREATE">Create</option>
              <option value="UPDATE">Update</option>
              <option value="DELETE">Delete</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Username</label>
            <input
              type="text"
              value={filters.username}
              onChange={(e) => setFilters({ ...filters, username: e.target.value })}
              placeholder="Filter by username"
              className="w-full px-3 py-2 border rounded"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Resource Type</label>
            <select
              value={filters.resource_type}
              onChange={(e) => setFilters({ ...filters, resource_type: e.target.value })}
              className="w-full px-3 py-2 border rounded"
            >
              <option value="">All</option>
              <option value="Article">Article</option>
              <option value="Source">Source</option>
              <option value="PaidArticle">PaidArticle</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Limit</label>
            <input
              type="number"
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value))}
              min={10}
              max={500}
              className="w-full px-3 py-2 border rounded"
            />
          </div>
        </div>
        <button
          onClick={fetchLogs}
          className="mt-3 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Apply Filters
        </button>
      </div>

      {/* Logs Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          {loading ? (
            <div className="p-8 text-center text-gray-500">Loading logs...</div>
          ) : logs.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No logs found</div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">User</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Resource</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Details</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">IP Address</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <Clock className="w-3 h-3 text-gray-400" />
                        {formatDate(log.timestamp)}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900">{log.username}</td>
                    <td className="px-4 py-3 text-sm">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getActionColor(log.action)}`}>
                        {log.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900">
                      {log.resource_type && (
                        <span className="text-gray-600">
                          {log.resource_type}
                          {log.resource_id && ` #${log.resource_id}`}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {log.details && (
                        <details className="cursor-pointer">
                          <summary className="text-blue-600 hover:underline">View</summary>
                          <pre className="mt-2 text-xs bg-gray-50 p-2 rounded max-w-xs overflow-x-auto">
                            {JSON.stringify(log.details, null, 2)}
                          </pre>
                        </details>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">{log.ip_address || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};

export default AuditLogs;
