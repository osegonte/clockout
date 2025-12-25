export default function Sites() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Sites Management</h2>
            <p className="text-gray-600 mt-1">Manage your farm sites and locations</p>
          </div>
          <button className="px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition shadow-lg hover:shadow-xl">
            + Add Site
          </button>
        </div>
      </div>

      {/* Sites List - Coming Soon */}
      <div className="bg-white rounded-xl shadow-sm p-12 text-center">
        <h3 className="text-xl font-bold text-gray-900 mb-2">Sites Management Coming Soon</h3>
        <p className="text-gray-600 max-w-md mx-auto">
          This section will allow you to add and manage your farm sites.
          Features include GPS coordinates, site managers, and worker assignments.
        </p>
      </div>
    </div>
  );
}