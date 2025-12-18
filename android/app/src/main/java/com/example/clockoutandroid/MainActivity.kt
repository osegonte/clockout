package com.example.clockoutandroid

import android.Manifest
import android.content.pm.PackageManager
import android.location.Location
import android.os.Bundle
import android.provider.Settings
import android.util.Log
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.lifecycle.lifecycleScope
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationServices
import kotlinx.coroutines.launch
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import kotlin.math.*

import com.example.clockoutandroid.data.local.AppDatabase
import com.example.clockoutandroid.data.local.entities.AttendanceEventEntity
import com.example.clockoutandroid.data.local.entities.WorkerEntity
import com.example.clockoutandroid.data.local.entities.SiteEntity
import com.example.clockoutandroid.data.repository.AttendanceRepository

class MainActivity : AppCompatActivity() {
    
    // UI Components
    private lateinit var tvSiteName: TextView
    private lateinit var tvGpsStatus: TextView
    private lateinit var tvDistance: TextView
    private lateinit var spinnerWorker: Spinner
    private lateinit var btnCheckIn: Button
    private lateinit var btnCheckOut: Button
    private lateinit var tvSyncStatus: TextView
    private lateinit var btnSync: Button
    
    // Services
    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private lateinit var repository: AttendanceRepository
    
    // State
    private var currentLocation: Location? = null
    private var workers = listOf<WorkerEntity>()
    private var currentSite: SiteEntity? = null
    
    companion object {
        private const val LOCATION_PERMISSION_REQUEST_CODE = 1001
        private const val TAG = "ClockOut"
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        initializeComponents()
        setupClickListeners()
        requestLocationPermission()
        loadDataFromApi()
        observeUnsyncedCount()
    }
    
    // ==========================================
    // INITIALIZATION
    // ==========================================
    
    private fun initializeComponents() {
        // Initialize UI
        tvSiteName = findViewById(R.id.tvSiteName)
        tvGpsStatus = findViewById(R.id.tvGpsStatus)
        tvDistance = findViewById(R.id.tvDistance)
        spinnerWorker = findViewById(R.id.spinnerWorker)
        btnCheckIn = findViewById(R.id.btnCheckIn)
        btnCheckOut = findViewById(R.id.btnCheckOut)
        tvSyncStatus = findViewById(R.id.tvSyncStatus)
        btnSync = findViewById(R.id.btnSync)
        
        // Initialize services
        val database = AppDatabase.getDatabase(this)
        repository = AttendanceRepository(database)
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)
        
        // Initial state
        tvSiteName.text = "Loading site..."
        tvGpsStatus.text = "Initializing..."
        btnCheckIn.isEnabled = false
        btnCheckOut.isEnabled = false
    }
    
    private fun setupClickListeners() {
        btnCheckIn.setOnClickListener { recordAttendance("IN") }
        btnCheckOut.setOnClickListener { recordAttendance("OUT") }
        btnSync.setOnClickListener { syncToBackend() }
    }
    
    // ==========================================
    // DATA LOADING
    // ==========================================
    
    private fun loadDataFromApi() {
        lifecycleScope.launch {
            // Load sites
            repository.fetchSitesFromApi(organizationId = 1)
                .onSuccess { sites ->
                    if (sites.isNotEmpty()) {
                        currentSite = sites[0]
                        tvSiteName.text = "📍 ${currentSite?.name}"
                        getLocation() // Refresh location to validate geofence
                    }
                }
                .onFailure { error ->
                    Log.e(TAG, "Failed to fetch sites: ${error.message}")
                    showError("Failed to load site data")
                }
            
            // Load workers
            repository.fetchWorkersFromApi(organizationId = 1)
                .onSuccess { fetchedWorkers ->
                    workers = fetchedWorkers
                    updateWorkerSpinner()
                    Toast.makeText(
                        this@MainActivity,
                        "Loaded ${workers.size} workers",
                        Toast.LENGTH_SHORT
                    ).show()
                }
                .onFailure { error ->
                    Log.e(TAG, "Failed to fetch workers: ${error.message}")
                    showError("Failed to load workers")
                }
        }
    }
    
    private fun updateWorkerSpinner() {
        val workerNames = workers.map { it.name }
        val adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_item,
            workerNames
        )
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        spinnerWorker.adapter = adapter
    }
    
    private fun observeUnsyncedCount() {
        lifecycleScope.launch {
            repository.getUnsyncedCount().collect { count ->
                tvSyncStatus.text = if (count > 0) {
                    "⏳ $count event(s) pending"
                } else {
                    "✓ All synced"
                }
            }
        }
    }
    
    // ==========================================
    // LOCATION & GEOFENCE - UPDATED FOR FRESH GPS
    // ==========================================
    
    private fun requestLocationPermission() {
        if (ActivityCompat.checkSelfPermission(
                this,
                Manifest.permission.ACCESS_FINE_LOCATION
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.ACCESS_FINE_LOCATION),
                LOCATION_PERMISSION_REQUEST_CODE
            )
        } else {
            getLocation()
        }
    }
    
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == LOCATION_PERMISSION_REQUEST_CODE) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                getLocation()
            } else {
                tvGpsStatus.text = "❌ Location permission denied"
                Toast.makeText(this, "Location permission required", Toast.LENGTH_LONG).show()
            }
        }
    }
    
    private fun getLocation() {
        if (ActivityCompat.checkSelfPermission(
                this,
                Manifest.permission.ACCESS_FINE_LOCATION
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            return
        }
        
        tvGpsStatus.text = "Getting fresh location..."
        
        // ✅ REQUEST FRESH LOCATION INSTEAD OF CACHED
        val locationRequest = com.google.android.gms.location.LocationRequest.create().apply {
            priority = com.google.android.gms.location.LocationRequest.PRIORITY_HIGH_ACCURACY
            interval = 5000
            fastestInterval = 2000
            numUpdates = 1 // Get just one fresh update
        }
        
        val locationCallback = object : com.google.android.gms.location.LocationCallback() {
            override fun onLocationResult(locationResult: com.google.android.gms.location.LocationResult) {
                val location = locationResult.lastLocation
                currentLocation = location
                
                if (location == null) {
                    tvGpsStatus.text = "❌ Location unavailable"
                    return
                }
                
                // Log fresh coordinates
                Log.d(TAG, "✅ Fresh GPS: ${location.latitude}, ${location.longitude}")
                
                val site = currentSite
                if (site == null) {
                    tvGpsStatus.text = "⚠ Waiting for site data..."
                    return
                }
                
                validateGeofence(location, site)
            }
        }
        
        fusedLocationClient.requestLocationUpdates(
            locationRequest,
            locationCallback,
            null
        )
    }
    
    private fun validateGeofence(location: Location, site: SiteEntity) {
        val distance = calculateDistance(
            location.latitude, location.longitude,
            site.latitude, site.longitude
        )
        
        val insideGeofence = distance <= site.radius
        
        tvGpsStatus.text = if (insideGeofence) {
            "✓ Inside geofence"
        } else {
            "⚠ Outside geofence (${distance.toInt()}m away)"
        }
        
        tvDistance.text = "Distance: ${distance.toInt()}m"
        
        btnCheckIn.isEnabled = insideGeofence
        btnCheckOut.isEnabled = insideGeofence
        
        // Log validation result
        Log.d(TAG, "Geofence check: distance=${distance.toInt()}m, radius=${site.radius.toInt()}m, valid=$insideGeofence")
    }
    
    private fun calculateDistance(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
        val R = 6371000.0 // Earth radius in meters
        val phi1 = Math.toRadians(lat1)
        val phi2 = Math.toRadians(lat2)
        val deltaPhi = Math.toRadians(lat2 - lat1)
        val deltaLambda = Math.toRadians(lon2 - lon1)
        
        val a = sin(deltaPhi / 2) * sin(deltaPhi / 2) +
                cos(phi1) * cos(phi2) *
                sin(deltaLambda / 2) * sin(deltaLambda / 2)
        val c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        return R * c
    }
    
    // ==========================================
    // ATTENDANCE RECORDING
    // ==========================================
    
    private fun recordAttendance(eventType: String) {
        if (workers.isEmpty()) {
            showError("No workers available")
            return
        }
        
        val site = currentSite
        if (site == null) {
            showError("Site data not loaded")
            return
        }
        
        val location = currentLocation
        if (location == null) {
            showError("Location not available")
            return
        }
        
        val selectedWorker = workers[spinnerWorker.selectedItemPosition]
        val deviceId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID)
        val timestamp = LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)
        
        val event = AttendanceEventEntity(
            workerId = selectedWorker.id,
            workerName = selectedWorker.name,
            siteId = site.id,
            siteName = site.name,
            eventType = eventType,
            timestamp = timestamp,
            gpsLat = location.latitude,
            gpsLon = location.longitude,
            accuracy = location.accuracy,
            isSynced = false,
            deviceId = deviceId,
            isValid = true
        )
        
        lifecycleScope.launch {
            try {
                repository.saveEvent(event)
                val action = if (eventType == "IN") "checked IN" else "checked OUT"
                Toast.makeText(
                    this@MainActivity,
                    "✅ ${selectedWorker.name} $action",
                    Toast.LENGTH_SHORT
                ).show()
            } catch (e: Exception) {
                Log.e(TAG, "Failed to save event: ${e.message}")
                showError("Failed to save attendance")
            }
        }
    }
    
    // ==========================================
    // SYNC
    // ==========================================
    
    private fun syncToBackend() {
        lifecycleScope.launch {
            tvSyncStatus.text = "⏳ Syncing..."
            
            repository.syncEvents()
                .onSuccess { count ->
                    if (count > 0) {
                        Toast.makeText(
                            this@MainActivity,
                            "✅ Synced $count event(s)",
                            Toast.LENGTH_SHORT
                        ).show()
                    } else {
                        Toast.makeText(
                            this@MainActivity,
                            "No events to sync",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                }
                .onFailure { error ->
                    Log.e(TAG, "Sync failed: ${error.message}")
                    showError("Sync failed: ${error.message}")
                }
        }
    }
    
    // ==========================================
    // UTILITIES
    // ==========================================
    
    private fun showError(message: String) {
        Toast.makeText(this, "⚠ $message", Toast.LENGTH_SHORT).show()
    }
}