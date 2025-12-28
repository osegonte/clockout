package com.example.clockoutandroid

object ApiConfig {
    // Production backend URL - CORRECTED to match actual Render deployment
    const val BASE_URL = "https://clockout-3v34.onrender.com/api/v1"
    
    // Endpoints (for reference)
    object Endpoints {
        const val LOGIN = "/auth/login"
        const val REGISTER = "/auth/register/organization"
        const val WORKERS = "/workers/"
        const val SITES = "/sites/"
        const val EVENTS = "/events/"
    }
}