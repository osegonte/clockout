package com.example.clockoutandroid.data.local.entities

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "workers")
data class WorkerEntity(
    @PrimaryKey
    val id: Int,
    val name: String,
    val phone: String?,
    val siteId: Int
)