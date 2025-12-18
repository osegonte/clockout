package com.example.clockoutandroid.data.remote

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