package com.example.clockoutandroid.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.example.clockoutandroid.data.local.entities.AttendanceEventEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface AttendanceEventDao {
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(event: AttendanceEventEntity): Long
    
    @Query("SELECT * FROM attendance_events WHERE isSynced = 0 ORDER BY timestamp ASC")
    suspend fun getUnsyncedEvents(): List<AttendanceEventEntity>
    
    @Query("SELECT COUNT(*) FROM attendance_events WHERE isSynced = 0")
    fun getUnsyncedCount(): Flow<Int>
    
    @Query("UPDATE attendance_events SET isSynced = 1 WHERE id = :eventId")
    suspend fun markAsSynced(eventId: Int)
    
    @Query("SELECT * FROM attendance_events ORDER BY timestamp DESC LIMIT 50")
    fun getRecentEvents(): Flow<List<AttendanceEventEntity>>
    
    @Query("DELETE FROM attendance_events WHERE isSynced = 1 AND timestamp < date('now', '-7 days')")
    suspend fun deleteOldSyncedEvents()
}