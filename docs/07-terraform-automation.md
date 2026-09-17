# 07 — Terraform Automation

This guide uses Terraform to codify the lab's VirtualBox VMs as infrastructure-as-code, making the entire lab reproducible with a single `terraform apply`.

## Prerequisites

Install Terraform on the host machine:

```bash
# Add HashiCorp GPG key and repo
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
  sudo tee /etc/apt/sources.list.d/hashicorp.list

sudo apt update && sudo apt install -y terraform

terraform --version
```

## VirtualBox Terraform Provider

The `terra-farm/virtualbox` community provider manages VirtualBox VMs. It's not as mature as AWS/Azure providers but demonstrates IaC principles with local infrastructure.

> **Alternative approach:** For a more robust IaC demonstration, you can also use Vagrant with Terraform-like declarative configs, or write Terraform modules that shell out to `VBoxManage`. This guide shows both the provider approach and a scripted approach.

## Project Structure

```
terraform/
├── modules/
│   ├── ubuntu-vm/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── windows-vm/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── environments/
│   └── homelab/
│       ├── main.tf
│       ├── variables.tf
│       ├── terraform.tfvars
│       └── outputs.tf
└── README.md
```

## Ubuntu VM Module

### `terraform/modules/ubuntu-vm/variables.tf`

```hcl
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
```

### `terraform/modules/ubuntu-vm/main.tf`

```hcl
terraform {
  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

# Use null_resource with VBoxManage for reliable VirtualBox control
resource "null_resource" "vm" {
  triggers = {
    vm_name  = var.vm_name
    memory   = var.memory_mb
    cpus     = var.cpus
    disk     = var.disk_size_mb
    ip       = var.static_ip
  }

  provisioner "local-exec" {
    command = <<-EOT
      # Create VM
      VBoxManage createvm --name "${var.vm_name}" --ostype Ubuntu_64 --register

      # Configure resources
      VBoxManage modifyvm "${var.vm_name}" \
        --cpus ${var.cpus} \
        --memory ${var.memory_mb} \
        --vram 16 \
        --nic1 hostonly --hostonlyadapter1 ${var.hostonlyif} \
        --nic2 nat \
        --boot1 dvd --boot2 disk

      # Create disk
      VBoxManage createmedium disk \
        --filename "$HOME/VirtualBox VMs/${var.vm_name}/${var.vm_name}.vdi" \
        --size ${var.disk_size_mb} --variant Standard

      # Attach storage
      VBoxManage storagectl "${var.vm_name}" --name "SATA" --add sata --controller IntelAhci
      VBoxManage storageattach "${var.vm_name}" --storagectl "SATA" --port 0 --device 0 \
        --type hdd --medium "$HOME/VirtualBox VMs/${var.vm_name}/${var.vm_name}.vdi"

      VBoxManage storagectl "${var.vm_name}" --name "IDE" --add ide
      VBoxManage storageattach "${var.vm_name}" --storagectl "IDE" --port 0 --device 0 \
        --type dvddrive --medium "${var.iso_path}"

      echo "VM ${var.vm_name} created. Boot and install OS, then configure IP ${var.static_ip}."
    EOT
  }

  provisioner "local-exec" {
    when    = destroy
    command = <<-EOT
      VBoxManage controlvm "${self.triggers.vm_name}" poweroff 2>/dev/null || true
      sleep 2
      VBoxManage unregistervm "${self.triggers.vm_name}" --delete 2>/dev/null || true
    EOT
  }
}
```

### `terraform/modules/ubuntu-vm/outputs.tf`

```hcl
output "vm_name" {
  value = var.vm_name
}

output "ip_address" {
  value = var.static_ip
}
```

## Homelab Environment

### `terraform/environments/homelab/terraform.tfvars`

```hcl
ubuntu_iso_path = "~/lab-isos/ubuntu-22.04-live-server-amd64.iso"
windows_iso_path = "~/lab-isos/Windows10Enterprise.iso"
```

### `terraform/environments/homelab/main.tf`

```hcl
variable "ubuntu_iso_path" {
  type = string
}

variable "windows_iso_path" {
  type = string
}

module "wazuh_server" {
  source    = "../../modules/ubuntu-vm"
  vm_name   = "wazuh-server"
  cpus      = 2
  memory_mb = 4096
  disk_size_mb = 51200
  static_ip = "192.168.56.10"
  iso_path  = var.ubuntu_iso_path
}

module "keycloak_server" {
  source    = "../../modules/ubuntu-vm"
  vm_name   = "keycloak-server"
  cpus      = 1
  memory_mb = 2048
  disk_size_mb = 20480
  static_ip = "192.168.56.11"
  iso_path  = var.ubuntu_iso_path
}

module "linux_endpoint" {
  source    = "../../modules/ubuntu-vm"
  vm_name   = "linux-endpoint"
  cpus      = 1
  memory_mb = 2048
  disk_size_mb = 30720
  static_ip = "192.168.56.21"
  iso_path  = var.ubuntu_iso_path
}

# Windows VM uses a similar pattern with Windows-specific VBoxManage flags
module "win10_endpoint" {
  source    = "../../modules/ubuntu-vm"  # Reuse with OS type override
  vm_name   = "win10-endpoint"
  cpus      = 2
  memory_mb = 4096
  disk_size_mb = 51200
  static_ip = "192.168.56.20"
  iso_path  = var.windows_iso_path
}
```

### `terraform/environments/homelab/outputs.tf`

```hcl
output "lab_inventory" {
  value = {
    wazuh_server    = module.wazuh_server.ip_address
    keycloak_server = module.keycloak_server.ip_address
    linux_endpoint  = module.linux_endpoint.ip_address
    win10_endpoint  = module.win10_endpoint.ip_address
  }
}
```

## Usage

```bash
cd terraform/environments/homelab

# Initialize
terraform init

# Preview what will be created
terraform plan

# Create all VMs
terraform apply

# Tear down the entire lab
terraform destroy
```

## What This Demonstrates

- Modular Terraform with reusable VM modules
- Environment-specific variable files
- Destroy provisioners for clean teardown
- IaC approach to local infrastructure (transferable to cloud providers)

## Next Step

Proceed to [08 — Python Automation Scripts](08-python-automation.md).
