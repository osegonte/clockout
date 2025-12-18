package com.example.clockoutandroid.data.remote.dto

data class SiteResponse(
    val id: Int,
    val name: String,
    val organization_id: Int,
    val gps_lat: Double,
    val gps_lon: Double,
    val radius_m: Double
)