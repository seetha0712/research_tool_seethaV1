import React, { useEffect, useMemo, useState } from "react";
import { FileText, Star, Check, Calendar, Bookmark, TrendingUp, Database, Trash2, ChevronDown, ChevronUp, AlertCircle, Clock } from "lucide-react";
import api from "../api";
import { getSourceAnalytics, getSyncHistory, deleteSyncHistory, deleteOldSyncHistory } from "../api";

const fmtDDMonYYYY = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const dd = String(d.getDate()).padStart(2, "0");
  return `${dd}-${months[d.getMonth()]}-${d.getFullYear()}`;
};

const fmtDateTime = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return `${fmtDDMonYYYY(iso)} ${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
};

// Helper: format date to YYYY-MM-DD
const toYMD = (d) => d.toISOString().slice(0, 10);
// Helper: today & N days ago
const today = () => new Date();
const daysAgo = (n) => {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d;
};

const quickRanges = [
  { label: "Last 7 days", from: () => daysAgo(7), to: () => today() },
  { label: "Last 30 days", from: () => daysAgo(30), to: () => today() },
  { label: "Last 90 days", from: () => daysAgo(90), to: () => today() },
  { label: "All time", from: () => new Date("2000-01-01"), to: () => today() },
];

const Dashboard = ({ token, getStatusColor, refreshKey = 0, isAdmin = false }) => {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  // Source Analytics state
  const [sourceAnalytics, setSourceAnalytics] = useState(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [showSourceAnalytics, setShowSourceAnalytics] = useState(true);

  // Sync History state
  const [syncHistory, setSyncHistory] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [showSyncHistory, setShowSyncHistory] = useState(true);
  const [expandedSyncId, setExpandedSyncId] = useState(null);

  // Date state (defaults to last 30 days)
  const [fromDate, setFromDate] = useState(toYMD(daysAgo(30)));
  const [toDate, setToDate] = useState(toYMD(today()));
  const [selectedQuick, setSelectedQuick] = useState("Last 30 days");

  const params = useMemo(
    () => ({
      from_date: fromDate || undefined,
      to_date: toDate || undefined,
    }),
    [fromDate, toDate]
  );

  const fetchMetrics = async () => {
    setLoading(true);
    try {
      const res = await api.get("/dashboard/metrics", {
        headers: { Authorization: `Bearer ${token}` },
        params,
      });
      setMetrics(res.data);
    } catch (e) {
      console.error("Failed to load metrics", e);
      setMetrics(null);
    }
    setLoading(false);
  };

  const fetchSourceAnalytics = async () => {
    setAnalyticsLoading(true);
    try {
      const data = await getSourceAnalytics(token, 30);
      setSourceAnalytics(data);
    } catch (e) {
      console.error("Failed to load source analytics", e);
      setSourceAnalytics(null);
    }
    setAnalyticsLoading(false);
  };

  const fetchSyncHistory = async () => {
    setHistoryLoading(true);
    try {
      const data = await getSyncHistory(token, { limit: 20 });
      setSyncHistory(data);
    } catch (e) {
      console.error("Failed to load sync history", e);
      setSyncHistory(null);
    }
    setHistoryLoading(false);
  };

  const handleDeleteSyncRecord = async (syncId) => {
    if (!window.confirm("Delete this sync history record?")) return;
    try {
      await deleteSyncHistory(token, syncId);
      fetchSyncHistory();
    } catch (e) {
      console.error("Failed to delete sync history", e);
      alert("Failed to delete sync history record");
    }
  };

  const handleDeleteOldHistory = async () => {
    if (!window.confirm("Delete all sync history records older than 360 days?")) return;
    try {
      const result = await deleteOldSyncHistory(token, 360);
      alert(`Deleted ${result.deleted_count} old records`);
      fetchSyncHistory();
    } catch (e) {
      console.error("Failed to delete old sync history", e);
      alert("Failed to delete old sync history");
    }
  };

  // Fetch whenever token, date range, or external refreshKey changes
  useEffect(() => {
    if (!token) return;
    fetchMetrics();
    fetchSourceAnalytics();
    fetchSyncHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, params.from_date, params.to_date, refreshKey]);

  const applyQuickRange = (label) => {
    const range = quickRanges.find((r) => r.label === label);
    if (!range) return;
    setSelectedQuick(label);
    setFromDate(toYMD(range.from()));
    setToDate(toYMD(range.to()));
  };

  if (loading) return <div className="p-6">Loading dashboard...</div>;
  if (!metrics) return <div className="p-6 text-red-500">Error loading dashboard data.</div>;
  const combinedTotal = (metrics.total_articles || 0) + (metrics.total_paid_articles || 0);

  return (
    <div className="p-6 space-y-6">
      {/* Date Filter Controls */}
      <div className="bg-white rounded-lg shadow p-4 space-y-3">
        {/* Quick Filters */}
        <div>
          <label className="text-sm font-medium text-gray-700 mb-2 block">Quick Filters:</label>
          <div className="flex flex-wrap gap-2">
            {quickRanges.map((r) => (
              <button
                key={r.label}
                onClick={() => applyQuickRange(r.label)}
                className={`px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
                  selectedQuick === r.label
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50 hover:border-gray-400"
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

        {/* Custom Date Range */}
        <div className="border-t pt-3">
          <label className="text-sm font-medium text-gray-700 mb-2 block">Or Custom Range:</label>
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600">From</label>
              <input
                type="date"
                value={fromDate}
                max={toDate}
                onChange={(e) => {
                  setSelectedQuick(""); // custom range
                  setFromDate(e.target.value);
                }}
                className="px-3 py-2 border rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600">To</label>
              <input
                type="date"
                value={toDate}
                min={fromDate}
                max={toYMD(today())}
                onChange={(e) => {
                  setSelectedQuick("");
                  setToDate(e.target.value);
                }}
                className="px-3 py-2 border rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            {selectedQuick && (
              <span className="text-sm text-blue-600 font-medium px-3 py-2 bg-blue-50 rounded">
                {selectedQuick}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <MetricCard
          label="Total Articles"
          value={combinedTotal}
          icon={<FileText className="w-8 h-8 text-blue-500" />}
        />
        <MetricCard
          label="Paid Articles"
          value={metrics.total_paid_articles}
          icon={<Bookmark className="w-8 h-8 text-indigo-500" />}
        />
        <MetricCard
          label="Shortlisted"
          value={metrics.shortlisted}
          icon={<Star className="w-8 h-8 text-yellow-500" />}
        />
        <MetricCard
          label="Final Selection"
          value={metrics.final}
          icon={<Check className="w-8 h-8 text-green-500" />}
        />
       <MetricCard
          label="Range"
          value={
            fromDate && toDate
              ? `${fmtDDMonYYYY(fromDate)} → ${fmtDDMonYYYY(toDate)}`
              : "All time"
          }
          smallValue={true}
          icon={<Calendar className="w-8 h-8 text-purple-500" />}
        />
      </div>

      {/* Source Analytics Section */}
      <div className="bg-white rounded-lg shadow">
        <div
          className="p-4 border-b flex items-center justify-between cursor-pointer hover:bg-gray-50"
          onClick={() => setShowSourceAnalytics(!showSourceAnalytics)}
        >
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-green-600" />
            <h3 className="text-lg font-semibold">Source Effectiveness Analytics</h3>
            {sourceAnalytics?.overall_stats && (
              <span className="text-sm text-gray-500 ml-2">
                ({sourceAnalytics.overall_stats.active_sources} active sources,
                Avg Score: {sourceAnalytics.overall_stats.avg_score})
              </span>
            )}
          </div>
          {showSourceAnalytics ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </div>

        {showSourceAnalytics && (
          <div className="p-4">
            {analyticsLoading ? (
              <div className="text-center py-4 text-gray-500">Loading analytics...</div>
            ) : sourceAnalytics?.sources?.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 text-left">
                      <th className="px-4 py-3 font-semibold">Source</th>
                      <th className="px-4 py-3 font-semibold">Type</th>
                      <th className="px-4 py-3 font-semibold text-right">Total</th>
                      <th className="px-4 py-3 font-semibold text-right">Avg Score</th>
                      <th className="px-4 py-3 font-semibold text-right">High Score %</th>
                      <th className="px-4 py-3 font-semibold">Top Categories</th>
                      <th className="px-4 py-3 font-semibold">Last Synced</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sourceAnalytics.sources.map((src, idx) => (
                      <tr key={src.source_id} className={idx % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                        <td className="px-4 py-3 font-medium">{src.source_name}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            src.source_type === 'rss' ? 'bg-orange-100 text-orange-700' :
                            src.source_type === 'pdf' ? 'bg-blue-100 text-blue-700' :
                            'bg-purple-100 text-purple-700'
                          }`}>
                            {src.source_type.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">{src.total_articles}</td>
                        <td className="px-4 py-3 text-right">
                          <span className={`font-bold ${
                            src.avg_score >= 70 ? 'text-green-600' :
                            src.avg_score >= 40 ? 'text-yellow-600' :
                            'text-red-600'
                          }`}>
                            {src.avg_score}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className={`${src.high_score_percentage >= 50 ? 'text-green-600' : 'text-gray-600'}`}>
                            {src.high_score_percentage}%
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-1">
                            {src.top_categories?.slice(0, 2).map((cat, i) => (
                              <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">
                                {cat.category} ({cat.count})
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-gray-500 text-xs">
                          {src.last_synced ? fmtDateTime(src.last_synced) : "Never"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-4 text-gray-500">No source analytics available yet.</div>
            )}
          </div>
        )}
      </div>

      {/* Sync History Section */}
      <div className="bg-white rounded-lg shadow">
        <div
          className="p-4 border-b flex items-center justify-between cursor-pointer hover:bg-gray-50"
          onClick={() => setShowSyncHistory(!showSyncHistory)}
        >
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-blue-600" />
            <h3 className="text-lg font-semibold">Sync History</h3>
            {syncHistory && (
              <span className="text-sm text-gray-500 ml-2">
                ({syncHistory.total} total syncs)
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {isAdmin && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteOldHistory();
                }}
                className="px-3 py-1 text-xs bg-red-50 text-red-600 rounded hover:bg-red-100"
                title="Delete records older than 360 days"
              >
                Clean Old Records
              </button>
            )}
            {showSyncHistory ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </div>
        </div>

        {showSyncHistory && (
          <div className="p-4">
            {historyLoading ? (
              <div className="text-center py-4 text-gray-500">Loading sync history...</div>
            ) : syncHistory?.history?.length > 0 ? (
              <div className="space-y-2">
                {syncHistory.history.map((sync) => (
                  <SyncHistoryRow
                    key={sync.id}
                    sync={sync}
                    expanded={expandedSyncId === sync.id}
                    onToggle={() => setExpandedSyncId(expandedSyncId === sync.id ? null : sync.id)}
                    onDelete={isAdmin ? () => handleDeleteSyncRecord(sync.id) : null}
                  />
                ))}
              </div>
            ) : (
              <div className="text-center py-4 text-gray-500">No sync history available yet. Run a sync to see results here.</div>
            )}
          </div>
        )}
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ActivityPanel
          title="Recent Main Articles"
          items={metrics.latest_articles}
          getStatusColor={getStatusColor}
        />
        <ActivityPanel
          title="Recent Paid Search Results"
          items={metrics.latest_paid}
          icon={<Bookmark className="inline w-4 h-4 text-indigo-500" />}
        />
      </div>
    </div>
  );
};

// Sync History Row Component
const SyncHistoryRow = ({ sync, expanded, onToggle, onDelete }) => {
  const hasErrors = sync.total_errors > 0;
  const scores = sync.scores_breakdown || {};

  return (
    <div className={`border rounded-lg ${hasErrors ? 'border-red-200' : 'border-gray-200'}`}>
      <div
        className={`p-3 flex items-center justify-between cursor-pointer hover:bg-gray-50 ${hasErrors ? 'bg-red-50' : ''}`}
        onClick={onToggle}
      >
        <div className="flex items-center gap-4">
          <Clock className="w-4 h-4 text-gray-400" />
          <span className="text-sm font-medium">{fmtDateTime(sync.sync_timestamp)}</span>
          <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium">
            {sync.total_articles_fetched} articles
          </span>
          <span className="text-xs text-gray-500">
            {sync.total_sources_synced} sources
          </span>
          {hasErrors && (
            <span className="flex items-center gap-1 px-2 py-1 bg-red-100 text-red-700 rounded text-xs font-medium">
              <AlertCircle className="w-3 h-3" />
              {sync.total_errors} errors
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-2 text-xs">
            <span className="px-2 py-1 bg-green-100 text-green-700 rounded" title="High (70+)">
              H: {scores.high || 0}
            </span>
            <span className="px-2 py-1 bg-yellow-100 text-yellow-700 rounded" title="Medium (40-69)">
              M: {scores.medium || 0}
            </span>
            <span className="px-2 py-1 bg-red-100 text-red-700 rounded" title="Low (<40)">
              L: {scores.low || 0}
            </span>
          </div>
          <span className="text-xs text-gray-500">{sync.duration_seconds}s</span>
          {onDelete && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="p-1 text-red-500 hover:bg-red-100 rounded"
              title="Delete this record"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </div>

      {expanded && (
        <div className="border-t p-4 bg-gray-50 space-y-4">
          {/* Sources Breakdown */}
          {sync.sources_breakdown?.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold mb-2">By Source:</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                {sync.sources_breakdown.map((src, idx) => (
                  <div key={idx} className="p-2 bg-white rounded border text-sm">
                    <div className="font-medium">{src.source_name}</div>
                    <div className="text-xs text-gray-500">
                      {src.count} articles • Avg: {src.avg_score}
                    </div>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {Object.entries(src.categories || {}).map(([cat, count]) => (
                        <span key={cat} className="px-1 bg-gray-100 rounded text-xs">
                          {cat}: {count}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Categories Breakdown */}
          {Object.keys(sync.categories_breakdown || {}).length > 0 && (
            <div>
              <h4 className="text-sm font-semibold mb-2">By Category:</h4>
              <div className="flex flex-wrap gap-2">
                {Object.entries(sync.categories_breakdown).map(([cat, count]) => (
                  <span key={cat} className="px-2 py-1 bg-white border rounded text-sm">
                    {cat}: <strong>{count}</strong>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Errors */}
          {sync.errors?.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold mb-2 text-red-600">Errors:</h4>
              <div className="space-y-1">
                {sync.errors.map((err, idx) => (
                  <div key={idx} className="p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                    <strong>{err.source_name}:</strong> {err.error}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sync Params */}
          <div className="text-xs text-gray-500">
            Sync params: limit={sync.sync_params?.limit || "N/A"}, from_date={sync.sync_params?.from_date || "N/A"}
          </div>
        </div>
      )}
    </div>
  );
};

// Sub-components

const MetricCard = ({ label, value, icon, smallValue = false }) => (
  <div className="bg-white rounded-lg shadow p-6 flex flex-col justify-between">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm text-gray-600">{label}</p>
        <p className={`${smallValue ? "text-sm" : "text-2xl"} font-bold text-gray-900`}>
          {value}
        </p>
      </div>
      {icon}
    </div>
  </div>
);

const ActivityPanel = ({ title, items, getStatusColor, icon }) => (
  <div className="bg-white rounded-lg shadow p-6">
    <h3 className="text-lg font-semibold mb-4">{title}</h3>
    <div className="max-h-96 overflow-y-auto space-y-3">
      {(!items || items.length === 0) && (
        <div className="text-sm text-gray-500">No activity yet.</div>
      )}
      {items &&
        items.map((item, idx) => (
          <div
            key={idx}
            className="flex items-center justify-between py-2 border-b last:border-0"
          >
            <div className="flex-1">
              <p className="font-medium text-gray-900 flex items-center gap-2">
                {icon}
                {item.url ? (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:underline"
                  >
                    {item.title}
                  </a>
                ) : (
                  item.title
                )}
              </p>
              <p className="text-sm text-gray-500">
                {(typeof item.source === "object"
                  ? (item.source?.name || item.source_name || "—")
                  : (item.source || item.source_name || "—"))}{" "}
                •{" "}
                {item.date
                  ? fmtDDMonYYYY(item.date)
                  : "—"}
              </p>
            </div>
            {item.status && getStatusColor && (
              <span
                className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(
                  item.status
                )}`}
              >
                {item.status}
              </span>
            )}
            {item.score !== undefined && (
              <span className="ml-2 text-xs text-indigo-600 font-bold">
                Score: {item.score}
              </span>
            )}
          </div>
        ))}
    </div>
  </div>
);

export default Dashboard;
