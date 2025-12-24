import { useState } from 'react';
import { authApi } from './api/auth';

function App() {
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<string>('');

  const testLogin = async () => {
    setTesting(true);
    setResult('Testing login...');
    
    try {
      const response = await authApi.login('admin@clockout.com', 'password123');
      setResult(`✅ Success! Logged in as: ${response.user.email}`);
      console.log('Login response:', response);
    } catch (error: any) {
      setResult(`❌ Error: ${error.message}`);
      console.error('Login error:', error);
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="card max-w-md w-full">
        <h1 className="text-3xl font-bold text-primary-600 mb-4">
          🎉 ClockOut Dashboard
        </h1>
        <p className="text-gray-600 mb-4">
          API Client is ready! Let's test the login endpoint.
        </p>
        
        <button 
          onClick={testLogin} 
          disabled={testing}
          className="btn btn-primary w-full mb-4"
        >
          {testing ? 'Testing...' : 'Test Login API'}
        </button>

        {result && (
          <div className={`p-4 rounded-md ${
            result.includes('✅') ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
          }`}>
            <p className="text-sm font-mono">{result}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;