package com.example.clockoutandroid.ui.fragments

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.os.Bundle
import android.os.Looper
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import androidx.core.app.ActivityCompat
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.example.clockoutandroid.R
import com.example.clockoutandroid.data.models.Site
import com.example.clockoutandroid.data.models.Worker
import com.example.clockoutandroid.data.remote.RetrofitInstance
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.UUID

class AttendanceFragment : Fragment() {

    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private lateinit var locationCallback: LocationCallback
    
    private lateinit var tvGpsStatus: TextView
    private lateinit var tvSiteName: TextView
    private lateinit var tvSyncStatus: TextView
    private lateinit var spinnerWorker: Spinner
    private lateinit var btnCheckIn: Button
    private lateinit var btnCheckOut: Button
    
    private var currentLocation: Location? = null
    private var currentSite: Site? = null
    private val GEOFENCE_RADIUS = 100.0

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_attendance, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        initViews(view)
        setupLocationClient()
        loadSiteAndWorkers()
    }

    private fun initViews(view: View) {
        tvGpsStatus = view.findViewById(R.id.tvGpsStatus)
        tvSiteName = view.findViewById(R.id.tvSiteName)
        tvSyncStatus = view.findViewById(R.id.tvSyncStatus)
        spinnerWorker = view.findViewById(R.id.spinnerWorker)
        btnCheckIn = view.findViewById(R.id.btnCheckIn)
        btnCheckOut = view.findViewById(R.id.btnCheckOut)
        
        btnCheckIn.setOnClickListener { markAttendance("IN") }
        btnCheckOut.setOnClickListener { markAttendance("OUT") }
    }

    private fun setupLocationClient() {
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(requireActivity())
        
        locationCallback = object : LocationCallback() {
            override fun onLocationResult(locationResult: LocationResult) {
                val location = locationResult.lastLocation
                if (location != null) {
                    currentLocation = location
                    currentSite?.let { site -> validateGeofence(location, site) }
                } else {
                    tvGpsStatus.text = "Location unavailable"
                }
            }
        }
    }

    private fun loadSiteAndWorkers() {
        val sharedPref = requireActivity().getSharedPreferences("ClockOutPrefs", Context.MODE_PRIVATE)
        val token = sharedPref.getString("access_token", "") ?: ""
        val userRole = sharedPref.getString("user_role", "worker") ?: "worker"
        
        Log.d("AttendanceFragment", "Loading data for role: " + userRole)
        
        lifecycleScope.launch {
            try {
                val sitesResponse = RetrofitInstance.api.getSites("Bearer " + token)
                
                if (sitesResponse.isSuccessful) {
                    val sites = sitesResponse.body() ?: emptyList()
                    Log.d("AttendanceFragment", "Fetched " + sites.size + " sites")
                    
                    if (sites.isNotEmpty()) {
                        currentSite = sites[0]
                        tvSiteName.text = currentSite?.name ?: "Unknown Site"
                        requestLocationUpdates()
                    } else {
                        tvSiteName.text = "No sites available"
                        tvGpsStatus.text = "No site assigned"
                    }
                } else {
                    Log.e("AttendanceFragment", "Failed to fetch sites: " + sitesResponse.code())
                    tvSiteName.text = "Error loading site"
                }
                
            } catch (e: Exception) {
                Log.e("AttendanceFragment", "Error loading site", e)
                tvSiteName.text = "Error loading site"
            }
        }
        
        updateWorkerSpinner()
    }

    private fun updateWorkerSpinner() {
        val sharedPref = requireActivity().getSharedPreferences("ClockOutPrefs", Context.MODE_PRIVATE)
        val token = sharedPref.getString("access_token", "") ?: ""
        
        lifecycleScope.launch {
            try {
                val workersResponse = RetrofitInstance.api.getWorkers("Bearer " + token)
                
                if (workersResponse.isSuccessful) {
                    val workers = workersResponse.body() ?: emptyList()
                    Log.d("AttendanceFragment", "Fetched " + workers.size + " workers")
                    
                    val workerNames = workers.map { it.name }
                    val adapter = ArrayAdapter(
                        requireContext(),
                        android.R.layout.simple_spinner_item,
                        workerNames
                    )
                    adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
                    spinnerWorker.adapter = adapter
                } else {
                    Log.e("AttendanceFragment", "Failed to fetch workers: " + workersResponse.code())
                    Toast.makeText(requireContext(), "Error loading workers", Toast.LENGTH_SHORT).show()
                }
                
            } catch (e: Exception) {
                Log.e("AttendanceFragment", "Error loading workers", e)
                Toast.makeText(requireContext(), "Error loading workers", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun requestLocationUpdates() {
        if (ActivityCompat.checkSelfPermission(
                requireContext(),
                Manifest.permission.ACCESS_FINE_LOCATION
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(
                arrayOf(Manifest.permission.ACCESS_FINE_LOCATION),
                100
            )
            return
        }
        
        val locationRequest = LocationRequest.create().apply {
            interval = 10000
            fastestInterval = 5000
            priority = LocationRequest.PRIORITY_HIGH_ACCURACY
        }
        
        fusedLocationClient.requestLocationUpdates(
            locationRequest,
            locationCallback,
            Looper.getMainLooper()
        )
        
        tvGpsStatus.text = "Getting location..."
    }

    private fun validateGeofence(location: Location, site: Site) {
        val siteLocation = Location("").apply {
            latitude = site.latitude
            longitude = site.longitude
        }
        
        val distance = location.distanceTo(siteLocation)
        
        if (distance <= GEOFENCE_RADIUS) {
            tvGpsStatus.text = "Inside geofence"
            btnCheckIn.isEnabled = true
            btnCheckOut.isEnabled = true
        } else {
            tvGpsStatus.text = "Outside geofence (" + distance.toInt() + "m away)"
            btnCheckIn.isEnabled = false
            btnCheckOut.isEnabled = false
        }
    }

    private fun markAttendance(eventType: String) {
        val selectedWorkerName = spinnerWorker.selectedItem?.toString()
        
        if (selectedWorkerName == null) {
            Toast.makeText(requireContext(), "Please select a worker", Toast.LENGTH_SHORT).show()
            return
        }
        
        val location = currentLocation
        val site = currentSite
        
        if (location == null || site == null) {
            Toast.makeText(requireContext(), "GPS or site not ready", Toast.LENGTH_SHORT).show()
            return
        }
        
        val sharedPref = requireActivity().getSharedPreferences("ClockOutPrefs", Context.MODE_PRIVATE)
        
        val timestamp = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault()).format(Date())
        val eventId = UUID.randomUUID().toString()
        
        val event = JSONObject().apply {
            put("id", eventId)
            put("worker_name", selectedWorkerName)
            put("site_id", site.id)
            put("event_type", eventType)
            put("latitude", location.latitude)
            put("longitude", location.longitude)
            put("timestamp", timestamp)
        }
        
        val pendingEvents = sharedPref.getString("pending_events", "[]") ?: "[]"
        val eventsArray = JSONArray(pendingEvents)
        eventsArray.put(event)
        
        sharedPref.edit().putString("pending_events", eventsArray.toString()).apply()
        
        Toast.makeText(
            requireContext(),
            selectedWorkerName + " checked " + eventType,
            Toast.LENGTH_SHORT
        ).show()
        
        updateSyncStatus()
    }

    private fun updateSyncStatus() {
        val sharedPref = requireActivity().getSharedPreferences("ClockOutPrefs", Context.MODE_PRIVATE)
        val pendingEvents = sharedPref.getString("pending_events", "[]") ?: "[]"
        val eventsArray = JSONArray(pendingEvents)
        
        tvSyncStatus.text = eventsArray.length().toString() + " events pending sync"
    }

    override fun onResume() {
        super.onResume()
        currentSite?.let { requestLocationUpdates() }
    }

    override fun onPause() {
        super.onPause()
        fusedLocationClient.removeLocationUpdates(locationCallback)
    }
}