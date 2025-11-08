import React, { useEffect, useMemo, useState } from "react";
import { FileText, Star, Check, Calendar, Bookmark, RefreshCw } from "lucide-react";
import api from "../api";

const fmtDDMonYYYY = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const dd = String(d.getDate()).padStart(2, "0");
  return `${dd}-${months[d.getMonth()]}-${d.getFullYear()}`;
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

const Dashboard = ({ token, getStatusColor, refreshKey = 0 }) => {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

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
        params, // backend should accept from_date, to_date (YYYY-MM-DD)
      });
      setMetrics(res.data);
    } catch (e) {
      console.error("Failed to load metrics", e);
      setMetrics(null);
    }
    setLoading(false);
  };

  // Fetch whenever token, date range, or external refreshKey changes
  useEffect(() => {
    if (!token) return;
    fetchMetrics();
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
      {/* Controls */}
      <div className="bg-white rounded-lg shadow p-4 flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-sm text-gray-600">Quick range:</span>
          <div className="flex gap-2 flex-wrap">
            {quickRanges.map((r) => (
              <button
                key={r.label}
                onClick={() => applyQuickRange(r.label)}
                className={`px-3 py-1 rounded border text-sm ${
                  selectedQuick === r.label
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

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
              className="px-3 py-2 border rounded text-sm"
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
              className="px-3 py-2 border rounded text-sm"
            />
          </div>

          <button
            onClick={fetchMetrics}
            className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
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
    <div className="space-y-3">
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
                  ? JSON.stringify(item.source)
                  : item.source) || "—"}{" "}
                •{" "}
                {item.date
                  ? item.date.substring(0, 10)
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