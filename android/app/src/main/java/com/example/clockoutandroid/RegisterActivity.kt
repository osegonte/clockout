package com.example.clockoutandroid

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.util.Patterns
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.example.clockoutandroid.databinding.ActivityRegisterBinding
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

class RegisterActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityRegisterBinding
    private var isLoading = false
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityRegisterBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        setupClickListeners()
    }
    
    private fun setupClickListeners() {
        // Register button
        binding.btnRegister.setOnClickListener {
            if (!isLoading) {
                validateAndRegister()
            }
        }
        
        // Already have account? Login
        binding.tvLogin.setOnClickListener {
            finish() // Go back to LoginActivity
        }
    }
    
    private fun validateAndRegister() {
        // Get input values
        val organizationName = binding.etOrganizationName.text.toString().trim()
        val adminName = binding.etAdminName.text.toString().trim()
        val email = binding.etEmail.text.toString().trim()
        val password = binding.etPassword.text.toString()
        val confirmPassword = binding.etConfirmPassword.text.toString()
        
        // Clear previous errors
        binding.etOrganizationName.error = null
        binding.etAdminName.error = null
        binding.etEmail.error = null
        binding.etPassword.error = null
        binding.etConfirmPassword.error = null
        
        // Validate organization name
        if (organizationName.isEmpty()) {
            binding.etOrganizationName.error = "Organization name is required"
            binding.etOrganizationName.requestFocus()
            return
        }
        
        if (organizationName.length < 3) {
            binding.etOrganizationName.error = "Organization name must be at least 3 characters"
            binding.etOrganizationName.requestFocus()
            return
        }
        
        // Validate admin name
        if (adminName.isEmpty()) {
            binding.etAdminName.error = "Your name is required"
            binding.etAdminName.requestFocus()
            return
        }
        
        // Validate email
        if (email.isEmpty()) {
            binding.etEmail.error = "Email is required"
            binding.etEmail.requestFocus()
            return
        }
        
        if (!Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
            binding.etEmail.error = "Please enter a valid email"
            binding.etEmail.requestFocus()
            return
        }
        
        // Validate password
        if (password.isEmpty()) {
            binding.etPassword.error = "Password is required"
            binding.etPassword.requestFocus()
            return
        }
        
        if (password.length < 6) {
            binding.etPassword.error = "Password must be at least 6 characters"
            binding.etPassword.requestFocus()
            return
        }
        
        // Validate confirm password
        if (confirmPassword.isEmpty()) {
            binding.etConfirmPassword.error = "Please confirm your password"
            binding.etConfirmPassword.requestFocus()
            return
        }
        
        if (password != confirmPassword) {
            binding.etConfirmPassword.error = "Passwords do not match"
            binding.etConfirmPassword.requestFocus()
            return
        }
        
        // All validations passed - proceed with registration
        performRegistration(organizationName, adminName, email, password)
    }
    
    private fun performRegistration(
        organizationName: String,
        adminName: String,
        email: String,
        password: String
    ) {
        isLoading = true
        binding.btnRegister.isEnabled = false
        binding.btnRegister.text = "Creating account..."
        
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val url = URL("${ApiConfig.BASE_URL}/auth/register/organization")
                val connection = url.openConnection() as HttpURLConnection
                
                connection.requestMethod = "POST"
                connection.setRequestProperty("Content-Type", "application/json")
                connection.doOutput = true
                
                // Create JSON request body
                val jsonBody = JSONObject().apply {
                    put("organization_name", organizationName)
                    put("admin_name", adminName)
                    put("email", email)
                    put("password", password)
                }
                
                // Send request
                connection.outputStream.use { outputStream ->
                    outputStream.write(jsonBody.toString().toByteArray())
                }
                
                val responseCode = connection.responseCode
                
                if (responseCode == HttpURLConnection.HTTP_CREATED) {
                    // Registration successful
                    val response = connection.inputStream.bufferedReader().readText()
                    val jsonResponse = JSONObject(response)
                    
                    withContext(Dispatchers.Main) {
                        Toast.makeText(
                            this@RegisterActivity,
                            "Account created successfully!",
                            Toast.LENGTH_SHORT
                        ).show()
                        
                        // Auto-login after registration
                        performAutoLogin(email, password)
                    }
                } else {
                    // Registration failed
                    val errorStream = connection.errorStream
                    val errorResponse = errorStream?.bufferedReader()?.readText() ?: "Unknown error"
                    
                    val errorMessage = try {
                        val errorJson = JSONObject(errorResponse)
                        errorJson.optString("detail", "Registration failed")
                    } catch (e: Exception) {
                        "Registration failed. Please try again."
                    }
                    
                    withContext(Dispatchers.Main) {
                        Toast.makeText(this@RegisterActivity, errorMessage, Toast.LENGTH_LONG).show()
                        resetButton()
                    }
                }
                
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(
                        this@RegisterActivity,
                        "Network error: ${e.message}",
                        Toast.LENGTH_LONG
                    ).show()
                    resetButton()
                }
            }
        }
    }
    
    private fun performAutoLogin(email: String, password: String) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val url = URL("${ApiConfig.BASE_URL}/auth/login")
                val connection = url.openConnection() as HttpURLConnection
                
                connection.requestMethod = "POST"
                connection.setRequestProperty("Content-Type", "application/x-www-form-urlencoded")
                connection.doOutput = true
                
                // OAuth2 format
                val postData = "username=$email&password=$password"
                
                connection.outputStream.use { outputStream ->
                    outputStream.write(postData.toByteArray())
                }
                
                val responseCode = connection.responseCode
                
                if (responseCode == HttpURLConnection.HTTP_OK) {
                    val response = connection.inputStream.bufferedReader().readText()
                    val jsonResponse = JSONObject(response)
                    
                    // Extract user data
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
                        apply()
                    }
                    
                    withContext(Dispatchers.Main) {
                        // Navigate to MainActivity
                        val intent = Intent(this@RegisterActivity, MainActivity::class.java)
                        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                        startActivity(intent)
                        finish()
                    }
                } else {
                    withContext(Dispatchers.Main) {
                        Toast.makeText(
                            this@RegisterActivity,
                            "Account created but login failed. Please login manually.",
                            Toast.LENGTH_LONG
                        ).show()
                        finish() // Go back to login screen
                    }
                }
                
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(
                        this@RegisterActivity,
                        "Account created but login failed. Please login manually.",
                        Toast.LENGTH_LONG
                    ).show()
                    finish()
                }
            }
        }
    }
    
    private fun resetButton() {
        isLoading = false
        binding.btnRegister.isEnabled = true
        binding.btnRegister.text = "Create Account"
    }
}