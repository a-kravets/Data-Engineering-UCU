
terraform {
   backend "gcs" {
     bucket = "dev-dataops-ucu-terraform-state-bucket-20250921"
     prefix = "terraform/state"
   }
}