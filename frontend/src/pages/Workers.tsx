import { useState, useEffect } from 'react';
import { workersApi, Worker, CreateWorkerData, UpdateWorkerData } from '../api/workers';

export default function Workers() {
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  
  // Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedWorker, setSelectedWorker] = useState<Worker | null>(null);
  
  // Form state
  const [formData, setFormData] = useState<CreateWorkerData>({
    full_name: '',
    phone_number: '',
    id_number: '',
    site_id: null,
  });

  // Load workers on mount
  useEffect(() => {
    loadWorkers();
  }, []);

  const loadWorkers = async () => {
    try {
      setLoading(true);
      const data = await workersApi.getAll();
      setWorkers(data);
      setError('');
    } catch (err: any) {
      setError('Failed to load workers');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddWorker = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await workersApi.create(formData);
      setShowAddModal(false);
      resetForm();
      loadWorkers();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add worker');
    }
  };

  const handleEditWorker = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWorker) return;
    
    try {
      await workersApi.update(selectedWorker.id, formData as UpdateWorkerData);
      setShowEditModal(false);
      resetForm();
      setSelectedWorker(null);
      loadWorkers();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update worker');
    }
  };

  const handleDeleteWorker = async () => {
    if (!selectedWorker) return;
    
    try {
      await workersApi.delete(selectedWorker.id);
      setShowDeleteModal(false);
      setSelectedWorker(null);
      loadWorkers();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete worker');
    }
  };

  const handleToggleStatus = async (worker: Worker) => {
    try {
      await workersApi.toggleStatus(worker.id, !worker.is_active);
      loadWorkers();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update status');
    }
  };

  const openEditModal = (worker: Worker) => {
    setSelectedWorker(worker);
    setFormData({
      full_name: worker.full_name,
      phone_number: worker.phone_number,
      id_number: worker.id_number,
      site_id: worker.site_id,
    });
    setShowEditModal(true);
  };

  const openDeleteModal = (worker: Worker) => {
    setSelectedWorker(worker);
    setShowDeleteModal(true);
  };

  const resetForm = () => {
    setFormData({
      full_name: '',
      phone_number: '',
      id_number: '',
      site_id: null,
    });
  };

  const filteredWorkers = workers.filter(worker =>
    worker.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    worker.phone_number.includes(searchTerm) ||
    worker.id_number.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Workers Management</h2>
            <p className="text-gray-600 mt-1">Manage your farm workers and their information</p>
          </div>
          <button 
            onClick={() => setShowAddModal(true)}
            className="px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition shadow-lg hover:shadow-xl"
          >
            + Add Worker
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* Search Bar */}
      <div className="bg-white rounded-xl shadow-sm p-4">
        <input
          type="text"
          placeholder="Search by name, phone, or ID number..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        />
      </div>

      {/* Workers Table */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading workers...</p>
          </div>
        ) : filteredWorkers.length === 0 ? (
          <div className="p-12 text-center">
            <h3 className="text-xl font-bold text-gray-900 mb-2">No Workers Found</h3>
            <p className="text-gray-600 mb-4">
              {searchTerm ? 'No workers match your search.' : 'Get started by adding your first worker.'}
            </p>
            {!searchTerm && (
              <button 
                onClick={() => setShowAddModal(true)}
                className="px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition"
              >
                + Add Your First Worker
              </button>
            )}
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Phone Number
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  ID Number
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Site
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredWorkers.map((worker) => (
                <tr key={worker.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="font-medium text-gray-900">{worker.full_name}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-600">
                    {worker.phone_number}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-600">
                    {worker.id_number}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-600">
                    {worker.site_name || 'Not assigned'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <button
                      onClick={() => handleToggleStatus(worker)}
                      className={`px-3 py-1 rounded-full text-xs font-medium ${
                        worker.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {worker.is_active ? 'Active' : 'Inactive'}
                    </button>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                    <button
                      onClick={() => openEditModal(worker)}
                      className="text-primary-600 hover:text-primary-900"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => openDeleteModal(worker)}
                      className="text-red-600 hover:text-red-900"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Add Worker Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
            <h3 className="text-xl font-bold text-gray-900 mb-4">Add New Worker</h3>
            <form onSubmit={handleAddWorker} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Full Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  placeholder="John Doe"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Phone Number *
                </label>
                <input
                  type="tel"
                  required
                  value={formData.phone_number}
                  onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  placeholder="+234 801 234 5678"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  ID Number *
                </label>
                <input
                  type="text"
                  required
                  value={formData.id_number}
                  onChange={(e) => setFormData({ ...formData, id_number: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  placeholder="NIN or other ID"
                />
              </div>

              <div className="flex space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => { setShowAddModal(false); resetForm(); }}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg"
                >
                  Add Worker
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Worker Modal */}
      {showEditModal && selectedWorker && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
            <h3 className="text-xl font-bold text-gray-900 mb-4">Edit Worker</h3>
            <form onSubmit={handleEditWorker} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Full Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Phone Number *
                </label>
                <input
                  type="tel"
                  required
                  value={formData.phone_number}
                  onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  ID Number *
                </label>
                <input
                  type="text"
                  required
                  value={formData.id_number}
                  onChange={(e) => setFormData({ ...formData, id_number: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                />
              </div>

              <div className="flex space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => { setShowEditModal(false); setSelectedWorker(null); resetForm(); }}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && selectedWorker && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
            <h3 className="text-xl font-bold text-gray-900 mb-4">Delete Worker</h3>
            <p className="text-gray-600 mb-6">
              Are you sure you want to delete <strong>{selectedWorker.full_name}</strong>? 
              This action cannot be undone.
            </p>
            <div className="flex space-x-3">
              <button
                onClick={() => { setShowDeleteModal(false); setSelectedWorker(null); }}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteWorker}
                className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}