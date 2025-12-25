export default function Attendance() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Attendance Reports</h2>
            <p className="text-gray-600 mt-1">View and analyze worker attendance records</p>
          </div>
          <button className="px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition shadow-lg hover:shadow-xl">
            Export Report
          </button>
        </div>
      </div>

      {/* Attendance Reports - Coming Soon */}
      <div className="bg-white rounded-xl shadow-sm p-12 text-center">
        <h3 className="text-xl font-bold text-gray-900 mb-2">Attendance Reports Coming Soon</h3>
        <p className="text-gray-600 max-w-md mx-auto">
          This section will show detailed attendance records with GPS verification.
          Features include filtering, searching, and exporting attendance data.
        </p>
      </div>
    </div>
  );
}