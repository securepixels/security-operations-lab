# 11 — Active Directory Lab

This guide deploys a Windows Server domain controller on the lab network, creates an AD domain, joins the Windows 10 endpoint to it, and configures Group Policy Objects for security hardening — all skills that map directly to enterprise IAM and SC-500 objectives.

## Why AD Matters for Your Resume

Active Directory is still the backbone of identity management at most organizations. Even companies using Entra ID or Okta typically have a hybrid AD environment. Demonstrating that you can stand up a domain, manage GPOs, and monitor AD security events with a SIEM covers a gap that certifications alone don't fill.

## Prerequisites

- Lab network running (Guide 01)
- Wazuh Server operational (Guide 02)
- Windows 10 endpoint enrolled (Guide 03)
- Download [Windows Server 2022 Evaluation](https://www.microsoft.com/en-us/evalcenter/evaluate-windows-server-2022) ISO (~5 GB, 180-day trial, free, no Azure billing)

## Create the Domain Controller VM

This is a Tier 2 VM — shut down Keycloak or the vuln target before booting it.

```bash
VBoxManage createvm --name "ad-dc" --ostype Windows2022_64 --register

VBoxManage modifyvm "ad-dc" \
  --cpus 2 \
  --memory 2048 \
  --vram 128 \
  --nic1 hostonly --hostonlyadapter1 vboxnet0 \
  --nic2 nat \
  --boot1 dvd --boot2 disk

VBoxManage createmedium disk \
  --filename ~/VirtualBox\ VMs/ad-dc/ad-dc.vdi \
  --size 40960 --variant Standard

VBoxManage storagectl "ad-dc" --name "SATA" --add sata --controller IntelAhci
VBoxManage storageattach "ad-dc" --storagectl "SATA" --port 0 --device 0 \
  --type hdd --medium ~/VirtualBox\ VMs/ad-dc/ad-dc.vdi

VBoxManage storagectl "ad-dc" --name "IDE" --add ide
VBoxManage storageattach "ad-dc" --storagectl "IDE" --port 0 --device 0 \
  --type dvddrive --medium ~/lab-isos/WindowsServer2022.iso
```

Install Windows Server 2022 (Desktop Experience). After installation:

- Set static IP: `192.168.56.12`
- Subnet: `255.255.255.0`
- DNS: `127.0.0.1` (itself, once AD DNS is installed)
- Set hostname: `ad-dc`

## Install Active Directory Domain Services

Open PowerShell as Administrator:

```powershell
# Install AD DS and DNS roles
Install-WindowsFeature AD-Domain-Services -IncludeManagementTools
Install-WindowsFeature DNS -IncludeManagementTools

# Promote to domain controller
# This creates a new forest — lab.local is the domain name
Install-ADDSForest `
  -DomainName "lab.local" `
  -DomainNetBIOSName "LAB" `
  -InstallDns:$true `
  -SafeModeAdministratorPassword (ConvertTo-SecureString "DsrmP@ss2024!" -AsPlainText -Force) `
  -Force:$true
```

The server reboots automatically. After reboot, log in as `LAB\Administrator`.

### Verify AD DS

```powershell
# Confirm domain services are running
Get-Service NTDS, DNS, Kdc

# Confirm the domain exists
Get-ADDomain

# Confirm DNS zone
Get-DnsServerZone
```

## Create Organizational Units and Users

Build a realistic OU structure that mirrors an enterprise environment:

```powershell
# Create OUs
New-ADOrganizationalUnit -Name "Security" -Path "DC=lab,DC=local"
New-ADOrganizationalUnit -Name "IT" -Path "DC=lab,DC=local"
New-ADOrganizationalUnit -Name "Users" -Path "OU=Security,DC=lab,DC=local"
New-ADOrganizationalUnit -Name "Service Accounts" -Path "OU=IT,DC=lab,DC=local"
New-ADOrganizationalUnit -Name "Workstations" -Path "DC=lab,DC=local"

# Create security team users
$securityUsers = @(
    @{Name="SOC Analyst T1"; SamAccountName="soc.t1"; Title="SOC Analyst - Tier 1"},
    @{Name="SOC Analyst T2"; SamAccountName="soc.t2"; Title="SOC Analyst - Tier 2"},
    @{Name="Security Engineer"; SamAccountName="sec.engineer"; Title="Security Engineer"},
    @{Name="IAM Admin"; SamAccountName="iam.admin"; Title="IAM Administrator"}
)

foreach ($user in $securityUsers) {
    New-ADUser `
      -Name $user.Name `
      -SamAccountName $user.SamAccountName `
      -UserPrincipalName "$($user.SamAccountName)@lab.local" `
      -Title $user.Title `
      -Path "OU=Users,OU=Security,DC=lab,DC=local" `
      -AccountPassword (ConvertTo-SecureString "TempP@ss123!" -AsPlainText -Force) `
      -ChangePasswordAtLogon $true `
      -Enabled $true
}

# Create security groups for RBAC
New-ADGroup -Name "SOC-Tier1" -GroupScope Global -Path "OU=Security,DC=lab,DC=local"
New-ADGroup -Name "SOC-Tier2" -GroupScope Global -Path "OU=Security,DC=lab,DC=local"
New-ADGroup -Name "SecurityEngineers" -GroupScope Global -Path "OU=Security,DC=lab,DC=local"
New-ADGroup -Name "IAMAdmins" -GroupScope Global -Path "OU=Security,DC=lab,DC=local"

# Add users to groups
Add-ADGroupMember -Identity "SOC-Tier1" -Members "soc.t1"
Add-ADGroupMember -Identity "SOC-Tier2" -Members "soc.t2"
Add-ADGroupMember -Identity "SecurityEngineers" -Members "sec.engineer"
Add-ADGroupMember -Identity "IAMAdmins" -Members "iam.admin"
```

## Join the Windows 10 Endpoint to the Domain

On the `win10-endpoint` VM, first point DNS to the domain controller:

```powershell
# Set DNS to the DC
Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -ServerAddresses 192.168.56.12

# Test DNS resolution
Resolve-DnsName lab.local

# Join the domain
Add-Computer -DomainName "lab.local" -Credential LAB\Administrator -Restart -Force
```

After reboot, you can log in as any domain user (e.g., `LAB\soc.t1`).

## Configure Security-Relevant GPOs

### GPO 1 — Audit Policy (Event Logging)

This GPO enables the detailed Windows Security event logging that Wazuh needs:

```powershell
# Create the GPO
New-GPO -Name "Security Audit Policy" | New-GPLink -Target "DC=lab,DC=local"

# Configure audit policies via the GPO
# (Run from Group Policy Management or use AuditPol on each machine)

# On the DC or domain-joined workstation:
AuditPol /set /category:"Logon/Logoff" /success:enable /failure:enable
AuditPol /set /category:"Account Logon" /success:enable /failure:enable
AuditPol /set /category:"Account Management" /success:enable /failure:enable
AuditPol /set /category:"Privilege Use" /success:enable /failure:enable
AuditPol /set /category:"Object Access" /success:enable /failure:enable
```

### GPO 2 — Password Policy

```powershell
# Set domain password policy
Set-ADDefaultDomainPasswordPolicy -Identity lab.local `
  -MinPasswordLength 12 `
  -MaxPasswordAge (New-TimeSpan -Days 90) `
  -PasswordHistoryCount 12 `
  -ComplexityEnabled $true `
  -LockoutThreshold 5 `
  -LockoutDuration (New-TimeSpan -Minutes 30) `
  -LockoutObservationWindow (New-TimeSpan -Minutes 30)
```

### GPO 3 — Restrict Local Admin

```powershell
# Create a GPO to remove users from local Administrators on workstations
# This is best done via Group Policy Management Console (GPMC):
# Computer Configuration → Policies → Windows Settings → Security Settings →
# Restricted Groups → Add "Administrators" → Members: only Domain Admins
```

## Install Wazuh Agent on the Domain Controller

The DC generates critical security events — monitor it with Wazuh:

```powershell
# Download and install the Wazuh agent
Invoke-WebRequest -Uri "https://packages.wazuh.com/4.x/windows/wazuh-agent-4.9.0-1.msi" `
  -OutFile "C:\wazuh-agent.msi"

msiexec /i C:\wazuh-agent.msi /q WAZUH_MANAGER="192.168.56.10" WAZUH_AGENT_NAME="ad-dc"

NET START Wazuh
```

Add AD-specific event channels to `C:\Program Files (x86)\ossec-agent\ossec.conf`:

```xml
<localfile>
  <location>Security</location>
  <log_format>eventchannel</log_format>
</localfile>

<localfile>
  <location>Microsoft-Windows-Sysmon/Operational</location>
  <log_format>eventchannel</log_format>
</localfile>

<localfile>
  <location>Directory Service</location>
  <log_format>eventchannel</log_format>
</localfile>

<localfile>
  <location>Microsoft-Windows-PowerShell/Operational</location>
  <log_format>eventchannel</log_format>
</localfile>
```

Restart the agent to apply.

## AD Detection Rules for Wazuh

Add these to your `local_rules.xml` on the Wazuh Manager:

```xml
<!-- AD: Account lockout (Event 4740) -->
<group name="local,active_directory">
  <rule id="100060" level="10">
    <if_sid>60106</if_sid>
    <field name="win.system.eventID">4740</field>
    <description>AD account locked out — possible brute force against domain account</description>
    <mitre>
      <id>T1110</id>
    </mitre>
    <group>ad,account_lockout</group>
  </rule>

  <!-- AD: User added to privileged group (Event 4728/4732/4756) -->
  <rule id="100061" level="12">
    <if_sid>60106</if_sid>
    <field name="win.system.eventID">4728|4732|4756</field>
    <match>Domain Admins|Enterprise Admins|Schema Admins|Administrators</match>
    <description>User added to privileged AD group — review immediately</description>
    <mitre>
      <id>T1098</id>
    </mitre>
    <group>ad,privilege_escalation</group>
  </rule>

  <!-- AD: GPO modified (Event 5136) -->
  <rule id="100062" level="10">
    <if_sid>60106</if_sid>
    <field name="win.system.eventID">5136</field>
    <description>Group Policy Object modified — verify authorized change</description>
    <mitre>
      <id>T1484.001</id>
    </mitre>
    <group>ad,gpo_change</group>
  </rule>
</group>
```

## Portfolio Exercises

Document these as writeups with screenshots for your GitHub:

### Exercise 1 — Onboarding and Least Privilege
Create a new analyst account, assign to SOC-Tier1, domain-join a workstation, verify they can read but not modify Wazuh dashboards. Screenshot the access review.

### Exercise 2 — Privilege Escalation Detection
Add `soc.t1` to Domain Admins, observe the Wazuh alert fire (rule 100061), investigate the event, remove the user, document the incident response.

### Exercise 3 — Account Lockout Investigation
Trigger 5+ failed logins against a domain account, observe the lockout event in Wazuh, trace the source IP, document the triage workflow.

### Exercise 4 — GPO Hardening Audit
Run `gpresult /R` on the domain-joined workstation, compare applied policies against CIS Windows 10 Benchmark, document gaps and remediation.

## Snapshot

```bash
VBoxManage snapshot "ad-dc" take "ad-configured" \
  --description "AD DS installed, lab.local domain, users/groups/GPOs configured, Wazuh agent enrolled"
```

## Next Step

Proceed to [12 — Okta Developer Integration](12-okta-integration.md) to set up a cloud identity provider alongside your local AD.
