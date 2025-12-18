package com.example.clockoutandroid.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.example.clockoutandroid.data.local.entities.WorkerEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface WorkerDao {
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(workers: List<WorkerEntity>)
    
    @Query("SELECT * FROM workers ORDER BY name ASC")
    fun getAllWorkers(): Flow<List<WorkerEntity>>
    
    @Query("SELECT * FROM workers WHERE siteId = :siteId ORDER BY name ASC")
    fun getWorkersBySite(siteId: Int): Flow<List<WorkerEntity>>
    
    @Query("DELETE FROM workers")
    suspend fun deleteAll()
}