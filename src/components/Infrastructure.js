import React, { useState, useEffect, useCallback } from "react";
import {
  Server, Database, Play, Square, RefreshCw, AlertTriangle,
  CheckCircle, XCircle, Clock, User, Settings
} from "lucide-react";
import {
  getInfrastructureConfig,
  getServicesStatus,
  startService,
  stopService,
  getInfrastructureActivity
} from "../api";

const Infrastructure = ({ token }) => {
  const [config, setConfig] = useState(null);
  const [services, setServices] = useState([]);
  const [activity, setActivity] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState({});
  const [error, setError] = useState(null);
  const [confirmAction, setConfirmAction] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [configRes, activityRes] = await Promise.all([
        getInfrastructureConfig(token),
        getInfrastructureActivity(token, 10)
      ]);
      setConfig(configRes);
      setActivity(activityRes.activities || []);

      if (configRes.render_configured) {
        try {
          const statusRes = await getServicesStatus(token);
          setServices(statusRes.services || []);
        } catch (statusErr) {
          console.error("Failed to fetch service status:", statusErr);
          setServices(configRes.services.map(s => ({
            ...s,
            status: "unknown",
            suspended: null,
            error: "Unable to fetch status"
          })));
        }
      }
      setLastRefresh(new Date());
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Failed to load infrastructure data");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAction = async (serviceKey, action) => {
    setActionLoading(prev => ({ ...prev, [serviceKey]: true }));
    setError(null);

    try {
      if (action === "start") {
        await startService(token, serviceKey);
      } else {
        await stopService(token, serviceKey);
      }
      setConfirmAction(null);
      await fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || `Failed to ${action} service`);
    } finally {
      setActionLoading(prev => ({ ...prev, [serviceKey]: false }));
    }
  };

  const getServiceIcon = (type) => {
    if (type === "postgres") return <Database className="w-5 h-5" />;
    return <Server className="w-5 h-5" />;
  };

  const getStatusBadge = (service) => {
    if (service.error) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
          <AlertTriangle className="w-3 h-3" />
          Unknown
        </span>
      );
    }
    if (service.suspended) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
          <XCircle className="w-3 h-3" />
          Suspended
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
        <CheckCircle className="w-3 h-3" />
        Running
      </span>
    );
  };

  const formatTimestamp = (ts) => {
    if (!ts) return "N/A";
    const date = new Date(ts);
    return date.toLocaleString();
  };

  const formatTimeAgo = (ts) => {
    if (!ts) return "";
    const date = new Date(ts);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  if (loading && !config) {
    return (
      <div className="flex items-center justify-center p-12">
        <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
        <span className="ml-3 text-gray-600">Loading infrastructure status...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Settings className="w-6 h-6 text-blue-600" />
          <h2 className="text-xl font-semibold text-gray-800">Infrastructure Management</h2>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {lastRefresh && (
        <p className="text-xs text-gray-500">
          Last updated: {formatTimestamp(lastRefresh)}
        </p>
      )}

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-medium text-red-800">Error</h4>
            <p className="text-sm text-red-600">{error}</p>
          </div>
        </div>
      )}

      {/* Configuration Status */}
      {config && !config.render_configured && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-medium text-yellow-800">Render API Not Configured</h4>
              <p className="text-sm text-yellow-700 mt-1">
                To enable service management, configure the following environment variables on your backend:
              </p>
              <ul className="text-sm text-yellow-700 mt-2 space-y-1 font-mono">
                <li>RENDER_API_KEY</li>
                <li>RENDER_SERVICE_ID_DB</li>
                <li>RENDER_SERVICE_ID_APP</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {config && !config.email_configured && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-medium text-blue-800">Email Notifications Not Configured</h4>
              <p className="text-sm text-blue-700 mt-1">
                Actions will work but admin email notifications won't be sent. Configure SMTP settings to enable notifications.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Services Table */}
      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <div className="px-6 py-4 border-b bg-gray-50">
          <h3 className="font-semibold text-gray-800">Render Services</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 text-left text-sm text-gray-600">
              <tr>
                <th className="px-6 py-3 font-medium">Service</th>
                <th className="px-6 py-3 font-medium">Type</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {services.length === 0 && (
                <tr>
                  <td colSpan="4" className="px-6 py-8 text-center text-gray-500">
                    No services configured
                  </td>
                </tr>
              )}
              {services.map((service) => (
                <tr key={service.service_key || service.key} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      {getServiceIcon(service.type)}
                      <span className="font-medium text-gray-800">{service.name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-gray-600 capitalize">
                    {service.type === "postgres" ? "PostgreSQL Database" : "Web Service"}
                  </td>
                  <td className="px-6 py-4">
                    {getStatusBadge(service)}
                  </td>
                  <td className="px-6 py-4 text-right">
                    {actionLoading[service.service_key || service.key] ? (
                      <span className="inline-flex items-center gap-2 text-sm text-gray-500">
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Processing...
                      </span>
                    ) : service.suspended ? (
                      <button
                        onClick={() => setConfirmAction({ key: service.service_key || service.key, action: "start", name: service.name })}
                        disabled={!config?.render_configured}
                        className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Play className="w-4 h-4" />
                        Start
                      </button>
                    ) : (
                      <button
                        onClick={() => setConfirmAction({ key: service.service_key || service.key, action: "stop", name: service.name })}
                        disabled={!config?.render_configured}
                        className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Square className="w-4 h-4" />
                        Stop
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <div className="px-6 py-4 border-b bg-gray-50">
          <h3 className="font-semibold text-gray-800">Recent Activity</h3>
        </div>
        <div className="divide-y">
          {activity.length === 0 && (
            <div className="px-6 py-8 text-center text-gray-500">
              No recent infrastructure activity
            </div>
          )}
          {activity.map((item) => (
            <div key={item.id} className="px-6 py-4 flex items-center justify-between hover:bg-gray-50">
              <div className="flex items-center gap-4">
                <div className={`p-2 rounded-full ${
                  item.action === "start" ? "bg-green-100" : "bg-red-100"
                }`}>
                  {item.action === "start" ? (
                    <Play className={`w-4 h-4 ${item.success ? "text-green-600" : "text-gray-400"}`} />
                  ) : (
                    <Square className={`w-4 h-4 ${item.success ? "text-red-600" : "text-gray-400"}`} />
                  )}
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-800">
                    {item.username}{" "}
                    <span className={item.action === "start" ? "text-green-600" : "text-red-600"}>
                      {item.action === "start" ? "started" : "stopped"}
                    </span>{" "}
                    {item.service_name}
                  </p>
                  {!item.success && item.error && (
                    <p className="text-xs text-red-500 mt-1">Failed: {item.error}</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Clock className="w-4 h-4" />
                <span title={formatTimestamp(item.timestamp)}>
                  {formatTimeAgo(item.timestamp)}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Confirmation Modal */}
      {confirmAction && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className={`p-3 rounded-full ${
                confirmAction.action === "start" ? "bg-green-100" : "bg-red-100"
              }`}>
                {confirmAction.action === "start" ? (
                  <Play className="w-6 h-6 text-green-600" />
                ) : (
                  <Square className="w-6 h-6 text-red-600" />
                )}
              </div>
              <h3 className="text-lg font-semibold text-gray-800">
                {confirmAction.action === "start" ? "Start" : "Stop"} Service?
              </h3>
            </div>
            <p className="text-gray-600 mb-6">
              Are you sure you want to {confirmAction.action}{" "}
              <strong>{confirmAction.name}</strong>?
              {confirmAction.action === "stop" && (
                <span className="block mt-2 text-sm text-red-600">
                  This will make the service unavailable to all users.
                </span>
              )}
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmAction(null)}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleAction(confirmAction.key, confirmAction.action)}
                className={`px-4 py-2 text-white rounded-lg transition-colors ${
                  confirmAction.action === "start"
                    ? "bg-green-600 hover:bg-green-700"
                    : "bg-red-600 hover:bg-red-700"
                }`}
              >
                {confirmAction.action === "start" ? "Start Service" : "Stop Service"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Infrastructure;
