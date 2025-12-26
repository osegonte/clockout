package com.example.clockoutandroid.data.remote

import retrofit2.http.Field
import retrofit2.http.FormUrlEncoded
import retrofit2.http.Header
import com.example.clockoutandroid.data.models.Site
import com.example.clockoutandroid.data.models.Worker
import com.example.clockoutandroid.data.remote.dto.ClockEventRequest
import com.example.clockoutandroid.data.remote.dto.ClockEventResponse
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

interface ApiService {
    
    @GET("workers")
    suspend fun getWorkers(
        @Header("Authorization") token: String,
        @Query("organization_id") organizationId: Int? = null,
        @Query("site_id") siteId: Int? = null
    ): Response<List<Worker>>
    
    @GET("sites")
    suspend fun getSites(
        @Header("Authorization") token: String,
        @Query("organization_id") organizationId: Int? = null
    ): Response<List<Site>>
    
    @POST("events")
    suspend fun createEvent(
        @Body event: ClockEventRequest
    ): Response<ClockEventResponse>
    
    @POST("events/bulk")
    suspend fun createEventsBulk(
        @Body events: List<ClockEventRequest>
    ): Response<List<ClockEventResponse>>
    
    @FormUrlEncoded
    @POST("auth/login")
    suspend fun login(
        @Field("username") email: String,
        @Field("password") password: String
    ): Response<LoginResponse>
}

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