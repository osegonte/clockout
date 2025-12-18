package com.example.clockoutandroid.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import com.example.clockoutandroid.data.local.dao.AttendanceEventDao
import com.example.clockoutandroid.data.local.dao.SiteDao
import com.example.clockoutandroid.data.local.dao.WorkerDao
import com.example.clockoutandroid.data.local.entities.AttendanceEventEntity
import com.example.clockoutandroid.data.local.entities.SiteEntity
import com.example.clockoutandroid.data.local.entities.WorkerEntity

@Database(
    entities = [
        AttendanceEventEntity::class,
        WorkerEntity::class,
        SiteEntity::class
    ],
    version = 1,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    
    abstract fun attendanceEventDao(): AttendanceEventDao
    abstract fun workerDao(): WorkerDao
    abstract fun siteDao(): SiteDao
    
    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null
        
        fun getDatabase(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "clockout_database"
                )
                    .fallbackToDestructiveMigration()
                    .build()
                INSTANCE = instance
                instance
            }
        }
    }
}