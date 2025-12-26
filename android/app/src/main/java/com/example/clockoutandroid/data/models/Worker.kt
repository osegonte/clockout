package com.example.clockoutandroid.data.models

import com.google.gson.annotations.SerializedName

data class Worker(
    @SerializedName("id")
    val id: Int,
    
    @SerializedName("name")
    val name: String,
    
    @SerializedName("phone")
    val phone: String?,
    
    @SerializedName("employee_id")
    val employeeId: String?,
    
    @SerializedName("site_id")
    val siteId: Int?,
    
    @SerializedName("is_active")
    val isActive: Boolean
)