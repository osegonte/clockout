package com.example.clockoutandroid

import android.Manifest
import android.content.pm.PackageManager
import android.location.Location
import android.os.Bundle
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationServices
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

class MainActivity : AppCompatActivity() {
    
    // UI Elements
    private lateinit var tvSiteName: TextView
    private lateinit var tvGpsStatus: TextView
    private lateinit var tvDistance: TextView
    private lateinit var spinnerWorker: Spinner
    private lateinit var btnCheckIn: Button
    private lateinit var btnCheckOut: Button
    private lateinit var tvSyncStatus: TextView
    
    // Location
    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private var currentLocation: Location? = null
    
    // Test Data (will be replaced with API calls later)
    private val siteLat = 6.5244  // Lagos Farm
    private val siteLon = 3.3792
    private val siteRadius = 100.0 // meters
    private val workers = listOf("John Doe", "Jane Smith", "Samuel Obi")
    
    companion object {
        private const val LOCATION_PERMISSION_REQUEST_CODE = 1001
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        // Initialize UI
        tvSiteName = findViewById(R.id.tvSiteName)
        tvGpsStatus = findViewById(R.id.tvGpsStatus)
        tvDistance = findViewById(R.id.tvDistance)
        spinnerWorker = findViewById(R.id.spinnerWorker)
        btnCheckIn = findViewById(R.id.btnCheckIn)
        btnCheckOut = findViewById(R.id.btnCheckOut)
        tvSyncStatus = findViewById(R.id.tvSyncStatus)
        
        // Set site name
        tvSiteName.text = "Lagos Farm"
        
        // Setup worker spinner
        val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_item, workers)
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        spinnerWorker.adapter = adapter
        
        // Initialize location client
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)
        
        // Setup buttons
        btnCheckIn.setOnClickListener { checkIn() }
        btnCheckOut.setOnClickListener { checkOut() }
        
        // Request location permission and get location
        requestLocationPermission()
    }
    
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
        
        tvGpsStatus.text = "Getting location..."
        
        fusedLocationClient.lastLocation.addOnSuccessListener { location: Location? ->
            if (location != null) {
                currentLocation = location
                val distance = calculateDistance(
                    location.latitude, location.longitude,
                    siteLat, siteLon
                )
                
                tvGpsStatus.text = if (distance <= siteRadius) {
                    "✓ Inside geofence"
                } else {
                    "⚠ Outside geofence (${distance.toInt()}m away)"
                }
                
                tvDistance.text = "Distance: ${distance.toInt()}m"
                
                // Enable/disable buttons based on geofence
                val insideGeofence = distance <= siteRadius
                btnCheckIn.isEnabled = insideGeofence
                btnCheckOut.isEnabled = insideGeofence
                
            } else {
                tvGpsStatus.text = "❌ Could not get location"
            }
        }
    }
    
    private fun checkIn() {
        val worker = spinnerWorker.selectedItem as String
        val timestamp = LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)
        
        // TODO: Save to Room Database (offline queue)
        // TODO: Sync to API when online
        
        Toast.makeText(
            this,
            "✓ $worker checked in at $timestamp",
            Toast.LENGTH_SHORT
        ).show()
        
        tvSyncStatus.text = "⏳ 1 event pending sync"
    }
    
    private fun checkOut() {
        val worker = spinnerWorker.selectedItem as String
        val timestamp = LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME)
        
        // TODO: Save to Room Database (offline queue)
        // TODO: Sync to API when online
        
        Toast.makeText(
            this,
            "✓ $worker checked out at $timestamp",
            Toast.LENGTH_SHORT
        ).show()
        
        tvSyncStatus.text = "⏳ 1 event pending sync"
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