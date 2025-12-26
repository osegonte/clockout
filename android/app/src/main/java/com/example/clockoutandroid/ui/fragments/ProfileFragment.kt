package com.example.clockoutandroid.ui.fragments

import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.example.clockoutandroid.LoginActivity
import com.example.clockoutandroid.R
import kotlinx.coroutines.launch
import org.json.JSONArray

class ProfileFragment : Fragment() {
    
    private lateinit var tvUserName: TextView
    private lateinit var tvUserEmail: TextView
    private lateinit var tvUserRole: TextView
    private lateinit var tvSyncStatus: TextView
    private lateinit var tvAppVersion: TextView
    private lateinit var btnSync: Button
    private lateinit var btnLogout: Button
    
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_profile, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        initViews(view)
        loadUserInfo()
        updateSyncStatus()
        setupButtons()
    }

    private fun initViews(view: View) {
        tvUserName = view.findViewById(R.id.tvUserName)
        tvUserEmail = view.findViewById(R.id.tvUserEmail)
        tvUserRole = view.findViewById(R.id.tvUserRole)
        tvSyncStatus = view.findViewById(R.id.tvSyncStatus)
        tvAppVersion = view.findViewById(R.id.tvAppVersion)
        btnSync = view.findViewById(R.id.btnSync)
        btnLogout = view.findViewById(R.id.btnLogout)
    }

    private fun loadUserInfo() {
        val sharedPref = requireActivity().getSharedPreferences("auth", Context.MODE_PRIVATE)
        
        val userName = sharedPref.getString("user_name", null)
        val userEmail = sharedPref.getString("email", null)
        val userMode = sharedPref.getString("user_mode", "worker") ?: "worker"
        
        // Set user info
        if (userName != null) {
            tvUserName.text = userName
        } else {
            tvUserName.text = "User"
        }
        
        if (userEmail != null) {
            tvUserEmail.text = userEmail
        } else {
            tvUserEmail.text = "No email set"
        }
        
        // Format role nicely
        val roleText = when (userMode) {
            "admin" -> "Administrator"
            "manager" -> "Manager"
            "worker" -> "Worker"
            else -> userMode.capitalize()
        }
        tvUserRole.text = roleText
        
        // App version
        try {
            val packageInfo = requireActivity().packageManager.getPackageInfo(requireActivity().packageName, 0)
            val versionText = "Version " + packageInfo.versionName
            tvAppVersion.text = versionText
        } catch (e: Exception) {
            tvAppVersion.text = "Version 1.0"
        }
    }

    private fun updateSyncStatus() {
        val sharedPref = requireActivity().getSharedPreferences("auth", Context.MODE_PRIVATE)
        val pendingEvents = sharedPref.getString("pending_events", "[]") ?: "[]"
        
        try {
            val eventsArray = JSONArray(pendingEvents)
            val count = eventsArray.length()
            
            if (count == 0) {
                tvSyncStatus.text = "All synced"
                btnSync.isEnabled = false
            } else {
                val statusText = count.toString() + " events pending sync"
                tvSyncStatus.text = statusText
                btnSync.isEnabled = true
            }
        } catch (e: Exception) {
            tvSyncStatus.text = "Sync status unavailable"
            btnSync.isEnabled = false
        }
    }

    private fun setupButtons() {
        btnSync.setOnClickListener {
            performSync()
        }
        
        btnLogout.setOnClickListener {
            showLogoutConfirmation()
        }
    }

    private fun performSync() {
        Toast.makeText(requireContext(), "Manual sync coming soon", Toast.LENGTH_SHORT).show()
        
        // TODO: Implement actual sync logic
        // For now, just update the status
        updateSyncStatus()
    }

    private fun showLogoutConfirmation() {
        AlertDialog.Builder(requireContext())
            .setTitle("Logout")
            .setMessage("Are you sure you want to logout?")
            .setPositiveButton("Logout") { _, _ ->
                performLogout()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun performLogout() {
        // Clear all auth data
        val sharedPref = requireActivity().getSharedPreferences("auth", Context.MODE_PRIVATE)
        sharedPref.edit().clear().apply()
        
        // Also clear pending events if needed
        // sharedPref.edit().remove("pending_events").apply()
        
        Toast.makeText(requireContext(), "Logged out successfully", Toast.LENGTH_SHORT).show()
        
        // Navigate to login
        val intent = Intent(requireActivity(), LoginActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        startActivity(intent)
        requireActivity().finish()
    }

    override fun onResume() {
        super.onResume()
        // Refresh sync status when fragment becomes visible
        updateSyncStatus()
    }
}