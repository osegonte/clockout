import { useAuth } from '../contexts/AuthContext';

export default function Dashboard() {
  const { user } = useAuth();

  const stats = [
    { label: 'Total Workers', value: '0' },
    { label: 'Active Sites', value: '0' },
    { label: "Today's Attendance", value: '0' },
    { label: 'Managers', value: '0' },
  ];

  return (
    <div className="space-y-6">
      {/* Welcome Card */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h2 className="text-2xl font-bold text-gray-900">
          Welcome back, {user?.full_name}
        </h2>
        <p className="text-gray-600 mt-2">
          Here's what's happening with your farm operations today.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => (
          <div 
            key={stat.label} 
            className={`bg-white rounded-xl shadow-sm p-6 border-l-4 ${
              index === 0 ? 'border-blue-500' : 
              index === 1 ? 'border-green-500' : 
              index === 2 ? 'border-purple-500' : 
              'border-orange-500'
            }`}
          >
            <p className="text-sm text-gray-600 font-medium">{stat.label}</p>
            <p className="text-3xl font-bold text-gray-900 mt-2">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button className="p-4 border-2 border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition text-left">
            <h4 className="font-semibold text-gray-900">Add Worker</h4>
            <p className="text-sm text-gray-600 mt-1">Register a new farm worker</p>
          </button>

          <button className="p-4 border-2 border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition text-left">
            <h4 className="font-semibold text-gray-900">Add Site</h4>
            <p className="text-sm text-gray-600 mt-1">Create a new farm site</p>
          </button>

          <button className="p-4 border-2 border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition text-left">
            <h4 className="font-semibold text-gray-900">View Reports</h4>
            <p className="text-sm text-gray-600 mt-1">Check attendance reports</p>
          </button>
        </div>
      </div>

      {/* Getting Started */}
      <div className="bg-gradient-to-r from-primary-500 to-primary-600 rounded-xl shadow-sm p-6 text-white">
        <h3 className="text-xl font-bold mb-3">Getting Started</h3>
        <p className="mb-4 opacity-90">
          Your ClockOut dashboard is ready! Start by adding your farm sites and workers.
        </p>
        <div className="space-y-2 text-sm opacity-90">
          <p>• Account created and verified</p>
          <p>• Add your first site</p>
          <p>• Register workers</p>
          <p>• Set up attendance tracking</p>
        </div>
      </div>
    </div>
  );
}