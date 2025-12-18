package com.example.clockoutandroid.data.remote.dto

data class ClockEventResponse(
    val id: Int,
    val worker_id: Int,
    val site_id: Int,
    val event_type: String,
    val event_timestamp: String,
    val gps_lat: Double,
    val gps_lon: Double,
    val is_valid: Boolean,
    val distance_m: Double?
)