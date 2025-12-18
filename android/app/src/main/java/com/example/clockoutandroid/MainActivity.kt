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
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt
import kotlinx.coroutines.launch

// Database and API imports
import com.example.clockoutandroid.data.local.AppDatabase
import com.example.clockoutandroid.data.local.entities.AttendanceEventEntity
import com.example.clockoutandroid.data.local.entities.WorkerEntity
import com.example.clockoutandroid.data.local.entities.SiteEntity
import com.example.clockoutandroid.data.repository.AttendanceRepository

class MainActivity : AppCompatActivity() {
    
    // UI Elements
    private lateinit var tvSiteName: TextView
    private lateinit var tvGpsStatus: TextView
    private lateinit var tvDistance: TextView
    private lateinit var spinnerWorker: Spinner
    private lateinit var btnCheckIn: Button
    private lateinit var btnCheckOut: Button
    private lateinit var tvSyncStatus: TextView
    private lateinit var btnSync: Button
    
    // Location
    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private var currentLocation: Location? = null
    
    // Repository
    private lateinit var repository: AttendanceRepository
    
    // Data
    private var workers = listOf<WorkerEntity>()
    private var currentSite: SiteEntity? = null
    
    companion object {
        private const val LOCATION_PERMISSION_REQUEST_CODE = 1001
        private const val TAG = "ClockOut"
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        Log.d(TAG, "=== APP STARTED - API TEST MODE ===")
        
        // Initialize UI
        tvSiteName = findViewById(R.id.tvSiteName)
        tvGpsStatus = findViewById(R.id.tvGpsStatus)
        tvDistance = findViewById(R.id.tvDistance)
        spinnerWorker = findViewById(R.id.spinnerWorker)
        btnCheckIn = findViewById(R.id.btnCheckIn)
        btnCheckOut = findViewById(R.id.btnCheckOut)
        tvSyncStatus = findViewById(R.id.tvSyncStatus)
        btnSync = findViewById(R.id.btnSync)
        
        // Create SYNC button dynamically (we'll add it to layout later)
        btnSync = Button(this).apply {
            text = "SYNC NOW"
            setOnClickListener { syncToBackend() }
        }
        
        tvSiteName.text = "Loading..."
        tvSyncStatus.text = "Initializing..."
        
        // Initialize repository
        val database = AppDatabase.getDatabase(this)
        repository = AttendanceRepository(database)
        
        // Initialize location client
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)
        
        // Setup buttons
        btnCheckIn.setOnClickListener { checkIn() }
        btnCheckOut.setOnClickListener { checkOut() }
        
        // Request location permission
        requestLocationPermission()
        
        // Fetch data from API
        fetchDataFromApi()
        
        // Observe unsynced count
        observeUnsyncedCount()
    }
    
    // ============================================
    // FETCH DATA FROM API
    // ============================================
    private fun fetchDataFromApi() {
        lifecycleScope.launch {
            Log.d(TAG, "--- FETCHING DATA FROM API ---")
            
            // Fetch sites
            val sitesResult = repository.fetchSitesFromApi(organizationId = 1)
            sitesResult.onSuccess { sites ->
                if (sites.isNotEmpty()) {
                    currentSite = sites[0]  // Use first site for testing
                    tvSiteName.text = "📍 ${currentSite?.name} (from API)"
                    Log.d(TAG, "✅ Site loaded: ${currentSite?.name}")
                }
            }.onFailure { error ->
                Log.e(TAG, "❌ Failed to fetch sites", error)
                tvSiteName.text = "⚠ Failed to load site"
                Toast.makeText(
                    this@MainActivity,
                    "Failed to fetch sites: ${error.message}",
                    Toast.LENGTH_LONG
                ).show()
            }
            
            // Fetch workers
            val workersResult = repository.fetchWorkersFromApi(organizationId = 1)
            workersResult.onSuccess { fetchedWorkers ->
                workers = fetchedWorkers
                updateWorkerSpinner()
                Log.d(TAG, "✅ Workers loaded: ${workers.size} workers")
                Toast.makeText(
                    this@MainActivity,
                    "✅ Loaded ${workers.size} workers from API",
                    Toast.LENGTH_SHORT
                ).show()
            }.onFailure { error ->
                Log.e(TAG, "❌ Failed to fetch workers", error)
                Toast.makeText(
                    this@MainActivity,
                    "Failed to fetch workers: ${error.message}",
                    Toast.LENGTH_LONG
                ).show()
                // Use fallback hardcoded data
                useFallbackData()
            }
        }
    }
    
    private fun useFallbackData() {
        Log.w(TAG, "Using fallback hardcoded data")
        workers = listOf(
            WorkerEntity(id = 1, name = "John Doe (local)", phone = null, siteId = 1),
            WorkerEntity(id = 2, name = "Jane Smith (local)", phone = null, siteId = 1),
            WorkerEntity(id = 3, name = "Samuel Obi (local)", phone = null, siteId = 1)
        )
        updateWorkerSpinner()
        
        currentSite = SiteEntity(
            id = 1,
            name = "Lagos Farm (local)",
            latitude = 6.5244,
            longitude = 3.3792,
            radius = 100.0
        )
        tvSiteName.text = "📍 ${currentSite?.name} (offline mode)"
    }
    
    private fun updateWorkerSpinner() {
        val workerNames = workers.map { it.name }
        val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_item, workerNames)
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        spinnerWorker.adapter = adapter
    }
    
    // ============================================
    // OBSERVE UNSYNCED COUNT
    // ============================================
    private fun observeUnsyncedCount() {
        lifecycleScope.launch {
            repository.getUnsyncedCount().collect { count ->
                tvSyncStatus.text = if (count > 0) {
                    "⏳ $count event(s) pending sync"
                } else {
                    "✓ All synced"
                }
                Log.d(TAG, "Unsynced events: $count")
            }
        }
    }
    
    // ============================================
    // LOCATION
    // ============================================
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
        
        tvGpsStatus.text = "Getting location..."
        
        fusedLocationClient.lastLocation.addOnSuccessListener { location: Location? ->
            if (location != null) {
                currentLocation = location
                
                if (currentSite != null) {
                    val distance = calculateDistance(
                        location.latitude, location.longitude,
                        currentSite!!.latitude, currentSite!!.longitude
                    )
                    
                    tvGpsStatus.text = if (distance <= currentSite!!.radius) {
                        "✓ Inside geofence"
                    } else {
                        "⚠ Outside geofence (${distance.toInt()}m away)"
                    }
                    
                    tvDistance.text = "Distance: ${distance.toInt()}m"
                    
                    // Enable/disable buttons based on geofence
                    val insideGeofence = distance <= currentSite!!.radius
                    btnCheckIn.isEnabled = insideGeofence
                    btnCheckOut.isEnabled = insideGeofence
                    
                    Log.d(TAG, "GPS: ${location.latitude}, ${location.longitude} | Distance: ${distance}m")
                } else {
                    tvGpsStatus.text = "⚠ Site data not loaded yet"
                }
                
            } else {
                tvGpsStatus.text = "❌ Could not get location"
            }
        }
    }
    
    // ============================================
    // CHECK IN
    // ============================================
    private fun checkIn() {
        if (workers.isEmpty()) {
            Toast.makeText(this, "⚠ No workers loaded", Toast.LENGTH_SHORT).show()
            return
        }
        
        if (currentSite == null) {
            Toast.makeText(this, "⚠ No site loaded", Toast.LENGTH_SHORT).show()
            return
        }
        
        val selectedWorker = workers[spinnerWorker.selectedItemPosition]
        val timestamp = LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)
        val deviceId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID)
        
        val event = AttendanceEventEntity(
            workerId = selectedWorker.id,
            workerName = selectedWorker.name,
            siteId = currentSite!!.id,
            siteName = currentSite!!.name,
            eventType = "IN",
            timestamp = timestamp,
            gpsLat = currentLocation?.latitude ?: 0.0,
            gpsLon = currentLocation?.longitude ?: 0.0,
            accuracy = currentLocation?.accuracy ?: 0f,
            isSynced = false,
            deviceId = deviceId,
            isValid = true
        )
        
        lifecycleScope.launch {
            try {
                val eventId = repository.saveEvent(event)
                Log.d(TAG, "✅ CHECK IN saved: Event ID $eventId")
                Toast.makeText(
                    this@MainActivity,
                    "✅ ${selectedWorker.name} checked IN",
                    Toast.LENGTH_SHORT
                ).show()
            } catch (e: Exception) {
                Log.e(TAG, "❌ Error saving check-in", e)
                Toast.makeText(
                    this@MainActivity,
                    "❌ Error: ${e.message}",
                    Toast.LENGTH_LONG
                ).show()
            }
        }
    }
    
    // ============================================
    // CHECK OUT
    // ============================================
    private fun checkOut() {
        if (workers.isEmpty()) {
            Toast.makeText(this, "⚠ No workers loaded", Toast.LENGTH_SHORT).show()
            return
        }
        
        if (currentSite == null) {
            Toast.makeText(this, "⚠ No site loaded", Toast.LENGTH_SHORT).show()
            return
        }
        
        val selectedWorker = workers[spinnerWorker.selectedItemPosition]
        val timestamp = LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)
        val deviceId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID)
        
        val event = AttendanceEventEntity(
            workerId = selectedWorker.id,
            workerName = selectedWorker.name,
            siteId = currentSite!!.id,
            siteName = currentSite!!.name,
            eventType = "OUT",
            timestamp = timestamp,
            gpsLat = currentLocation?.latitude ?: 0.0,
            gpsLon = currentLocation?.longitude ?: 0.0,
            accuracy = currentLocation?.accuracy ?: 0f,
            isSynced = false,
            deviceId = deviceId,
            isValid = true
        )
        
        lifecycleScope.launch {
            try {
                val eventId = repository.saveEvent(event)
                Log.d(TAG, "✅ CHECK OUT saved: Event ID $eventId")
                Toast.makeText(
                    this@MainActivity,
                    "✅ ${selectedWorker.name} checked OUT",
                    Toast.LENGTH_SHORT
                ).show()
            } catch (e: Exception) {
                Log.e(TAG, "❌ Error saving check-out", e)
                Toast.makeText(
                    this@MainActivity,
                    "❌ Error: ${e.message}",
                    Toast.LENGTH_LONG
                ).show()
            }
        }
    }
    
    // ============================================
    // SYNC TO BACKEND
    // ============================================
    private fun syncToBackend() {
        Log.d(TAG, "--- MANUAL SYNC TRIGGERED ---")
        
        lifecycleScope.launch {
            try {
                tvSyncStatus.text = "⏳ Syncing..."
                
                val result = repository.syncEvents()
                
                result.onSuccess { count ->
                    Log.d(TAG, "✅ Sync successful: $count events synced")
                    Toast.makeText(
                        this@MainActivity,
                        "✅ Synced $count event(s) to backend!",
                        Toast.LENGTH_LONG
                    ).show()
                }.onFailure { error ->
                    Log.e(TAG, "❌ Sync failed", error)
                    Toast.makeText(
                        this@MainActivity,
                        "❌ Sync failed: ${error.message}",
                        Toast.LENGTH_LONG
                    ).show()
                }
            } catch (e: Exception) {
                Log.e(TAG, "❌ Sync error", e)
                Toast.makeText(
                    this@MainActivity,
                    "❌ Sync error: ${e.message}",
                    Toast.LENGTH_LONG
                ).show()
            }
        }
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
}