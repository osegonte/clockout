package com.example.clockoutandroid.ui.fragments

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import com.example.clockoutandroid.ApiConfig
import com.example.clockoutandroid.LoginActivity
import com.example.clockoutandroid.databinding.FragmentProfileBinding
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import java.net.HttpURLConnection
import java.net.URL

class ProfileFragment : Fragment() {
    
    private var _binding: FragmentProfileBinding? = null
    private val binding get() = _binding!!
    
    private var token: String = ""
    private var userName: String = ""
    private var userEmail: String = ""
    private var userRole: String = ""
    private var organizationId: Int = 0
    private var organizationName: String = ""
    
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentProfileBinding.inflate(inflater, container, false)
        return binding.root
    }
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        loadUserData()
        displayUserInfo()
        loadStats()
        setupClickListeners()
    }
    
    private fun loadUserData() {
        val prefs = requireContext().getSharedPreferences("auth", Context.MODE_PRIVATE)
        token = prefs.getString("token", "") ?: ""
        userName = prefs.getString("user_name", "User") ?: "User"
        userEmail = prefs.getString("email", "") ?: ""
        userRole = prefs.getString("user_role", "user") ?: "user"
        organizationId = prefs.getInt("organization_id", 0)
    }
    
    private fun displayUserInfo() {
        // Set user initials
        val initials = getInitials(userName)
        binding.tvUserInitials.text = initials
        
        // Set user name
        binding.tvUserName.text = userName
        
        // Set email
        binding.tvUserEmail.text = userEmail
        
        // Set role with proper capitalization
        binding.tvUserRole.text = when (userRole.lowercase()) {
            "admin" -> "Admin"
            "manager" -> "Manager"
            "worker" -> "Worker"
            else -> "User"
        }
        
        // Fetch organization name
        fetchOrganizationName()
    }
    
    private fun getInitials(name: String): String {
        val parts = name.trim().split(" ")
        return when {
            parts.size >= 2 -> "${parts[0].first()}${parts[1].first()}".uppercase()
            parts.size == 1 && parts[0].isNotEmpty() -> {
                if (parts[0].length >= 2) {
                    parts[0].substring(0, 2).uppercase()
                } else {
                    parts[0].first().uppercase()
                }
            }
            else -> "U"
        }
    }
    
    private fun fetchOrganizationName() {
        if (organizationId == 0) return
        
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val url = URL("${ApiConfig.BASE_URL}/organizations/$organizationId")
                val connection = url.openConnection() as HttpURLConnection
                connection.requestMethod = "GET"
                connection.setRequestProperty("Authorization", "Bearer $token")
                
                if (connection.responseCode == HttpURLConnection.HTTP_OK) {
                    val response = connection.inputStream.bufferedReader().readText()
                    val jsonResponse = org.json.JSONObject(response)
                    organizationName = jsonResponse.optString("name", "Organization")
                    
                    withContext(Dispatchers.Main) {
                        binding.tvOrganizationName.text = organizationName
                    }
                }
                
            } catch (e: Exception) {
                // Silent fail - keep default text
            }
        }
    }
    
    private fun loadStats() {
        if (token.isEmpty()) return
        
        CoroutineScope(Dispatchers.IO).launch {
            try {
                // Load workers count
                val workersCount = fetchCount("${ApiConfig.BASE_URL}/workers/?organization_id=$organizationId")
                
                // Load sites count
                val sitesCount = fetchCount("${ApiConfig.BASE_URL}/sites/?organization_id=$organizationId")
                
                // Load attendance count
                val attendanceCount = fetchCount("${ApiConfig.BASE_URL}/attendance/?organization_id=$organizationId")
                
                withContext(Dispatchers.Main) {
                    binding.tvTotalWorkers.text = workersCount.toString()
                    binding.tvTotalSites.text = sitesCount.toString()
                    binding.tvTotalAttendance.text = attendanceCount.toString()
                }
                
            } catch (e: Exception) {
                // Silent fail - keep showing 0s
            }
        }
    }
    
    private fun fetchCount(urlString: String): Int {
        return try {
            val url = URL(urlString)
            val connection = url.openConnection() as HttpURLConnection
            connection.requestMethod = "GET"
            connection.setRequestProperty("Authorization", "Bearer $token")
            
            if (connection.responseCode == HttpURLConnection.HTTP_OK) {
                val response = connection.inputStream.bufferedReader().readText()
                val jsonArray = JSONArray(response)
                jsonArray.length()
            } else {
                0
            }
        } catch (e: Exception) {
            0
        }
    }
    
    private fun setupClickListeners() {
        // Edit Profile
        binding.btnEditProfile.setOnClickListener {
            Toast.makeText(requireContext(), "Edit profile coming soon", Toast.LENGTH_SHORT).show()
        }
        
        // Change Password
        binding.btnChangePassword.setOnClickListener {
            Toast.makeText(requireContext(), "Change password coming soon", Toast.LENGTH_SHORT).show()
        }
        
        // About
        binding.btnAbout.setOnClickListener {
            showAboutDialog()
        }
        
        // Logout
        binding.btnLogout.setOnClickListener {
            performLogout()
        }
    }
    
    private fun showAboutDialog() {
        val message = """
            ClockOut v1.0.0
            
            GPS-verified farm attendance tracking system for Nigerian agriculture.
            
            Features:
            • GPS geofencing
            • Real-time attendance
            • Multi-site management
            • Worker tracking
            
            © 2024 ClockOut
        """.trimIndent()
        
        android.app.AlertDialog.Builder(requireContext())
            .setTitle("About ClockOut")
            .setMessage(message)
            .setPositiveButton("OK", null)
            .show()
    }
    
    private fun performLogout() {
        // Confirm logout
        android.app.AlertDialog.Builder(requireContext())
            .setTitle("Logout")
            .setMessage("Are you sure you want to logout?")
            .setPositiveButton("Logout") { _, _ ->
                // Clear all saved data
                val prefs = requireContext().getSharedPreferences("auth", Context.MODE_PRIVATE)
                prefs.edit().clear().apply()
                
                // Navigate to login
                val intent = Intent(requireContext(), LoginActivity::class.java)
                intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                startActivity(intent)
                
                Toast.makeText(requireContext(), "Logged out successfully", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }
    
    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}