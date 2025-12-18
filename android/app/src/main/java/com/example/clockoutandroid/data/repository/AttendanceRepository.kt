package com.example.clockoutandroid.data.repository

import android.util.Log
import com.example.clockoutandroid.data.local.AppDatabase
import com.example.clockoutandroid.data.local.entities.AttendanceEventEntity
import com.example.clockoutandroid.data.local.entities.SiteEntity
import com.example.clockoutandroid.data.local.entities.WorkerEntity
import com.example.clockoutandroid.data.remote.RetrofitInstance
import com.example.clockoutandroid.data.remote.dto.ClockEventRequest
import kotlinx.coroutines.flow.Flow

class AttendanceRepository(private val database: AppDatabase) {
    
    private val TAG = "AttendanceRepository"
    private val api = RetrofitInstance.api
    
    // ============================================
    // LOCAL DATABASE OPERATIONS
    // ============================================
    
    suspend fun saveEvent(event: AttendanceEventEntity): Long {
        return database.attendanceEventDao().insert(event)
    }
    
    fun getUnsyncedCount(): Flow<Int> {
        return database.attendanceEventDao().getUnsyncedCount()
    }
    
    suspend fun getUnsyncedEvents(): List<AttendanceEventEntity> {
        return database.attendanceEventDao().getUnsyncedEvents()
    }
    
    fun getRecentEvents(): Flow<List<AttendanceEventEntity>> {
        return database.attendanceEventDao().getRecentEvents()
    }
    
    // ============================================
    // WORKERS
    // ============================================
    
    fun getAllWorkers(): Flow<List<WorkerEntity>> {
        return database.workerDao().getAllWorkers()
    }
    
    suspend fun fetchWorkersFromApi(organizationId: Int = 1, siteId: Int? = null): Result<List<WorkerEntity>> {
        return try {
            Log.d(TAG, "Fetching workers from API...")
            val response = api.getWorkers(organizationId, siteId)
            
            if (response.isSuccessful && response.body() != null) {
                val workers = response.body()!!.map { dto ->
                    WorkerEntity(
                        id = dto.id,
                        name = dto.name,
                        phone = dto.phone,
                        siteId = dto.site_id ?: 1
                    )
                }
                
                // Save to local database
                database.workerDao().deleteAll()
                database.workerDao().insertAll(workers)
                
                Log.d(TAG, "Fetched ${workers.size} workers from API")
                Result.success(workers)
            } else {
                Log.e(TAG, "API error: ${response.code()} - ${response.message()}")
                Result.failure(Exception("Failed to fetch workers: ${response.message()}"))
            }
        } catch (e: Exception) {
            Log.e(TAG, "Network error fetching workers", e)
            Result.failure(e)
        }
    }
    
    // ============================================
    // SITES
    // ============================================
    
    fun getAllSites(): Flow<List<SiteEntity>> {
        return database.siteDao().getAllSites()
    }
    
    suspend fun getSiteById(siteId: Int): SiteEntity? {
        return database.siteDao().getSiteById(siteId)
    }
    
    suspend fun fetchSitesFromApi(organizationId: Int = 1): Result<List<SiteEntity>> {
        return try {
            Log.d(TAG, "Fetching sites from API...")
            val response = api.getSites(organizationId)
            
            if (response.isSuccessful && response.body() != null) {
                val sites = response.body()!!.map { dto ->
                    SiteEntity(
                        id = dto.id,
                        name = dto.name,
                        latitude = dto.gps_lat,
                        longitude = dto.gps_lon,
                        radius = dto.radius_m
                    )
                }
                
                // Save to local database
                database.siteDao().deleteAll()
                database.siteDao().insertAll(sites)
                
                Log.d(TAG, "Fetched ${sites.size} sites from API")
                Result.success(sites)
            } else {
                Log.e(TAG, "API error: ${response.code()} - ${response.message()}")
                Result.failure(Exception("Failed to fetch sites: ${response.message()}"))
            }
        } catch (e: Exception) {
            Log.e(TAG, "Network error fetching sites", e)
            Result.failure(e)
        }
    }
    
    // ============================================
    // SYNC EVENTS TO API
    // ============================================
    
    suspend fun syncEvents(): Result<Int> {
        return try {
            val unsyncedEvents = database.attendanceEventDao().getUnsyncedEvents()
            
            if (unsyncedEvents.isEmpty()) {
                Log.d(TAG, "No events to sync")
                return Result.success(0)
            }
            
            Log.d(TAG, "Syncing ${unsyncedEvents.size} events to API...")
            
            // Convert to API format
            val apiEvents = unsyncedEvents.map { event ->
                ClockEventRequest(
                    worker_id = event.workerId,
                    site_id = event.siteId,
                    device_id = event.deviceId,
                    event_type = event.eventType,
                    event_timestamp = event.timestamp,
                    gps_lat = event.gpsLat,
                    gps_lon = event.gpsLon,
                    accuracy_m = event.accuracy
                )
            }
            
            // Send to API
            val response = api.createEventsBulk(apiEvents)
            
            if (response.isSuccessful && response.body() != null) {
                val syncedCount = response.body()!!.size
                
                // Mark as synced in local database
                unsyncedEvents.forEach { event ->
                    database.attendanceEventDao().markAsSynced(event.id)
                }
                
                Log.d(TAG, "Successfully synced $syncedCount events")
                Result.success(syncedCount)
            } else {
                Log.e(TAG, "Sync failed: ${response.code()} - ${response.message()}")
                Result.failure(Exception("Sync failed: ${response.message()}"))
            }
        } catch (e: Exception) {
            Log.e(TAG, "Network error during sync", e)
            Result.failure(e)
        }
    }
}