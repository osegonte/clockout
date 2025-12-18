package com.example.clockoutandroid.data.remote

import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object RetrofitInstance {
    
    private const val BASE_URL = "https://clockout-3v34.onrender.com/api/v1/"
    
    private val retrofit by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }
    
    val api: ApiService by lazy {
        retrofit.create(ApiService::class.java)
    }
}