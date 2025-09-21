resource "google_compute_instance" "vm_instance" {
	project = var.project_id
	name = var.machine_name
	machine_type = var.machine_type
	zone = var.zone
	boot_disk {
		initialize_params {
			image = "centos-stream-9"
		}
		}

	network_interface {
		network = var.network
		subnetwork = var.subnetwork
		access_config {
		}	
	}
	
	tags = ["ssh", "devops-course"]
	
}

resource "google_storage_bucket" "dataops-bucket" {
  name          = var.gcs_bucket_name
  location      = var.location
  force_destroy = true


  public_access_prevention = "enforced"
}



resource "google_bigquery_dataset" "dataops-dataset" {
  dataset_id = var.bq_dataset_name
  location   = var.location
}

