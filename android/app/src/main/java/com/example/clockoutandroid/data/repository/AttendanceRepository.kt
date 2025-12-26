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
    
    fun getAllWorkers(): Flow<List<WorkerEntity>> {
        return database.workerDao().getAllWorkers()
    }
    
    suspend fun fetchWorkersFromApi(token: String, organizationId: Int? = null, siteId: Int? = null): Result<Int> {
        return try {
            Log.d(TAG, "Fetching workers from API...")
            val response = api.getWorkers("Bearer " + token, organizationId, siteId)
            
            if (response.isSuccessful && response.body() != null) {
                val workers = response.body()!!
                
                val workerEntities = workers.map { worker ->
                    WorkerEntity(
                        id = worker.id,
                        name = worker.name,
                        phone = worker.phone,
                        siteId = worker.siteId ?: 1
                    )
                }
                
                database.workerDao().deleteAll()
                database.workerDao().insertAll(workerEntities)
                
                Log.d(TAG, "Fetched " + workers.size + " workers from API")
                Result.success(workers.size)
            } else {
                Log.e(TAG, "API error: " + response.code())
                Result.failure(Exception("Failed to fetch workers"))
            }
        } catch (e: Exception) {
            Log.e(TAG, "Network error fetching workers", e)
            Result.failure(e)
        }
    }
    
    fun getAllSites(): Flow<List<SiteEntity>> {
        return database.siteDao().getAllSites()
    }
    
    suspend fun getSiteById(siteId: Int): SiteEntity? {
        return database.siteDao().getSiteById(siteId)
    }
    
    suspend fun fetchSitesFromApi(token: String, organizationId: Int? = null): Result<Int> {
        return try {
            Log.d(TAG, "Fetching sites from API...")
            val response = api.getSites("Bearer " + token, organizationId)
            
            if (response.isSuccessful && response.body() != null) {
                val sites = response.body()!!
                
                val siteEntities = sites.map { site ->
                    SiteEntity(
                        id = site.id,
                        name = site.name,
                        latitude = site.latitude,
                        longitude = site.longitude,
                        radius = site.radius
                    )
                }
                
                database.siteDao().deleteAll()
                database.siteDao().insertAll(siteEntities)
                
                Log.d(TAG, "Fetched " + sites.size + " sites from API")
                Result.success(sites.size)
            } else {
                Log.e(TAG, "API error: " + response.code())
                Result.failure(Exception("Failed to fetch sites"))
            }
        } catch (e: Exception) {
            Log.e(TAG, "Network error fetching sites", e)
            Result.failure(e)
        }
    }
    
    suspend fun syncEvents(): Result<Int> {
        return try {
            val unsyncedEvents = database.attendanceEventDao().getUnsyncedEvents()
            
            if (unsyncedEvents.isEmpty()) {
                Log.d(TAG, "No events to sync")
                return Result.success(0)
            }
            
            Log.d(TAG, "Syncing " + unsyncedEvents.size + " events to API...")
            
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
            
            val response = api.createEventsBulk(apiEvents)
            
            if (response.isSuccessful && response.body() != null) {
                val syncedCount = response.body()!!.size
                
                unsyncedEvents.forEach { event ->
                    database.attendanceEventDao().markAsSynced(event.id)
                }
                
                Log.d(TAG, "Successfully synced " + syncedCount + " events")
                Result.success(syncedCount)
            } else {
                Log.e(TAG, "Sync failed: " + response.code())
                Result.failure(Exception("Sync failed"))
            }
        } catch (e: Exception) {
            Log.e(TAG, "Network error during sync", e)
            Result.failure(e)
        }
    }
}
