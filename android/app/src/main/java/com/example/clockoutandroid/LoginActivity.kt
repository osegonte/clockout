package com.example.clockoutandroid

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.widget.CheckBox
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.example.clockoutandroid.databinding.ActivityLoginBinding
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

class LoginActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityLoginBinding
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Check if already logged in
        val prefs = getSharedPreferences("auth", Context.MODE_PRIVATE)
        val token = prefs.getString("token", null)
        val loginTime = prefs.getLong("login_time", 0)
        
        // Check if token is still valid (7 days)
        val tokenValid = token != null && (System.currentTimeMillis() - loginTime) < 7 * 24 * 60 * 60 * 1000
        
        if (tokenValid) {
            navigateToMain()
            return
        }
        
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        loadSavedCredentials()
        setupClickListeners()
    }
    
    private fun loadSavedCredentials() {
        val prefs = getSharedPreferences("auth", Context.MODE_PRIVATE)
        val savedEmail = prefs.getString("saved_email", "")
        val rememberMe = prefs.getBoolean("remember_me", false)
        
        if (rememberMe && !savedEmail.isNullOrEmpty()) {
            binding.etEmail.setText(savedEmail)
            binding.cbRememberMe.isChecked = true
        }
    }
    
    private fun setupClickListeners() {
        // Login button
        binding.btnLogin.setOnClickListener {
            val email = binding.etEmail.text.toString().trim()
            val password = binding.etPassword.text.toString()
            
            if (email.isEmpty()) {
                binding.etEmail.error = "Email is required"
                return@setOnClickListener
            }
            
            if (password.isEmpty()) {
                binding.etPassword.error = "Password is required"
                return@setOnClickListener
            }
            
            performLogin(email, password)
        }
        
        // Register link
        binding.tvRegister.setOnClickListener {
            val intent = Intent(this, RegisterActivity::class.java)
            startActivity(intent)
        }
        
        // Forgot password (placeholder for now)
        binding.tvForgotPassword.setOnClickListener {
            Toast.makeText(this, "Password reset coming soon", Toast.LENGTH_SHORT).show()
        }
    }
    
    private fun performLogin(email: String, password: String) {
        binding.btnLogin.isEnabled = false
        binding.btnLogin.text = "Signing in..."
        
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val url = URL("${ApiConfig.BASE_URL}/auth/login")
                val connection = url.openConnection() as HttpURLConnection
                
                connection.requestMethod = "POST"
                connection.setRequestProperty("Content-Type", "application/x-www-form-urlencoded")
                connection.doOutput = true
                
                // OAuth2 format requires username field (not email)
                val postData = "username=$email&password=$password"
                
                connection.outputStream.use { outputStream ->
                    outputStream.write(postData.toByteArray())
                }
                
                val responseCode = connection.responseCode
                
                if (responseCode == HttpURLConnection.HTTP_OK) {
                    val response = connection.inputStream.bufferedReader().readText()
                    val jsonResponse = JSONObject(response)
                    
                    // Extract data
                    val token = jsonResponse.getString("access_token")
                    val userObj = jsonResponse.getJSONObject("user")
                    
                    // Save to SharedPreferences
                    val prefs = getSharedPreferences("auth", Context.MODE_PRIVATE)
                    prefs.edit().apply {
                        putString("token", token)
                        putInt("user_id", userObj.getInt("id"))
                        putString("user_name", userObj.optString("full_name", ""))
                        putString("email", userObj.getString("email"))
                        putString("user_role", userObj.getString("role"))
                        putString("user_mode", userObj.getString("mode"))
                        putInt("organization_id", userObj.getInt("organization_id"))
                        putLong("login_time", System.currentTimeMillis())
                        
                        // Save remember me preference
                        val rememberMe = binding.cbRememberMe.isChecked
                        putBoolean("remember_me", rememberMe)
                        if (rememberMe) {
                            putString("saved_email", email)
                        } else {
                            remove("saved_email")
                        }
                        
                        apply()
                    }
                    
                    withContext(Dispatchers.Main) {
                        navigateToMain()
                    }
                } else {
                    withContext(Dispatchers.Main) {
                        Toast.makeText(this@LoginActivity, "Invalid email or password", Toast.LENGTH_SHORT).show()
                        binding.btnLogin.isEnabled = true
                        binding.btnLogin.text = "Sign In"
                    }
                }
                
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@LoginActivity, "Error: ${e.message}", Toast.LENGTH_LONG).show()
                    binding.btnLogin.isEnabled = true
                    binding.btnLogin.text = "Sign In"
                }
            }
        }
    }
    
    private fun navigateToMain() {
        val intent = Intent(this, MainActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        startActivity(intent)
        finish()
    }
}