"use client";

import React, { useState } from 'react';
import { Search, Plus, Key, AlertCircle, UserPlus } from 'lucide-react';

const PasswordManager = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [passwords, setPasswords] = useState([]);
  const [newPassword, setNewPassword] = useState({
    service: '',
    service_username: '',
    encrypted_password: ''
  });
  const [error, setError] = useState('');
  const [qrCode, setQrCode] = useState('');
  const [secret, setSecret] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);

  const handleRegister = async (e) => {
      // Without preventDefault():
      // form submits -> page refreshes -> lose all state

      // With preventDefault():
      // form submits -> stay on same page -> keep state
    e.preventDefault();
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username }),
      });
      
      const data = await response.json();
      if (response.ok) {
        setQrCode(data.qr_code);
        setSecret(data.secret);
        setError('');
      } else {
        setError(data.detail || 'Registration failed');
      }
    } catch (err) {
      setError('Registration failed');
    }
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/verify-totp`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, code: totpCode }),
      });
      
      if (response.ok) {
        setIsAuthenticated(true);
        setError('');
        setQrCode('');
        setSecret('');
      } else {
        setError('Invalid authentication code');
      }
    } catch (err) {
      setError('Authentication failed');
    }
  };

  const searchPasswords = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/passwords/${username}/${searchTerm}`);
      const data = await response.json();
      setPasswords(data);
      setError('');
    } catch (err) {
      setError('Failed to fetch passwords');
    }
  };

  const addPassword = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/passwords/${username}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          service: newPassword.service,
          service_username: newPassword.service_username,
          encrypted_password: newPassword.encrypted_password
        }),
      });
      
      if (response.ok) {
        setNewPassword({ service: '', service_username: '', encrypted_password: '' });
        setError('');
        if (searchTerm) {
          searchPasswords();
        }
      } else {
        setError('Failed to add password');
      }
    } catch (err) {
      setError('Failed to add password');
    }
  };

  const renderPasswordForm = () => (
    <div className="space-y-4">
      <h3 className="text-lg font-medium flex items-center gap-2">
        <Plus className="h-5 w-5" />
        Add New Password
      </h3>
      <form onSubmit={addPassword} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Service:</label>
          <input
            type="text"
            value={newPassword.service}
            onChange={(e) => setNewPassword({...newPassword, service: e.target.value})}
            className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
            placeholder="e.g., Facebook"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-2">Service Username:</label>
          <input
            type="text"
            value={newPassword.service_username}
            onChange={(e) => setNewPassword({...newPassword, service_username: e.target.value})}
            className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
            placeholder="Username for this service"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-2">Password:</label>
          <input
            type="password"
            value={newPassword.encrypted_password}
            onChange={(e) => setNewPassword({...newPassword, encrypted_password: e.target.value})}
            className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
            placeholder="Enter password"
            required
          />
        </div>
        <button
          type="submit"
          className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600 transition-colors"
        >
          Add Password
        </button>
      </form>
    </div>
  );

  if (!isAuthenticated) {
    return (
      <div className="container mx-auto p-4 max-w-4xl">
        <div className="bg-white shadow-lg rounded-lg overflow-hidden">
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-center gap-2 text-xl font-bold">
              <Key className="h-6 w-6" />
              Password Manager
            </div>
          </div>
          
          <div className="p-6">
            {isRegistering ? (
              <div className="space-y-4">
                <h3 className="text-lg font-medium flex items-center gap-2">
                  <UserPlus className="h-5 w-5" />
                  Register New User
                </h3>
                <form onSubmit={handleRegister} className="space-y-4"> 
                {/* Once submitted, we will call handleRegister with our input value */}  
                  <div>
                    <label className="block text-sm font-medium mb-2">Username:</label>
                    <input
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>
                  <button
                    type="submit"
                    className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
                  >
                    Register
                  </button>
                </form>
                
                {qrCode && (
                  <div className="space-y-4">
                    <p className="font-medium">Scan this QR code with Google Authenticator:</p>
                    <img
                      src={`data:image/png;base64,${qrCode}`}
                      alt="TOTP QR Code"
                      className="border p-2"
                    />
                    <p className="text-sm">Secret key (if needed): {secret}</p>
                  </div>
                )}
                
                <button
                  onClick={() => {
                      setIsRegistering(false);
                      setError(''); // This will set the error to an empty string
                      setQrCode('');
                    }
                  }
                  className="text-blue-500 hover:text-blue-600"
                >
                  Back to Login
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <form onSubmit={handleAuth} className="space-y-4">
                {/* Once submitted, we will call handleAuth with our input value */}  
                  <div>
                    <label className="block text-sm font-medium mb-2">Username:</label>
                    <input
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Enter Google Authenticator Code:
                    </label>
                    <input
                      type="text"
                      value={totpCode}
                      onChange={(e) => setTotpCode(e.target.value)}
                      className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
                      placeholder="Enter 6-digit code"
                      required
                    />
                  </div>
                  <button
                    type="submit"
                    className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
                  >
                    Login
                  </button>
                </form>
                
                <button
                  onClick={() => setIsRegistering(true)}
                  className="text-blue-500 hover:text-blue-600"
                >
                  Register New User
                </button>
              </div>
            )}

            {error && (
              <div className="mt-4 p-4 bg-red-50 border-l-4 border-red-500 text-red-700 flex items-center gap-2">
                <AlertCircle className="h-5 w-5" />
                <p>{error}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 max-w-4xl">
      <div className="bg-white shadow-lg rounded-lg overflow-hidden">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center gap-2 text-xl font-bold">
            <Key className="h-6 w-6" />
            Password Manager
          </div>
        </div>
        
        <div className="p-6">
          <div className="space-y-8">
            {/* Search Section */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium flex items-center gap-2">
                <Search className="h-5 w-5" />
                Search Passwords
              </h3>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="flex-1 p-2 border rounded focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter service name (e.g., 'facebook')"
                />
                <button
                  onClick={searchPasswords}
                  className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 transition-colors"
                >
                  Search
                </button>
              </div>
              {passwords.length > 0 && (
                <div className="mt-4">
                  <h4 className="font-medium mb-2">Results:</h4>
                  <div className="space-y-2">
                    {passwords.map((pass, index) => (
                      <div key={index} className="p-4 border rounded bg-gray-50">
                        <p><strong>Service:</strong> {pass.service}</p>
                        <p><strong>Username:</strong> {pass.username}</p>
                        <p><strong>Password:</strong> {pass.password}</p>
                        <p><strong>Last Rotated:</strong> {pass.last_rotated}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Add New Password Section */}
            {renderPasswordForm()}
          </div>

          {error && (
            <div className="mt-4 p-4 bg-red-50 border-l-4 border-red-500 text-red-700 flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              <p>{error}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PasswordManager;