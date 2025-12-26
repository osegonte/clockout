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
import com.example.clockoutandroid.data.models.Site
import com.example.clockoutandroid.data.remote.RetrofitInstance
import com.example.clockoutandroid.ui.adapters.SiteAdapter
import com.google.android.material.floatingactionbutton.FloatingActionButton
import kotlinx.coroutines.launch

class SitesFragment : Fragment() {

    private lateinit var recyclerView: RecyclerView
    private lateinit var searchView: SearchView
    private lateinit var fabAddSite: FloatingActionButton
    private lateinit var progressBar: ProgressBar
    private lateinit var tvEmptyState: TextView
    
    private lateinit var siteAdapter: SiteAdapter
    private var allSites = listOf<Site>()
    
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_sites, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        initViews(view)
        setupRecyclerView()
        setupSearchView()
        setupFab()
        loadSites()
    }

    private fun initViews(view: View) {
        recyclerView = view.findViewById(R.id.recyclerViewSites)
        searchView = view.findViewById(R.id.searchViewSites)
        fabAddSite = view.findViewById(R.id.fabAddSite)
        progressBar = view.findViewById(R.id.progressBar)
        tvEmptyState = view.findViewById(R.id.tvEmptyState)
    }

    private fun setupRecyclerView() {
        siteAdapter = SiteAdapter(
            onEditClick = { site -> showEditSiteDialog(site) },
            onDeleteClick = { site -> showDeleteConfirmation(site) }
        )
        
        recyclerView.apply {
            layoutManager = LinearLayoutManager(requireContext())
            adapter = siteAdapter
        }
    }

    private fun setupSearchView() {
        searchView.setOnQueryTextListener(object : SearchView.OnQueryTextListener {
            override fun onQueryTextSubmit(query: String?): Boolean {
                return false
            }

            override fun onQueryTextChange(newText: String?): Boolean {
                filterSites(newText ?: "")
                return true
            }
        })
    }

    private fun setupFab() {
        fabAddSite.setOnClickListener {
            showAddSiteDialog()
        }
    }

    private fun loadSites() {
        val sharedPref = requireActivity().getSharedPreferences("auth", Context.MODE_PRIVATE)
        val token = sharedPref.getString("token", "") ?: ""
        
        Log.d("SitesFragment", "Token: " + token)
        
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
                Log.d("SitesFragment", "Calling API...")
                val response = RetrofitInstance.api.getSites("Bearer " + token)
                
                Log.d("SitesFragment", "Response code: " + response.code())
                Log.d("SitesFragment", "Response successful: " + response.isSuccessful)
                
                if (response.isSuccessful) {
                    allSites = response.body() ?: emptyList()
                    
                    Log.d("SitesFragment", "Sites loaded: " + allSites.size)
                    
                    siteAdapter.submitList(allSites)
                    
                    if (allSites.isEmpty()) {
                        tvEmptyState.visibility = View.VISIBLE
                        tvEmptyState.text = "No sites yet. Tap + to add one."
                    } else {
                        tvEmptyState.visibility = View.GONE
                    }
                } else {
                    val errorBody = response.errorBody()?.string() ?: "Unknown error"
                    Log.e("SitesFragment", "API Error: " + response.code() + " - " + errorBody)
                    
                    tvEmptyState.visibility = View.VISIBLE
                    tvEmptyState.text = "Error: " + response.code() + "\n" + errorBody
                    
                    Toast.makeText(
                        requireContext(), 
                        "Failed to load sites: " + response.code(),
                        Toast.LENGTH_LONG
                    ).show()
                }
                
                progressBar.visibility = View.GONE
                
            } catch (e: Exception) {
                progressBar.visibility = View.GONE
                
                Log.e("SitesFragment", "Exception loading sites", e)
                
                val errorMessage = "Network error: " + e.message
                tvEmptyState.visibility = View.VISIBLE
                tvEmptyState.text = errorMessage
                
                Toast.makeText(requireContext(), errorMessage, Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun filterSites(query: String) {
        val filteredList = if (query.isEmpty()) {
            allSites
        } else {
            allSites.filter { site ->
                site.name.contains(query, ignoreCase = true)
            }
        }
        
        siteAdapter.submitList(filteredList)
        
        if (filteredList.isEmpty() && query.isNotEmpty()) {
            tvEmptyState.visibility = View.VISIBLE
            tvEmptyState.text = "No sites found for: " + query
        } else {
            tvEmptyState.visibility = View.GONE
        }
    }

    private fun showAddSiteDialog() {
        val dialogView = layoutInflater.inflate(R.layout.dialog_add_site, null)
        
        val etName = dialogView.findViewById<EditText>(R.id.etSiteName)
        val etLatitude = dialogView.findViewById<EditText>(R.id.etLatitude)
        val etLongitude = dialogView.findViewById<EditText>(R.id.etLongitude)
        val etRadius = dialogView.findViewById<EditText>(R.id.etRadius)
        
        AlertDialog.Builder(requireContext())
            .setTitle("Add New Site")
            .setView(dialogView)
            .setPositiveButton("Add") { _, _ ->
                val name = etName.text.toString().trim()
                val latStr = etLatitude.text.toString().trim()
                val lonStr = etLongitude.text.toString().trim()
                val radiusStr = etRadius.text.toString().trim()
                
                if (name.isEmpty()) {
                    Toast.makeText(requireContext(), "Name is required", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                
                if (latStr.isEmpty() || lonStr.isEmpty()) {
                    Toast.makeText(requireContext(), "GPS coordinates are required", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                
                Toast.makeText(requireContext(), "Add site API coming soon", Toast.LENGTH_SHORT).show()
                loadSites()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun showEditSiteDialog(site: Site) {
        val dialogView = layoutInflater.inflate(R.layout.dialog_add_site, null)
        
        val etName = dialogView.findViewById<EditText>(R.id.etSiteName)
        val etLatitude = dialogView.findViewById<EditText>(R.id.etLatitude)
        val etLongitude = dialogView.findViewById<EditText>(R.id.etLongitude)
        val etRadius = dialogView.findViewById<EditText>(R.id.etRadius)
        
        etName.setText(site.name)
        etLatitude.setText(site.latitude.toString())
        etLongitude.setText(site.longitude.toString())
        etRadius.setText(site.radius.toString())
        
        AlertDialog.Builder(requireContext())
            .setTitle("Edit Site")
            .setView(dialogView)
            .setPositiveButton("Save") { _, _ ->
                val name = etName.text.toString().trim()
                val latStr = etLatitude.text.toString().trim()
                val lonStr = etLongitude.text.toString().trim()
                val radiusStr = etRadius.text.toString().trim()
                
                if (name.isEmpty()) {
                    Toast.makeText(requireContext(), "Name is required", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                
                if (latStr.isEmpty() || lonStr.isEmpty()) {
                    Toast.makeText(requireContext(), "GPS coordinates are required", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                
                Toast.makeText(requireContext(), "Update site API coming soon", Toast.LENGTH_SHORT).show()
                loadSites()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun showDeleteConfirmation(site: Site) {
        AlertDialog.Builder(requireContext())
            .setTitle("Delete Site")
            .setMessage("Are you sure you want to delete " + site.name + "?")
            .setPositiveButton("Delete") { _, _ ->
                Toast.makeText(requireContext(), "Delete site API coming soon", Toast.LENGTH_SHORT).show()
                loadSites()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }
}