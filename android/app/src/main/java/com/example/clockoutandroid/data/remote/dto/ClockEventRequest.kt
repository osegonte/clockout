package com.example.clockoutandroid.data.remote.dto

data class ClockEventRequest(
    val worker_id: Int,
    val site_id: Int,
    val device_id: String,
    val event_type: String,
    val event_timestamp: String,  // ISO format: "2025-12-17T08:05:00"
    val gps_lat: Double,
    val gps_lon: Double,
    val accuracy_m: Float?
)