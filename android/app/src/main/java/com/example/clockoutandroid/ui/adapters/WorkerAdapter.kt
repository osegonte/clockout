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
import com.example.clockoutandroid.data.models.Worker

class WorkerAdapter(
    private val onEditClick: (Worker) -> Unit,
    private val onDeleteClick: (Worker) -> Unit
) : ListAdapter<Worker, WorkerAdapter.WorkerViewHolder>(WorkerDiffCallback()) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): WorkerViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_worker, parent, false)
        return WorkerViewHolder(view)
    }

    override fun onBindViewHolder(holder: WorkerViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    inner class WorkerViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val tvWorkerName: TextView = itemView.findViewById(R.id.tvWorkerName)
        private val tvWorkerPhone: TextView = itemView.findViewById(R.id.tvWorkerPhone)
        private val tvWorkerEmployeeId: TextView = itemView.findViewById(R.id.tvWorkerEmployeeId)
        private val tvWorkerStatus: TextView = itemView.findViewById(R.id.tvWorkerStatus)
        private val btnEdit: ImageButton = itemView.findViewById(R.id.btnEditWorker)
        private val btnDelete: ImageButton = itemView.findViewById(R.id.btnDeleteWorker)

        fun bind(worker: Worker) {
            tvWorkerName.text = worker.name
            
            val phoneText = if (worker.phone.isNullOrEmpty()) {
                "No phone"
            } else {
                "📱 " + worker.phone
            }
            tvWorkerPhone.text = phoneText
            
            val employeeIdText = if (worker.employeeId.isNullOrEmpty()) {
                "No ID"
            } else {
                "ID: " + worker.employeeId
            }
            tvWorkerEmployeeId.text = employeeIdText
            
            val statusText = if (worker.isActive) "Active" else "Inactive"
            tvWorkerStatus.text = statusText
            
            btnEdit.setOnClickListener { onEditClick(worker) }
            btnDelete.setOnClickListener { onDeleteClick(worker) }
        }
    }

    class WorkerDiffCallback : DiffUtil.ItemCallback<Worker>() {
        override fun areItemsTheSame(oldItem: Worker, newItem: Worker): Boolean {
            return oldItem.id == newItem.id
        }

        override fun areContentsTheSame(oldItem: Worker, newItem: Worker): Boolean {
            return oldItem == newItem
        }
    }
}