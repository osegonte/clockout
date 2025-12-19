package com.example.clockoutandroid.data.remote

import retrofit2.http.Field
import retrofit2.http.FormUrlEncoded
import com.example.clockoutandroid.data.remote.dto.ClockEventRequest
import com.example.clockoutandroid.data.remote.dto.ClockEventResponse
import com.example.clockoutandroid.data.remote.dto.SiteResponse
import com.example.clockoutandroid.data.remote.dto.WorkerResponse
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

interface ApiService {
    
    @GET("workers")
    suspend fun getWorkers(
        @Query("organization_id") organizationId: Int? = null,
        @Query("site_id") siteId: Int? = null
    ): Response<List<WorkerResponse>>
    
    @GET("sites")
    suspend fun getSites(
        @Query("organization_id") organizationId: Int? = null
    ): Response<List<SiteResponse>>
    
    @POST("events")
    suspend fun createEvent(
        @Body event: ClockEventRequest
    ): Response<ClockEventResponse>
    
    @POST("events/bulk")
    suspend fun createEventsBulk(
        @Body events: List<ClockEventRequest>
    ): Response<List<ClockEventResponse>>
}

// Add these data classes
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

// Add this method to the ApiService interface
@FormUrlEncoded
@POST("auth/login")
suspend fun login(
    @Field("username") email: String,  // OAuth2 uses "username" field
    @Field("password") password: String
): Response<LoginResponse>