terraform {
  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}
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
      VBoxManage createvm --name "${var.vm_name}" --ostype Ubuntu_64 --register
      VBoxManage modifyvm "${var.vm_name}" \
        --cpus ${var.cpus} --memory ${var.memory_mb} --vram 16 \
        --nic1 hostonly --hostonlyadapter1 ${var.hostonlyif} \
        --nic2 nat --boot1 dvd --boot2 disk
      VBoxManage createmedium disk \
        --filename "$HOME/VirtualBox VMs/${var.vm_name}/${var.vm_name}.vdi" \
        --size ${var.disk_size_mb} --variant Standard
      VBoxManage storagectl "${var.vm_name}" --name "SATA" --add sata --controller IntelAhci
      VBoxManage storageattach "${var.vm_name}" --storagectl "SATA" --port 0 --device 0 \
        --type hdd --medium "$HOME/VirtualBox VMs/${var.vm_name}/${var.vm_name}.vdi"
      VBoxManage storagectl "${var.vm_name}" --name "IDE" --add ide
      VBoxManage storageattach "${var.vm_name}" --storagectl "IDE" --port 0 --device 0 \
        --type dvddrive --medium "${var.iso_path}"
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
