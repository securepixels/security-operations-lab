variable "vm_name" {
  description = "Name of the VirtualBox VM"
  type        = string
}
variable "cpus" {
  description = "Number of CPU cores"
  type        = number
  default     = 2
}
variable "memory_mb" {
  description = "RAM in megabytes"
  type        = number
  default     = 2048
}
variable "disk_size_mb" {
  description = "Disk size in megabytes"
  type        = number
  default     = 51200
}
variable "static_ip" {
  description = "Static IP on the host-only network"
  type        = string
}
variable "hostonlyif" {
  description = "Host-only interface name"
  type        = string
  default     = "vboxnet0"
}
variable "iso_path" {
  description = "Path to the Ubuntu ISO for initial boot"
  type        = string
}
