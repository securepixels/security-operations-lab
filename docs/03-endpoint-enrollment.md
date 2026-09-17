# 03 — Endpoint Agent Enrollment

This guide covers installing Wazuh agents on both the Windows and Linux endpoint VMs, plus configuring Sysmon on Windows for enhanced telemetry.

## Overview

| Endpoint | OS | IP | What It Simulates |
|---|---|---|---|
| `win10-endpoint` | Windows 10 | 192.168.56.20 | Corporate workstation — EDR monitoring target |
| `linux-endpoint` | Ubuntu 22.04 | 192.168.56.21 | Server/workstation — data scanning and automation host |

Both agents report to the Wazuh Manager at `192.168.56.10`.

## Windows Endpoint Setup

### Create the Windows 10 VM

```bash
VBoxManage createvm --name "win10-endpoint" --ostype Windows10_64 --register

VBoxManage modifyvm "win10-endpoint" \
  --cpus 2 \
  --memory 4096 \
  --vram 128 \
  --nic1 hostonly --hostonlyadapter1 vboxnet0 \
  --nic2 nat \
  --boot1 dvd --boot2 disk

# Create 50 GB disk
VBoxManage createmedium disk \
  --filename ~/VirtualBox\ VMs/win10-endpoint/win10-endpoint.vdi \
  --size 51200 --variant Standard

VBoxManage storagectl "win10-endpoint" --name "SATA" --add sata --controller IntelAhci
VBoxManage storageattach "win10-endpoint" --storagectl "SATA" --port 0 --device 0 \
  --type hdd --medium ~/VirtualBox\ VMs/win10-endpoint/win10-endpoint.vdi

VBoxManage storagectl "win10-endpoint" --name "IDE" --add ide
VBoxManage storageattach "win10-endpoint" --storagectl "IDE" --port 0 --device 0 \
  --type dvddrive --medium ~/lab-isos/Windows10Enterprise.iso
```

Install Windows 10, then set a static IP:
- IP: `192.168.56.20`
- Subnet: `255.255.255.0`
- Gateway: `192.168.56.1`
- DNS: `8.8.8.8` (via NAT adapter for internet)

### Install Sysmon (Enhanced Telemetry)

Sysmon provides detailed process creation, network connection, and file modification logs that standard Windows Event Logs don't capture. This is essential for EDR-style monitoring.

1. Download [Sysmon](https://learn.microsoft.com/en-us/sysinternals/downloads/sysmon) from Sysinternals.

2. Download a community Sysmon config (SwiftOnSecurity's is the standard baseline):

```powershell
# In PowerShell (as Administrator)
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/SwiftOnSecurity/sysmon-config/master/sysmonconfig-export.xml" `
  -OutFile "C:\sysmonconfig.xml"
```

3. Install Sysmon with the config:

```powershell
# Extract Sysmon, then:
.\Sysmon64.exe -accepteula -i C:\sysmonconfig.xml
```

4. Verify Sysmon is running:

```powershell
Get-Service Sysmon64
# Status should be "Running"

# Confirm events are logging
Get-WinEvent -LogName "Microsoft-Windows-Sysmon/Operational" -MaxEvents 5
```

### Install the Wazuh Agent (Windows)

1. Download the Wazuh agent MSI from within the Wazuh Dashboard:
   - Navigate to **Agents → Deploy new agent**
   - Select **Windows** and copy the provided download URL

   Or download directly:

```powershell
Invoke-WebRequest -Uri "https://packages.wazuh.com/4.x/windows/wazuh-agent-4.9.0-1.msi" `
  -OutFile "C:\wazuh-agent.msi"
```

2. Install with the manager IP preconfigured:

```powershell
msiexec /i C:\wazuh-agent.msi /q WAZUH_MANAGER="192.168.56.10" WAZUH_AGENT_NAME="win10-endpoint"
```

3. Start the agent service:

```powershell
NET START Wazuh
```

### Configure Sysmon Log Ingestion

Edit the Wazuh agent config to collect Sysmon events. Open `C:\Program Files (x86)\ossec-agent\ossec.conf` in a text editor (as Administrator) and add:

```xml
<localfile>
  <location>Microsoft-Windows-Sysmon/Operational</location>
  <log_format>eventchannel</log_format>
</localfile>
```

Also ensure standard Windows Security events are collected:

```xml
<localfile>
  <location>Security</location>
  <log_format>eventchannel</log_format>
</localfile>

<localfile>
  <location>System</location>
  <log_format>eventchannel</log_format>
</localfile>

<localfile>
  <location>Microsoft-Windows-PowerShell/Operational</location>
  <log_format>eventchannel</log_format>
</localfile>
```

Restart the agent:

```powershell
NET STOP Wazuh
NET START Wazuh
```

### Enable PowerShell Script Block Logging

This captures the full content of executed PowerShell scripts — critical for detecting encoded commands and fileless attacks:

```powershell
# Enable via Group Policy (Local)
# Computer Configuration → Administrative Templates → Windows Components →
# Windows PowerShell → Turn on PowerShell Script Block Logging → Enabled

# Or via registry:
New-Item -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging" -Force
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging" `
  -Name "EnableScriptBlockLogging" -Value 1
```

## Linux Endpoint Setup

The `linux-endpoint` VM was already cloned from the base template in Guide 01.

### Assign the IP

```bash
# On the linux-endpoint VM
sudo hostnamectl set-hostname linux-endpoint

# Edit netplan config
sudo nano /etc/netplan/01-labnet.yaml
```

Set the static IP:

```yaml
network:
  version: 2
  ethernets:
    enp0s3:
      dhcp4: no
      addresses:
        - 192.168.56.21/24
    enp0s8:
      dhcp4: yes
```

```bash
sudo netplan apply
```

### Install the Wazuh Agent (Linux)

```bash
# Import the Wazuh GPG key
curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | sudo gpg --no-default-keyring \
  --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import && \
  sudo chmod 644 /usr/share/keyrings/wazuh.gpg

# Add the repository
echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" | \
  sudo tee /etc/apt/sources.list.d/wazuh.list

# Install the agent
sudo apt update
sudo WAZUH_MANAGER="192.168.56.10" WAZUH_AGENT_NAME="linux-endpoint" apt install -y wazuh-agent

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable wazuh-agent
sudo systemctl start wazuh-agent
```

### Verify Agent Status

```bash
sudo /var/ossec/bin/wazuh-control status
# All processes should show "running"
```

## Verify Enrollment on the Manager

SSH into the Wazuh server and check enrolled agents:

```bash
ssh labadmin@192.168.56.10

# List enrolled agents
sudo /var/ossec/bin/agent_control -l
```

You should see both `win10-endpoint` and `linux-endpoint` listed as **Active**.

Alternatively, check from the Wazuh Dashboard at `https://192.168.56.10`:
- Navigate to **Agents**
- Both endpoints should appear with a green "Active" status

## Validate Log Flow

### From the Windows Endpoint

Generate a test event on the Windows VM:

```powershell
# Failed login attempt (generates Security Event 4625)
runas /user:fakeuser cmd
# Enter any password when prompted — it will fail
```

### From the Linux Endpoint

```bash
# Failed SSH attempt (generates auth.log entry)
ssh fakeuser@localhost
```

### Confirm on the Dashboard

In the Wazuh Dashboard:
1. Go to **Security Events**
2. Filter by agent name (`win10-endpoint` or `linux-endpoint`)
3. You should see the failed authentication events within 1–2 minutes

## Snapshot

Take snapshots of both endpoints:

```bash
VBoxManage snapshot "win10-endpoint" take "agent-enrolled-sysmon" \
  --description "Wazuh agent installed, Sysmon configured, agent reporting to manager"

VBoxManage snapshot "linux-endpoint" take "agent-enrolled" \
  --description "Wazuh agent installed and reporting to manager"
```

## What You've Built

- Windows endpoint with Wazuh agent, Sysmon, and PowerShell logging — simulates a monitored corporate workstation
- Linux endpoint with Wazuh agent — serves as a server endpoint and future automation/scanning host
- Both agents reporting to the central Wazuh Manager with verified log flow

## Next Step

Proceed to [04 — Keycloak IAM Setup](04-keycloak-setup.md) to deploy the identity provider.
