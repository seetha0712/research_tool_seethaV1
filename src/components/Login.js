import React, { useState, useRef, useEffect } from "react";
import { loginUser } from "../api";

const Login = ({ onLoginSuccess, onSwitchToRegister }) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const inputRef = useRef();

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const { access_token } = await loginUser(username, password);
      localStorage.setItem("jwt_token", access_token); // Save token
      onLoginSuccess(access_token);
    } catch (err) {
      setError(err?.response?.data?.detail || "Login failed");
    }
    setLoading(false);
  };

  return (
    <div className="flex flex-col items-center mt-24">
      <form className="bg-white p-6 rounded shadow w-full max-w-sm" onSubmit={handleLogin}>
        <h2 className="text-xl font-bold mb-6">Login</h2>
        {error && <div className="mb-4 text-red-600">{error}</div>}
        <input
          ref={inputRef}
          className="w-full mb-4 p-2 border rounded"
          placeholder="Username"
          value={username}
          onChange={e => setUsername(e.target.value)}
          required
          disabled={loading}
        />
        <input
          className="w-full mb-6 p-2 border rounded"
          type="password"
          placeholder="Password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          required
          disabled={loading}
        />
        <button
          className="w-full py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          type="submit"
          disabled={loading}
        >
          {loading ? "Logging in..." : "Login"}
        </button>
        <button
          type="button"
          onClick={onSwitchToRegister}
          className="mt-4 text-blue-600 underline w-full"
          disabled={loading}
        >
          New user? Register
        </button>
      </form>
    </div>
  );
};

export default Login;