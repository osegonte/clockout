package com.example.clockoutandroid

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.Fragment
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.example.clockoutandroid.ui.fragments.AttendanceFragment
import com.example.clockoutandroid.ui.fragments.HomeFragment
import com.example.clockoutandroid.ui.fragments.ProfileFragment
import com.example.clockoutandroid.ui.fragments.SitesFragment
import com.example.clockoutandroid.ui.fragments.WorkersFragment

class MainActivity : AppCompatActivity() {
    
    private lateinit var bottomNav: BottomNavigationView
    private var userMode: String = "manager"
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        if (!isLoggedIn()) {
            navigateToLogin()
            return
        }
        
        loadUserMode()
        
        setContentView(R.layout.activity_main_container)
        
        setupBottomNavigation()
        
        if (savedInstanceState == null) {
            loadFragment(HomeFragment())
        }
    }
    
    private fun isLoggedIn(): Boolean {
        val prefs = getSharedPreferences("auth", Context.MODE_PRIVATE)
        val token = prefs.getString("token", null)
        val loginTime = prefs.getLong("login_time", 0)
        
        val tokenValid = token != null && (System.currentTimeMillis() - loginTime) < 7 * 24 * 60 * 60 * 1000
        
        return tokenValid
    }
    
    private fun loadUserMode() {
        val prefs = getSharedPreferences("auth", Context.MODE_PRIVATE)
        userMode = prefs.getString("user_mode", "manager") ?: "manager"
    }
    
    private fun setupBottomNavigation() {
        bottomNav = findViewById(R.id.bottomNavigation)
        
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