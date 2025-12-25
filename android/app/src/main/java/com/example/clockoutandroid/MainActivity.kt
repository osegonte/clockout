package com.example.clockoutandroid

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.Fragment
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.example.clockoutandroid.ui.fragments.*

class MainActivity : AppCompatActivity() {
    
    private lateinit var bottomNav: BottomNavigationView
    private var userMode: String = "manager"  // Will load from SharedPreferences
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Check authentication
        if (!isLoggedIn()) {
            navigateToLogin()
            return
        }
        
        // Load user mode
        loadUserMode()
        
        // Set content view to new container layout
        setContentView(R.layout.activity_main_container)
        
        // Setup navigation
        setupBottomNavigation()
        
        // Load default fragment (Home)
        if (savedInstanceState == null) {
            loadFragment(HomeFragment())
        }
    }
    
    private fun isLoggedIn(): Boolean {
        val prefs = getSharedPreferences("auth", Context.MODE_PRIVATE)
        val token = prefs.getString("token", null)
        val loginTime = prefs.getLong("login_time", 0)
        
        // Token expires after 7 days
        val tokenValid = token != null && (System.currentTimeMillis() - loginTime) < 7 * 24 * 60 * 60 * 1000
        
        return tokenValid
    }
    
    private fun loadUserMode() {
        val prefs = getSharedPreferences("auth", Context.MODE_PRIVATE)
        userMode = prefs.getString("user_mode", "manager") ?: "manager"
    }
    
    private fun setupBottomNavigation() {
        bottomNav = findViewById(R.id.bottomNavigation)
        
        // Hide Workers/Sites tabs for managers
        if (userMode == "manager") {
            bottomNav.menu.findItem(R.id.nav_workers).isVisible = false
            bottomNav.menu.findItem(R.id.nav_sites).isVisible = false
        }
        
        bottomNav.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_home -> {
                    loadFragment(HomeFragment())
                    true
                }
                R.id.nav_attendance -> {
                    loadFragment(AttendanceFragment())
                    true
                }
                R.id.nav_workers -> {
                    loadFragment(WorkersFragment())
                    true
                }
                R.id.nav_sites -> {
                    loadFragment(SitesFragment())
                    true
                }
                R.id.nav_profile -> {
                    loadFragment(ProfileFragment())
                    true
                }
                else -> false
            }
        }
    }
    
    private fun loadFragment(fragment: Fragment) {
        supportFragmentManager.beginTransaction()
            .replace(R.id.fragmentContainer, fragment)
            .commit()
    }
    
    private fun navigateToLogin() {
        val intent = Intent(this, LoginActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        startActivity(intent)
        finish()
    }
}