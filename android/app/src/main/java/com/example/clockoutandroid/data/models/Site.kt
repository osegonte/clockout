package com.example.clockoutandroid.data.models

import com.google.gson.annotations.SerializedName

data class Site(
    @SerializedName("id")
    val id: Int,
    
    @SerializedName("name")
    val name: String,
    
    @SerializedName("gps_lat")
    val latitude: Double,
    
    @SerializedName("gps_lon")
    val longitude: Double,
    
    @SerializedName("radius_m")
    val radius: Double
)