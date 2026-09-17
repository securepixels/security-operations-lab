# 01 — Host & Network Setup

This guide covers preparing the ThinkCentre M920q host machine and configuring VirtualBox networking so all lab VMs can communicate on an isolated subnet.

## Host Preparation

### 1. Verify Hardware

Check available RAM and CPU on the host. Open a terminal:

```bash
# Check CPU cores
nproc --all

# Check total RAM (look for "MemTotal")
grep MemTotal /proc/meminfo

# Check available disk space
df -h /
```

This lab is designed for **16 GB RAM** using a tiered approach: three Tier 1 VMs run at all times (Wazuh, Windows endpoint, Linux endpoint — 10 GB total), and the two Tier 2 VMs (Keycloak, vuln target) swap in one at a time as needed (+2 GB each). See the main README for the full tier breakdown.

> **Storage:** The 256 GB NVMe holds the host OS comfortably, but VM disks total ~170 GB and snapshots add more. Before creating VMs, install a 2.5" SATA SSD (500 GB or larger) in the drive caddy and point VirtualBox's default machine folder there:
>
> **VirtualBox → File → Preferences → General → Default Machine Folder** → set to the SATA drive mount point (e.g., `/mnt/lab-storage` on Linux).
>
> This keeps your boot drive clean and gives snapshots room to grow.

> **If the host runs Windows initially:** Use `systeminfo` in PowerShell to check specs. The VirtualBox setup is the same regardless of host OS — you can build the lab now and migrate the VMs after switching to Linux.

### 2. Install VirtualBox

Download VirtualBox 7.x from [virtualbox.org](https://www.virtualbox.org/wiki/Downloads). Install the Extension Pack for USB 2.0/3.0, disk encryption, and PXE boot support.

**Linux host (Ubuntu/Debian):**

```bash
sudo apt update
sudo apt install -y virtualbox virtualbox-ext-pack
```

**Verify installation:**

```bash
VBoxManage --version
```

### 3. Enable Virtualization in BIOS

The M920q requires Intel VT-x and VT-d enabled in BIOS:

1. Reboot and press **F1** during POST to enter BIOS Setup
2. Navigate to **Security → Virtualization**
3. Enable **Intel Virtualization Technology** and **Intel VT-d Feature**
4. Save and exit

Verify from the host OS:

```bash
# Linux
grep -E 'vmx|svm' /proc/cpuinfo | head -1

# Windows (PowerShell)
Get-ComputerInfo -Property "HyperVisorPresent"
```

## Network Configuration

The lab uses two VirtualBox network types to give VMs both internal connectivity and internet access for package installation.

### Network Design

| Network | Type | Subnet | Purpose |
|---|---|---|---|
| `LabNet` | Host-Only | 192.168.56.0/24 | Inter-VM communication, host access to dashboards |
| NAT | NAT | 10.0.2.0/24 (VBox default) | Outbound internet for updates and downloads |

Each VM gets two network adapters:
- **Adapter 1:** Host-Only (`LabNet`) — static IP, used for all lab traffic
- **Adapter 2:** NAT — DHCP, used only for `apt`/`yum`/Windows Update

### Create the Host-Only Network

```bash
# Create the host-only network
VBoxManage hostonlyif create

# Identify the new interface name (usually vboxnet0)
VBoxManage list hostonlyifs

# Configure it with the lab gateway IP
VBoxManage hostonlyif ipconfig vboxnet0 --ip 192.168.56.1 --netmask 255.255.255.0
```

Disable the built-in DHCP server (we'll use static IPs):

```bash
VBoxManage dhcpserver remove --ifname vboxnet0
```

### Verify Networking

From the host, confirm the interface is up:

```bash
ip addr show vboxnet0
# Should show 192.168.56.1/24
```

## Download ISOs

Store ISOs in a central location on the host:

```bash
mkdir -p ~/lab-isos
```

Download these:

| ISO | Source | Size |
|---|---|---|
| Ubuntu 22.04.x Server | [releases.ubuntu.com/22.04](https://releases.ubuntu.com/22.04/) | ~1.4 GB |
| Windows 10 Enterprise Eval | [Microsoft Eval Center](https://www.microsoft.com/en-us/evalcenter/evaluate-windows-10-enterprise) | ~5 GB |

The Windows evaluation license is valid for 90 days and is free — no Azure or Microsoft billing required.

## Create Base VM Template

Create one Ubuntu Server VM as a template, then clone it for the Wazuh, Keycloak, and Linux endpoint VMs. This saves time and ensures consistency.

### Base Ubuntu VM

```bash
# Create the VM
VBoxManage createvm --name "ubuntu-base" --ostype Ubuntu_64 --register

# Configure resources (adjust for your template)
VBoxManage modifyvm "ubuntu-base" \
  --cpus 2 \
  --memory 2048 \
  --vram 16 \
  --nic1 hostonly --hostonlyadapter1 vboxnet0 \
  --nic2 nat \
  --boot1 dvd --boot2 disk

# Create a 50 GB dynamic disk
VBoxManage createmedium disk \
  --filename ~/VirtualBox\ VMs/ubuntu-base/ubuntu-base.vdi \
  --size 51200 --variant Standard

# Attach the disk
VBoxManage storagectl "ubuntu-base" --name "SATA" --add sata --controller IntelAhci
VBoxManage storageattach "ubuntu-base" --storagectl "SATA" --port 0 --device 0 \
  --type hdd --medium ~/VirtualBox\ VMs/ubuntu-base/ubuntu-base.vdi

# Attach the Ubuntu ISO
VBoxManage storagectl "ubuntu-base" --name "IDE" --add ide
VBoxManage storageattach "ubuntu-base" --storagectl "IDE" --port 0 --device 0 \
  --type dvddrive --medium ~/lab-isos/ubuntu-22.04-live-server-amd64.iso
```

### Install Ubuntu Server

Start the VM and complete the Ubuntu Server install:

```bash
VBoxManage startvm "ubuntu-base"
```

During installation:
- Set hostname to `ubuntu-base`
- Create a user (e.g., `labadmin`)
- Enable OpenSSH server when prompted
- Use defaults for disk partitioning (entire disk, LVM)

After install, remove the ISO and shut down:

```bash
VBoxManage storageattach "ubuntu-base" --storagectl "IDE" --port 0 --device 0 \
  --type dvddrive --medium emptydrive
```

### Post-Install Configuration

SSH into the base VM or use the console. Configure the static IP on the Host-Only adapter and apply baseline hardening:

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install baseline tools
sudo apt install -y net-tools curl wget gnupg apt-transport-https software-properties-common

# Configure static IP for the Host-Only adapter (ens33 or enp0s3 — check with `ip a`)
sudo tee /etc/netplan/01-labnet.yaml << 'EOF'
network:
  version: 2
  ethernets:
    enp0s3:
      dhcp4: no
      addresses:
        - 192.168.56.100/24  # Placeholder — clones will change this
    enp0s8:
      dhcp4: yes             # NAT adapter for internet
EOF

sudo netplan apply
```

### Clone for Lab VMs

Shut down the base VM, then create linked clones for each server:

```bash
# Shut down cleanly
VBoxManage controlvm "ubuntu-base" acpipowerbutton

# Clone for Wazuh (full clone for the primary server)
VBoxManage clonevm "ubuntu-base" --name "wazuh-server" --register --mode machine

# Clone for Keycloak
VBoxManage clonevm "ubuntu-base" --name "keycloak-server" --register --mode machine

# Clone for Linux endpoint
VBoxManage clonevm "ubuntu-base" --name "linux-endpoint" --register --mode machine
```

After cloning, set each VM's resources per the tiered layout:

```bash
# Tier 1 — always running
VBoxManage modifyvm "wazuh-server"    --memory 4096 --cpus 2   # 4 GB
VBoxManage modifyvm "linux-endpoint"  --memory 2048 --cpus 1   # 2 GB

# Tier 2 — swap in as needed (don't run both at once)
VBoxManage modifyvm "keycloak-server" --memory 2048 --cpus 1   # 2 GB
```

> **16 GB RAM note:** Tier 1 uses 10 GB (Wazuh 4 + Windows 4 + Linux 2), leaving ~3 GB for the host. Boot one Tier 2 VM at a time by shutting the other down first. Use `VBoxManage snapshot` to save/restore state so you don't lose work.

Then boot each clone, update its hostname and static IP:

```bash
# On the wazuh-server clone:
sudo hostnamectl set-hostname wazuh-server
# Edit /etc/netplan/01-labnet.yaml → change address to 192.168.56.10/24
sudo netplan apply
```

Repeat for each VM using the IPs from the main README.

## Connectivity Test

Once all VMs are booted with their assigned IPs, verify from the host:

```bash
ping -c 2 192.168.56.10   # wazuh-server
ping -c 2 192.168.56.11   # keycloak-server
ping -c 2 192.168.56.20   # win10-endpoint
ping -c 2 192.168.56.21   # linux-endpoint
```

And from any VM, confirm internet access through the NAT adapter:

```bash
curl -s -o /dev/null -w "%{http_code}" https://google.com
# Should return 200
```

## Next Step

Proceed to [02 — Wazuh SIEM Deployment](02-wazuh-deployment.md) to install the Wazuh all-in-one stack on the `wazuh-server` VM.
