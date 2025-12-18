package com.example.clockoutandroid.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.example.clockoutandroid.data.local.entities.SiteEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface SiteDao {
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(sites: List<SiteEntity>)
    
    @Query("SELECT * FROM sites")
    fun getAllSites(): Flow<List<SiteEntity>>
    
    @Query("SELECT * FROM sites WHERE id = :siteId")
    suspend fun getSiteById(siteId: Int): SiteEntity?
    
    @Query("DELETE FROM sites")
    suspend fun deleteAll()
}