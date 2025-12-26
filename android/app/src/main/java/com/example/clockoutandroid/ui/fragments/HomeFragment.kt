package com.example.clockoutandroid.ui.fragments

import android.content.Context
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.example.clockoutandroid.R
import com.example.clockoutandroid.data.remote.RetrofitInstance
import com.google.android.material.bottomnavigation.BottomNavigationView
import kotlinx.coroutines.launch

class HomeFragment : Fragment() {

    private lateinit var tvWelcome: TextView
    private lateinit var tvWorkersCount: TextView
    private lateinit var tvSitesCount: TextView
    private lateinit var tvTodayAttendance: TextView
    private lateinit var btnMarkAttendance: Button

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_home, container, false)
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        initViews(view)
        loadDashboardData()
        setupClickListeners()
    }

    private fun initViews(view: View) {
        tvWelcome = view.findViewById(R.id.tvWelcome)
        tvWorkersCount = view.findViewById(R.id.tvWorkersCount)
        tvSitesCount = view.findViewById(R.id.tvSitesCount)
        tvTodayAttendance = view.findViewById(R.id.tvTodayAttendance)
        btnMarkAttendance = view.findViewById(R.id.btnMarkAttendance)
    }

    private fun loadDashboardData() {
        val sharedPref = requireActivity().getSharedPreferences("auth", Context.MODE_PRIVATE)
        val userName = sharedPref.getString("user_name", "User") ?: "User"
        
        tvWelcome.text = "Welcome back, " + userName
        
        lifecycleScope.launch {
            try {
                val token = sharedPref.getString("token", "") ?: ""
                
                val workersResponse = RetrofitInstance.api.getWorkers("Bearer " + token)
                if (workersResponse.isSuccessful) {
                    val workers = workersResponse.body() ?: emptyList()
                    tvWorkersCount.text = workers.size.toString()
                } else {
                    tvWorkersCount.text = "0"
                }
                
                val sitesResponse = RetrofitInstance.api.getSites("Bearer " + token)
                if (sitesResponse.isSuccessful) {
                    val sites = sitesResponse.body() ?: emptyList()
                    tvSitesCount.text = sites.size.toString()
                } else {
                    tvSitesCount.text = "0"
                }
                
                tvTodayAttendance.text = "0"
                
            } catch (e: Exception) {
                tvWorkersCount.text = "0"
                tvSitesCount.text = "0"
                tvTodayAttendance.text = "0"
            }
        }
    }

    private fun setupClickListeners() {
        btnMarkAttendance.setOnClickListener {
            val bottomNav = activity?.findViewById<BottomNavigationView>(R.id.bottomNavigation)
            bottomNav?.selectedItemId = R.id.nav_attendance
        }
    }
}