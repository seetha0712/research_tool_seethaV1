import React, { useState, useRef, useEffect } from "react";
import { registerUser } from "../api";

const Register = ({ onSwitchToLogin }) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const inputRef = useRef();

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleRegister = async (e) => {
    e.preventDefault();
    setMsg(""); setError(""); setLoading(true);
    try {
      await registerUser(username.trim(), password);
      setMsg("Registration successful. Please log in.");
      setUsername(""); setPassword("");
    } catch (err) {
      setError(err?.response?.data?.detail || "Registration failed");
    }
    setLoading(false);
  };

  return (
    <div className="flex flex-col items-center mt-24">
      <form className="bg-white p-6 rounded shadow w-full max-w-sm" onSubmit={handleRegister}>
        <h2 className="text-xl font-bold mb-6">Register</h2>
        {msg && <div className="mb-4 text-green-600">{msg}</div>}
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
          {loading ? "Registering..." : "Register"}
        </button>
        <button
          type="button"
          onClick={onSwitchToLogin}
          className="mt-4 text-blue-600 underline w-full"
          disabled={loading}
        >
          Already have an account? Log In
        </button>
      </form>
    </div>
  );
};
export default Register;