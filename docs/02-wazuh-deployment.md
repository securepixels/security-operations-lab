# 02 — Wazuh SIEM Deployment

This guide walks through deploying Wazuh as an all-in-one installation (Manager + Indexer + Dashboard) on the `wazuh-server` VM (192.168.56.10).

## Prerequisites

- `wazuh-server` VM running Ubuntu 22.04 (cloned in Guide 01)
- Hostname set to `wazuh-server`, static IP `192.168.56.10`
- Internet access via NAT adapter for package downloads

## Resource Allocation

Ensure the VM has sufficient resources:

```bash
VBoxManage modifyvm "wazuh-server" --memory 4096 --cpus 2
```

Wazuh's Indexer (based on OpenSearch) is memory-intensive. 4 GB is the minimum for an all-in-one deployment.

## Installation

Wazuh provides an automated installer that deploys all components. SSH into the `wazuh-server` VM:

```bash
ssh labadmin@192.168.56.10
```

### Step 1 — Download and Run the Installer

```bash
# Download the Wazuh installer
curl -sO https://packages.wazuh.com/4.9/wazuh-install.sh

# Make it executable
chmod +x wazuh-install.sh

# Run the all-in-one installation
sudo ./wazuh-install.sh -a
```

The `-a` flag installs all components on a single node:
- **Wazuh Manager** — receives and processes agent data, runs detection rules
- **Wazuh Indexer** — stores alerts and logs (OpenSearch-based)
- **Wazuh Dashboard** — web UI for visualization and management

The installer takes 5–10 minutes. At the end, it prints the default admin credentials — **save these**.

> **Note:** The installer version (4.9 above) may change. Check [documentation.wazuh.com](https://documentation.wazuh.com/current/installation-guide/) for the current stable version.

### Step 2 — Verify Services

```bash
# Check all three services are active
sudo systemctl status wazuh-manager
sudo systemctl status wazuh-indexer
sudo systemctl status wazuh-dashboard
```

All three should show `active (running)`.

### Step 3 — Access the Dashboard

From the host machine's browser, navigate to:

```
https://192.168.56.10
```

Accept the self-signed certificate warning and log in with the credentials from the installer output. You should see the Wazuh Dashboard with zero agents enrolled.

### Step 4 — Extract Default Credentials

If you didn't capture the password during installation:

```bash
sudo tar -xvf wazuh-install-files.tar
cat wazuh-install-files/wazuh-passwords.txt
```

### Step 5 — Change Default Passwords

For lab security hygiene, change the admin password:

```bash
# Change the Wazuh Dashboard/Indexer admin password
sudo /usr/share/wazuh-indexer/plugins/opensearch-security/tools/wazuh-passwords-tool.sh \
  -u admin -p 'YourNewSecurePassword123!'
```

Document the new password in a local password manager (not in the repo).

## Post-Install Configuration

### Configure the Manager for the Lab Network

Edit the Wazuh Manager config to listen on the lab subnet:

```bash
sudo nano /var/ossec/etc/ossec.conf
```

Confirm the `<remote>` block allows connections on the lab network:

```xml
<remote>
  <connection>secure</connection>
  <port>1514</port>
  <protocol>tcp</protocol>
</remote>
```

### Enable Key Log Sources

While in `ossec.conf`, verify these log collection blocks are present:

```xml
<!-- Syslog collection -->
<localfile>
  <log_format>syslog</log_format>
  <location>/var/log/syslog</location>
</localfile>

<localfile>
  <log_format>syslog</log_format>
  <location>/var/log/auth.log</location>
</localfile>

<!-- JSON-format logs (for custom app logs) -->
<localfile>
  <log_format>json</log_format>
  <location>/var/log/custom/*.json</location>
</localfile>
```

Restart the manager after any config changes:

```bash
sudo systemctl restart wazuh-manager
```

### Verify the Indexer Health

```bash
# Check cluster health (should be "green" for single-node)
curl -k -u admin:'YourPassword' https://localhost:9200/_cluster/health?pretty
```

### Firewall Rules

Allow agent connections through the firewall:

```bash
sudo ufw allow 1514/tcp   # Agent communication
sudo ufw allow 1515/tcp   # Agent enrollment
sudo ufw allow 443/tcp    # Dashboard HTTPS
sudo ufw allow 9200/tcp   # Indexer API (restrict to lab subnet)
sudo ufw enable
```

## Validate the Deployment

Run these checks to confirm everything is working:

```bash
# Manager is listening for agents
sudo ss -tlnp | grep 1514

# Indexer is accepting queries
curl -k -u admin:'YourPassword' https://localhost:9200/_cat/indices

# Dashboard is accessible
curl -k -o /dev/null -w "%{http_code}" https://localhost:443
# Should return 200 or 302
```

## Snapshot

Take a VirtualBox snapshot before proceeding so you can roll back to a clean Wazuh install:

```bash
VBoxManage snapshot "wazuh-server" take "wazuh-installed-clean" \
  --description "Wazuh 4.9 all-in-one installed, default config, no agents enrolled"
```

## What You've Built

At this point you have:
- A running Wazuh SIEM stack with Manager, Indexer, and Dashboard
- The Manager listening on the lab network for agent enrollment
- A web dashboard accessible at `https://192.168.56.10`
- A snapshot to restore if anything breaks during later configuration

## Next Step

Proceed to [03 — Endpoint Agent Enrollment](03-endpoint-enrollment.md) to install Wazuh agents on the Windows and Linux endpoint VMs.
