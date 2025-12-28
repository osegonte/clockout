package com.example.clockoutandroid.data.remote

import retrofit2.http.*
import com.example.clockoutandroid.data.models.Site
import com.example.clockoutandroid.data.models.Worker
import com.example.clockoutandroid.data.remote.dto.ClockEventRequest
import com.example.clockoutandroid.data.remote.dto.ClockEventResponse
import retrofit2.Response

interface ApiService {
    
    // ==========================================
    // AUTHENTICATION
    // ==========================================
    
    @FormUrlEncoded
    @POST("auth/login")
    suspend fun login(
        @Field("username") email: String,
        @Field("password") password: String
    ): Response<LoginResponse>
    
    // ==========================================
    // SITES - FULL CRUD
    // ==========================================
    
    @GET("sites")
    suspend fun getSites(
        @Header("Authorization") token: String,
        @Query("organization_id") organizationId: Int? = null
    ): Response<List<Site>>
    
    @POST("sites")
    suspend fun createSite(
        @Header("Authorization") token: String,
        @Body site: SiteCreateRequest
    ): Response<Site>
    
    @PUT("sites/{site_id}")
    suspend fun updateSite(
        @Header("Authorization") token: String,
        @Path("site_id") siteId: Int,
        @Body site: SiteCreateRequest
    ): Response<Site>
    
    @DELETE("sites/{site_id}")
    suspend fun deleteSite(
        @Header("Authorization") token: String,
        @Path("site_id") siteId: Int
    ): Response<Unit>
    
    // ==========================================
    // WORKERS - FULL CRUD
    // ==========================================
    
    @GET("workers")
    suspend fun getWorkers(
        @Header("Authorization") token: String,
        @Query("organization_id") organizationId: Int? = null,
        @Query("site_id") siteId: Int? = null
    ): Response<List<Worker>>
    
    @POST("workers")
    suspend fun createWorker(
        @Header("Authorization") token: String,
        @Body worker: WorkerCreateRequest
    ): Response<Worker>
    
    @PUT("workers/{worker_id}")
    suspend fun updateWorker(
        @Header("Authorization") token: String,
        @Path("worker_id") workerId: Int,
        @Body worker: WorkerCreateRequest
    ): Response<Worker>
    
    @DELETE("workers/{worker_id}")
    suspend fun deleteWorker(
        @Header("Authorization") token: String,
        @Path("worker_id") workerId: Int
    ): Response<Unit>
    
    // ==========================================
    // ATTENDANCE EVENTS
    // ==========================================
    
    @POST("events")
    suspend fun createEvent(
        @Header("Authorization") token: String,
        @Body event: ClockEventRequest
    ): Response<ClockEventResponse>
    
    @POST("events/bulk")
    suspend fun createEventsBulk(
        @Header("Authorization") token: String,
        @Body events: List<ClockEventRequest>
    ): Response<List<ClockEventResponse>>
}

// ==========================================
// DATA CLASSES
// ==========================================

data class LoginResponse(
    val access_token: String,
    val token_type: String,
    val user: UserData
)

data class UserData(
    val id: Int,
    val email: String,
    val full_name: String?,
    val role: String,
    val mode: String,
    val assigned_sites: List<Int>,
    val organization_id: Int
)

data class SiteCreateRequest(
    val name: String,
    val gps_lat: Double,
    val gps_lon: Double,
    val radius_m: Double
)

data class WorkerCreateRequest(
    val name: String,
    val phone: String?,
    val employee_id: String?,
    val site_id: Int?
)