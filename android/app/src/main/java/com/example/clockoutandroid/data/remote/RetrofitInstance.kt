package com.example.clockoutandroid.data.remote

import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object RetrofitInstance {
    
    // FIXED: Changed to match ApiConfig.kt URL
    private const val BASE_URL = "https://clockout-3v34.onrender.com/api/v1/"

    // Add OkHttpClient with longer timeouts for Render.com cold starts
    private val okHttpClient = OkHttpClient.Builder()
        .connectTimeout(60, TimeUnit.SECONDS)  // Wait up to 60s for connection
        .readTimeout(60, TimeUnit.SECONDS)     // Wait up to 60s for response
        .writeTimeout(60, TimeUnit.SECONDS)    // Wait up to 60s for sending data
        .build()
    
    private val retrofit by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }
    
    val api: ApiService by lazy {
        retrofit.create(ApiService::class.java)
    }
}