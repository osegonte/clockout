package com.example.clockoutandroid.data.remote.dto

data class WorkerResponse(
    val id: Int,
    val name: String,
    val phone: String?,
    val employee_id: String?,
    val organization_id: Int,
    val site_id: Int?,
    val is_active: Boolean
)