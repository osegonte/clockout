package com.example.clockoutandroid.ui.adapters

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageButton
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.clockoutandroid.R
import com.example.clockoutandroid.data.models.Site

class SiteAdapter(
    private val onEditClick: (Site) -> Unit,
    private val onDeleteClick: (Site) -> Unit
) : ListAdapter<Site, SiteAdapter.SiteViewHolder>(SiteDiffCallback()) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): SiteViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_site, parent, false)
        return SiteViewHolder(view)
    }

    override fun onBindViewHolder(holder: SiteViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    inner class SiteViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val tvSiteName: TextView = itemView.findViewById(R.id.tvSiteName)
        private val tvSiteCoordinates: TextView = itemView.findViewById(R.id.tvSiteCoordinates)
        private val tvSiteRadius: TextView = itemView.findViewById(R.id.tvSiteRadius)
        private val btnEdit: ImageButton = itemView.findViewById(R.id.btnEditSite)
        private val btnDelete: ImageButton = itemView.findViewById(R.id.btnDeleteSite)

        fun bind(site: Site) {
            tvSiteName.text = site.name
            
            val coordinates = "📍 " + String.format("%.6f", site.latitude) + ", " + String.format("%.6f", site.longitude)
            tvSiteCoordinates.text = coordinates
            
            val radiusText = "Radius: " + site.radius.toInt() + "m"
            tvSiteRadius.text = radiusText
            
            btnEdit.setOnClickListener { onEditClick(site) }
            btnDelete.setOnClickListener { onDeleteClick(site) }
        }
    }

    class SiteDiffCallback : DiffUtil.ItemCallback<Site>() {
        override fun areItemsTheSame(oldItem: Site, newItem: Site): Boolean {
            return oldItem.id == newItem.id
        }

        override fun areContentsTheSame(oldItem: Site, newItem: Site): Boolean {
            return oldItem == newItem
        }
    }
}