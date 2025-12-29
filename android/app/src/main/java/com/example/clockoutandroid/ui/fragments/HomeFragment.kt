package com.example.clockoutandroid.ui.fragments

import android.content.Context
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import com.example.clockoutandroid.ApiConfig
import com.example.clockoutandroid.databinding.FragmentHomeBinding
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.*

class HomeFragment : Fragment() {
    
    private var _binding: FragmentHomeBinding? = null
    private val binding get() = _binding!!
    
    private var token: String = ""
    private var userName: String = ""
    private var organizationId: Int = 0
    
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentHomeBinding.inflate(inflater, container, false)
        return binding.root
    }
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        loadUserData()
        setupGreeting()
        setupClickListeners()
        loadStats()
    }
    
    private fun loadUserData() {
        val prefs = requireContext().getSharedPreferences("auth", Context.MODE_PRIVATE)
        token = prefs.getString("token", "") ?: ""
        userName = prefs.getString("user_name", "User") ?: "User"
        organizationId = prefs.getInt("organization_id", 0)
        
        // Set user initials
        val initials = getInitials(userName)
        binding.tvUserInitials.text = initials
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
    
    private fun setupGreeting() {
        val calendar = Calendar.getInstance()
        val hour = calendar.get(Calendar.HOUR_OF_DAY)
        
        val greeting = when (hour) {
            in 0..11 -> "Good morning"
            in 12..16 -> "Good afternoon"
            else -> "Good evening"
        }
        
        binding.tvGreeting.text = greeting
        binding.tvWelcome.text = userName
    }
    
    private fun setupClickListeners() {
        // Mark Attendance - Placeholder for now
        binding.btnMarkAttendance.setOnClickListener {
            Toast.makeText(requireContext(), "Opening Attendance...", Toast.LENGTH_SHORT).show()
        }
        
        // View Sites - Placeholder for now
        binding.btnViewSites.setOnClickListener {
            Toast.makeText(requireContext(), "Opening Sites...", Toast.LENGTH_SHORT).show()
        }
    }
    
    private fun loadStats() {
        if (token.isEmpty()) return
        
        CoroutineScope(Dispatchers.IO).launch {
            try {
                // Load workers count
                val workersCount = fetchWorkersCount()
                
                // Load sites count
                val sitesCount = fetchSitesCount()
                
                // Load today's attendance count
                val todayAttendance = fetchTodayAttendanceCount()
                
                withContext(Dispatchers.Main) {
                    binding.tvWorkersCount.text = workersCount.toString()
                    binding.tvSitesCount.text = sitesCount.toString()
                    binding.tvTodayAttendance.text = todayAttendance.toString()
                }
                
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    // Silent fail - keep showing 0s
                }
            }
        }
    }
    
    private fun fetchWorkersCount(): Int {
        return try {
            val url = URL("${ApiConfig.BASE_URL}/workers/?organization_id=$organizationId")
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
    
    private fun fetchSitesCount(): Int {
        return try {
            val url = URL("${ApiConfig.BASE_URL}/sites/?organization_id=$organizationId")
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
    
    private fun fetchTodayAttendanceCount(): Int {
        return try {
            // Get today's date
            val dateFormat = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
            val today = dateFormat.format(Date())
            
            val url = URL("${ApiConfig.BASE_URL}/attendance/?organization_id=$organizationId")
            val connection = url.openConnection() as HttpURLConnection
            connection.requestMethod = "GET"
            connection.setRequestProperty("Authorization", "Bearer $token")
            
            if (connection.responseCode == HttpURLConnection.HTTP_OK) {
                val response = connection.inputStream.bufferedReader().readText()
                val jsonArray = JSONArray(response)
                
                // Count records from today
                var count = 0
                for (i in 0 until jsonArray.length()) {
                    val record = jsonArray.getJSONObject(i)
                    val clockInTime = record.optString("clock_in_time", "")
                    if (clockInTime.startsWith(today)) {
                        count++
                    }
                }
                count
            } else {
                0
            }
        } catch (e: Exception) {
            0
        }
    }
    
    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}