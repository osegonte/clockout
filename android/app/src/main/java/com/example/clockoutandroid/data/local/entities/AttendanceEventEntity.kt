package com.example.clockoutandroid.data.local.entities

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "attendance_events")
data class AttendanceEventEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Int = 0,
    
    val workerId: Int,
    val workerName: String,  // Cached for offline display
    
    val siteId: Int,
    val siteName: String,    // Cached for offline display
    
    val eventType: String,   // "IN" or "OUT"
    val timestamp: String,   // ISO format: "2025-12-17T08:05:00"
    
    val gpsLat: Double,
    val gpsLon: Double,
    val accuracy: Float,
    
    val isSynced: Boolean = false,  // Key flag for offline queue
    val deviceId: String,
    
    val isValid: Boolean = true,    // Geofence validation result
    val distanceM: Double? = null   // Distance from site center
)