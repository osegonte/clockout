package com.example.clockoutandroid.ui.fragments

import android.app.AlertDialog
import android.content.Context
import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.ProgressBar
import android.widget.SearchView
import android.widget.TextView
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.clockoutandroid.R
import com.example.clockoutandroid.data.models.Worker
import com.example.clockoutandroid.data.remote.RetrofitInstance
import com.example.clockoutandroid.ui.adapters.WorkerAdapter
import com.google.android.material.floatingactionbutton.FloatingActionButton
import kotlinx.coroutines.launch

class WorkersFragment : Fragment() {

    private lateinit var recyclerView: RecyclerView
    private lateinit var searchView: SearchView
    private lateinit var fabAddWorker: FloatingActionButton
    private lateinit var progressBar: ProgressBar
    private lateinit var tvEmptyState: TextView
    
    private lateinit var workerAdapter: WorkerAdapter
    private var allWorkers = listOf<Worker>()
    
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_workers, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        initViews(view)
        setupRecyclerView()
        setupSearchView()
        setupFab()
        loadWorkers()
    }

    private fun initViews(view: View) {
        recyclerView = view.findViewById(R.id.recyclerViewWorkers)
        searchView = view.findViewById(R.id.searchViewWorkers)
        fabAddWorker = view.findViewById(R.id.fabAddWorker)
        progressBar = view.findViewById(R.id.progressBar)
        tvEmptyState = view.findViewById(R.id.tvEmptyState)
    }

    private fun setupRecyclerView() {
        workerAdapter = WorkerAdapter(
            onEditClick = { worker -> showEditWorkerDialog(worker) },
            onDeleteClick = { worker -> showDeleteConfirmation(worker) }
        )
        
        recyclerView.apply {
            layoutManager = LinearLayoutManager(requireContext())
            adapter = workerAdapter
        }
    }

    private fun setupSearchView() {
        searchView.setOnQueryTextListener(object : SearchView.OnQueryTextListener {
            override fun onQueryTextSubmit(query: String?): Boolean {
                return false
            }

            override fun onQueryTextChange(newText: String?): Boolean {
                filterWorkers(newText ?: "")
                return true
            }
        })
    }

    private fun setupFab() {
        fabAddWorker.setOnClickListener {
            showAddWorkerDialog()
        }
    }

    private fun loadWorkers() {
        val sharedPref = requireActivity().getSharedPreferences("auth", Context.MODE_PRIVATE)
        val token = sharedPref.getString("token", "") ?: ""
        
        // DEBUG: Log token
        Log.d("WorkersFragment", "Token: " + token)
        
        if (token.isEmpty()) {
            Toast.makeText(requireContext(), "No auth token found. Please login again.", Toast.LENGTH_LONG).show()
            tvEmptyState.visibility = View.VISIBLE
            tvEmptyState.text = "Not authenticated. Please logout and login again."
            return
        }
        
        progressBar.visibility = View.VISIBLE
        tvEmptyState.visibility = View.GONE
        
        lifecycleScope.launch {
            try {
                Log.d("WorkersFragment", "Calling API...")
                val response = RetrofitInstance.api.getWorkers("Bearer " + token)
                
                Log.d("WorkersFragment", "Response code: " + response.code())
                Log.d("WorkersFragment", "Response successful: " + response.isSuccessful)
                
                if (response.isSuccessful) {
                    allWorkers = response.body() ?: emptyList()
                    
                    Log.d("WorkersFragment", "Workers loaded: " + allWorkers.size)
                    
                    workerAdapter.submitList(allWorkers)
                    
                    if (allWorkers.isEmpty()) {
                        tvEmptyState.visibility = View.VISIBLE
                        tvEmptyState.text = "No workers yet. Tap + to add one."
                    } else {
                        tvEmptyState.visibility = View.GONE
                    }
                } else {
                    val errorBody = response.errorBody()?.string() ?: "Unknown error"
                    Log.e("WorkersFragment", "API Error: " + response.code() + " - " + errorBody)
                    
                    tvEmptyState.visibility = View.VISIBLE
                    tvEmptyState.text = "Error: " + response.code() + "\n" + errorBody
                    
                    Toast.makeText(
                        requireContext(), 
                        "Failed to load workers: " + response.code(),
                        Toast.LENGTH_LONG
                    ).show()
                }
                
                progressBar.visibility = View.GONE
                
            } catch (e: Exception) {
                progressBar.visibility = View.GONE
                
                Log.e("WorkersFragment", "Exception loading workers", e)
                
                val errorMessage = "Network error: " + e.message
                tvEmptyState.visibility = View.VISIBLE
                tvEmptyState.text = errorMessage
                
                Toast.makeText(requireContext(), errorMessage, Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun filterWorkers(query: String) {
        val filteredList = if (query.isEmpty()) {
            allWorkers
        } else {
            allWorkers.filter { worker ->
                worker.name.contains(query, ignoreCase = true) ||
                (worker.phone?.contains(query) == true)
            }
        }
        
        workerAdapter.submitList(filteredList)
        
        if (filteredList.isEmpty() && query.isNotEmpty()) {
            tvEmptyState.visibility = View.VISIBLE
            tvEmptyState.text = "No workers found for: " + query
        } else {
            tvEmptyState.visibility = View.GONE
        }
    }

    private fun showAddWorkerDialog() {
        val dialogView = layoutInflater.inflate(R.layout.dialog_add_worker, null)
        
        val etName = dialogView.findViewById<EditText>(R.id.etWorkerName)
        val etPhone = dialogView.findViewById<EditText>(R.id.etWorkerPhone)
        val etEmployeeId = dialogView.findViewById<EditText>(R.id.etEmployeeId)
        
        AlertDialog.Builder(requireContext())
            .setTitle("Add New Worker")
            .setView(dialogView)
            .setPositiveButton("Add") { _, _ ->
                val name = etName.text.toString().trim()
                val phone = etPhone.text.toString().trim()
                val employeeId = etEmployeeId.text.toString().trim()
                
                if (name.isEmpty()) {
                    Toast.makeText(requireContext(), "Name is required", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                
                Toast.makeText(requireContext(), "Add worker API coming soon", Toast.LENGTH_SHORT).show()
                loadWorkers()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun showEditWorkerDialog(worker: Worker) {
        val dialogView = layoutInflater.inflate(R.layout.dialog_add_worker, null)
        
        val etName = dialogView.findViewById<EditText>(R.id.etWorkerName)
        val etPhone = dialogView.findViewById<EditText>(R.id.etWorkerPhone)
        val etEmployeeId = dialogView.findViewById<EditText>(R.id.etEmployeeId)
        
        etName.setText(worker.name)
        etPhone.setText(worker.phone ?: "")
        etEmployeeId.setText(worker.employeeId ?: "")
        
        AlertDialog.Builder(requireContext())
            .setTitle("Edit Worker")
            .setView(dialogView)
            .setPositiveButton("Save") { _, _ ->
                val name = etName.text.toString().trim()
                val phone = etPhone.text.toString().trim()
                val employeeId = etEmployeeId.text.toString().trim()
                
                if (name.isEmpty()) {
                    Toast.makeText(requireContext(), "Name is required", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                
                Toast.makeText(requireContext(), "Update worker API coming soon", Toast.LENGTH_SHORT).show()
                loadWorkers()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun showDeleteConfirmation(worker: Worker) {
        AlertDialog.Builder(requireContext())
            .setTitle("Delete Worker")
            .setMessage("Are you sure you want to delete " + worker.name + "?")
            .setPositiveButton("Delete") { _, _ ->
                Toast.makeText(requireContext(), "Delete worker API coming soon", Toast.LENGTH_SHORT).show()
                loadWorkers()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }
}