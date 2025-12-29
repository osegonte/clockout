package com.example.clockoutandroid.ui.fragments

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import com.example.clockoutandroid.ApiConfig
import com.example.clockoutandroid.databinding.FragmentAttendanceBinding
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationServices
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.*

class AttendanceFragment : Fragment() {
    
    private var _binding: FragmentAttendanceBinding? = null
    private val binding get() = _binding!!
    
    private lateinit var fusedLocationClient: FusedLocationProviderClient
    
    private var token: String = ""
    private var userId: Int = 0
    private var organizationId: Int = 0
    private var selectedSiteId: Int = 0
    private var isClockedIn = false
    private var currentAttendanceId: Int = 0
    
    companion object {
        private const val LOCATION_PERMISSION_REQUEST_CODE = 1001
    }
    
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentAttendanceBinding.inflate(inflater, container, false)
        return binding.root
    }
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(requireActivity())
        
        loadUserData()
        updateCurrentTime()
        checkAttendanceStatus()
        setupClickListeners()
    }
    
    private fun loadUserData() {
        val prefs = requireContext().getSharedPreferences("auth", Context.MODE_PRIVATE)
        token = prefs.getString("token", "") ?: ""
        userId = prefs.getInt("user_id", 0)
        organizationId = prefs.getInt("organization_id", 0)
    }
    
    private fun updateCurrentTime() {
        val timeFormat = SimpleDateFormat("h:mm a", Locale.getDefault())
        val currentTime = timeFormat.format(Date())
        binding.tvCurrentTime.text = currentTime
    }
    
    private fun setupClickListeners() {
        // Main clock in/out button
        binding.btnClockInOut.setOnClickListener {
            if (isClockedIn) {
                performClockOut()
            } else {
                performClockIn()
            }
        }
        
        // View history
        binding.btnViewHistory.setOnClickListener {
            Toast.makeText(requireContext(), "Attendance history coming soon", Toast.LENGTH_SHORT).show()
        }
        
        // Select site
        binding.btnSelectSite.setOnClickListener {
            Toast.makeText(requireContext(), "Opening site selection...", Toast.LENGTH_SHORT).show()
            // TODO: Open site selection dialog
        }
    }
    
    private fun checkAttendanceStatus() {
        // Check if user is already clocked in today
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val dateFormat = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
                val today = dateFormat.format(Date())
                
                val url = URL("${ApiConfig.BASE_URL}/attendance/?organization_id=$organizationId&user_id=$userId")
                val connection = url.openConnection() as HttpURLConnection
                connection.requestMethod = "GET"
                connection.setRequestProperty("Authorization", "Bearer $token")
                
                if (connection.responseCode == HttpURLConnection.HTTP_OK) {
                    val response = connection.inputStream.bufferedReader().readText()
                    val jsonArray = org.json.JSONArray(response)
                    
                    // Check if there's an open attendance record today
                    for (i in 0 until jsonArray.length()) {
                        val record = jsonArray.getJSONObject(i)
                        val clockInTime = record.optString("clock_in_time", "")
                        val clockOutTime = record.optString("clock_out_time", "")
                        
                        if (clockInTime.startsWith(today) && clockOutTime.isEmpty()) {
                            // User is clocked in
                            currentAttendanceId = record.getInt("id")
                            val siteId = record.optInt("site_id", 0)
                            
                            withContext(Dispatchers.Main) {
                                updateUIForClockedIn(siteId)
                            }
                            return@launch
                        }
                    }
                    
                    // Not clocked in
                    withContext(Dispatchers.Main) {
                        updateUIForClockedOut()
                    }
                }
                
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    updateUIForClockedOut()
                }
            }
        }
    }
    
    private fun updateUIForClockedIn(siteId: Int) {
        isClockedIn = true
        selectedSiteId = siteId
        binding.tvClockAction.text = "Clock Out"
        binding.tvAttendanceStatus.text = "Currently clocked in"
        binding.btnClockInOut.setCardBackgroundColor(
            ContextCompat.getColor(requireContext(), com.example.clockoutandroid.R.color.error)
        )
        // TODO: Fetch site name and update tvSelectedSite
    }
    
    private fun updateUIForClockedOut() {
        isClockedIn = false
        binding.tvClockAction.text = "Clock In"
        binding.tvAttendanceStatus.text = "Ready to clock in"
        binding.btnClockInOut.setCardBackgroundColor(
            ContextCompat.getColor(requireContext(), com.example.clockoutandroid.R.color.info)
        )
        binding.tvSelectedSite.text = "No site selected"
        binding.tvTodayHours.text = "0:00"
    }
    
    private fun performClockIn() {
        // Check location permission
        if (ActivityCompat.checkSelfPermission(
                requireContext(),
                Manifest.permission.ACCESS_FINE_LOCATION
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(
                arrayOf(Manifest.permission.ACCESS_FINE_LOCATION),
                LOCATION_PERMISSION_REQUEST_CODE
            )
            return
        }
        
        // Get current location
        fusedLocationClient.lastLocation.addOnSuccessListener { location: Location? ->
            if (location != null) {
                sendClockInRequest(location.latitude, location.longitude)
            } else {
                Toast.makeText(requireContext(), "Unable to get location. Please try again.", Toast.LENGTH_SHORT).show()
            }
        }
    }
    
    private fun sendClockInRequest(latitude: Double, longitude: Double) {
        if (selectedSiteId == 0) {
            Toast.makeText(requireContext(), "Please select a site first", Toast.LENGTH_SHORT).show()
            return
        }
        
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val url = URL("${ApiConfig.BASE_URL}/attendance/")
                val connection = url.openConnection() as HttpURLConnection
                connection.requestMethod = "POST"
                connection.setRequestProperty("Content-Type", "application/json")
                connection.setRequestProperty("Authorization", "Bearer $token")
                connection.doOutput = true
                
                val jsonBody = JSONObject().apply {
                    put("user_id", userId)
                    put("site_id", selectedSiteId)
                    put("latitude", latitude)
                    put("longitude", longitude)
                    put("organization_id", organizationId)
                }
                
                connection.outputStream.use { outputStream ->
                    outputStream.write(jsonBody.toString().toByteArray())
                }
                
                val responseCode = connection.responseCode
                
                if (responseCode == HttpURLConnection.HTTP_OK || responseCode == HttpURLConnection.HTTP_CREATED) {
                    val response = connection.inputStream.bufferedReader().readText()
                    val jsonResponse = JSONObject(response)
                    currentAttendanceId = jsonResponse.getInt("id")
                    
                    withContext(Dispatchers.Main) {
                        updateUIForClockedIn(selectedSiteId)
                        Toast.makeText(requireContext(), "Clocked in successfully!", Toast.LENGTH_SHORT).show()
                    }
                } else {
                    val error = connection.errorStream?.bufferedReader()?.readText() ?: "Unknown error"
                    withContext(Dispatchers.Main) {
                        Toast.makeText(requireContext(), "Clock in failed: $error", Toast.LENGTH_LONG).show()
                    }
                }
                
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(requireContext(), "Error: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }
    
    private fun performClockOut() {
        // Get current location
        if (ActivityCompat.checkSelfPermission(
                requireContext(),
                Manifest.permission.ACCESS_FINE_LOCATION
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(
                arrayOf(Manifest.permission.ACCESS_FINE_LOCATION),
                LOCATION_PERMISSION_REQUEST_CODE
            )
            return
        }
        
        fusedLocationClient.lastLocation.addOnSuccessListener { location: Location? ->
            if (location != null) {
                sendClockOutRequest(location.latitude, location.longitude)
            } else {
                Toast.makeText(requireContext(), "Unable to get location. Please try again.", Toast.LENGTH_SHORT).show()
            }
        }
    }
    
    private fun sendClockOutRequest(latitude: Double, longitude: Double) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val url = URL("${ApiConfig.BASE_URL}/attendance/$currentAttendanceId")
                val connection = url.openConnection() as HttpURLConnection
                connection.requestMethod = "PUT"
                connection.setRequestProperty("Content-Type", "application/json")
                connection.setRequestProperty("Authorization", "Bearer $token")
                connection.doOutput = true
                
                val jsonBody = JSONObject().apply {
                    put("latitude", latitude)
                    put("longitude", longitude)
                }
                
                connection.outputStream.use { outputStream ->
                    outputStream.write(jsonBody.toString().toByteArray())
                }
                
                val responseCode = connection.responseCode
                
                if (responseCode == HttpURLConnection.HTTP_OK) {
                    withContext(Dispatchers.Main) {
                        updateUIForClockedOut()
                        Toast.makeText(requireContext(), "Clocked out successfully!", Toast.LENGTH_SHORT).show()
                    }
                } else {
                    val error = connection.errorStream?.bufferedReader()?.readText() ?: "Unknown error"
                    withContext(Dispatchers.Main) {
                        Toast.makeText(requireContext(), "Clock out failed: $error", Toast.LENGTH_LONG).show()
                    }
                }
                
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(requireContext(), "Error: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }
    
    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}