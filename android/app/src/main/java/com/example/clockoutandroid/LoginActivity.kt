package com.example.clockoutandroid

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import org.json.JSONObject

class LoginActivity : AppCompatActivity() {
    
    private lateinit var etEmail: EditText
    private lateinit var etPassword: EditText
    private lateinit var btnLogin: Button
    private lateinit var tvError: TextView
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Check if already logged in
        if (isLoggedIn()) {
            navigateToMain()
            return
        }
        
        setContentView(R.layout.activity_login)
        
        etEmail = findViewById(R.id.etEmail)
        etPassword = findViewById(R.id.etPassword)
        btnLogin = findViewById(R.id.btnLogin)
        tvError = findViewById(R.id.tvError)
        
        btnLogin.setOnClickListener {
            val email = etEmail.text.toString().trim()
            val password = etPassword.text.toString()
            
            if (email.isEmpty() || password.isEmpty()) {
                tvError.text = "Please enter email and password"
                tvError.visibility = TextView.VISIBLE
                return@setOnClickListener
            }
            
            login(email, password)
        }
    }
    
    private fun login(email: String, password: String) {
        btnLogin.isEnabled = false
        btnLogin.text = "Logging in..."
        tvError.visibility = TextView.GONE
        
        lifecycleScope.launch {
            try {
                // Call backend login API
                val response = com.example.clockoutandroid.data.remote.RetrofitInstance.api.login(email, password)
                
                if (response.isSuccessful && response.body() != null) {
                    val loginResponse = response.body()!!
                    
                    // Save token and user data
                    saveAuthData(
                        token = loginResponse.access_token,
                        userId = loginResponse.user.id,
                        userMode = loginResponse.user.mode,
                        assignedSites = loginResponse.user.assigned_sites
                    )
                    
                    Toast.makeText(this@LoginActivity, "Welcome ${loginResponse.user.full_name}!", Toast.LENGTH_SHORT).show()
                    navigateToMain()
                } else {
                    tvError.text = "Invalid email or password"
                    tvError.visibility = TextView.VISIBLE
                    btnLogin.isEnabled = true
                    btnLogin.text = "LOGIN"
                }
            } catch (e: Exception) {
                tvError.text = "Connection error: ${e.message}"
                tvError.visibility = TextView.VISIBLE
                btnLogin.isEnabled = true
                btnLogin.text = "LOGIN"
            }
        }
    }
    
    private fun saveAuthData(token: String, userId: Int, userMode: String, assignedSites: List<Int>) {
        val prefs = getSharedPreferences("auth", Context.MODE_PRIVATE)
        prefs.edit().apply {
            putString("token", token)
            putInt("user_id", userId)
            putString("user_mode", userMode)
            putString("assigned_sites", assignedSites.joinToString(","))
            putLong("login_time", System.currentTimeMillis())
            apply()
        }
    }
    
    private fun isLoggedIn(): Boolean {
        val prefs = getSharedPreferences("auth", Context.MODE_PRIVATE)
        val token = prefs.getString("token", null)
        val loginTime = prefs.getLong("login_time", 0)
        
        // Token expires after 7 days (same as backend)
        val tokenValid = token != null && (System.currentTimeMillis() - loginTime) < 7 * 24 * 60 * 60 * 1000
        
        return tokenValid
    }
    
    private fun navigateToMain() {
        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }
}