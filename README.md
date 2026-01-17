<div align="center">

# Slurm Lightsail Cluster

[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Platform](https://img.shields.io/badge/platform-AWS%20Lightsail-orange.svg)](https://aws.amazon.com/lightsail/)
[![Ansible](https://img.shields.io/badge/ansible-automated-red.svg)](https://www.ansible.com/)
[![Slurm](https://img.shields.io/badge/scheduler-SLURM-blue.svg)](https://slurm.schedmd.com/)

**High-Performance Computing (HPC) cluster deployment on AWS Lightsail.**
<br>
Utilizes SLURM for centralized job scheduling and NFS for shared storage across a Head Node and multiple Worker Nodes.

[Demo](#demo) • [Infrastructure](#infrastructure-overview) • [Ansible Automation](#option-1-ansible-automation-recommended) • [Manual Setup](#option-3-manual-configuration)

</div>

---

## Overview
The repository provides a comprehensive Ansible playbook to fully automate the setup, handling Munge authentication, DNS configuration, and service orchestration to enable secure, synchronized communication over private internal networking.

## Demo
Demonstration of slurm commands, NFS shared storage, and running a python script on the cluster.

<div align="center">
  <img width="982" height="605" alt="Cluster Demo" src="https://github.com/user-attachments/assets/310ff299-7ae3-42ee-9289-daeccd097724" />
</div>

> **Watch the full recording:** [View Demo Video](https://github.com/user-attachments/assets/423419ec-421d-4a34-8db0-ea8ac98f3a0d)

---

## Setup Guide

### Infrastructure Overview
*   **Head Node:** `ubuntu-1`
*   **Worker Nodes:** `ubuntu-2`, `ubuntu-3`, `ubuntu-4`...
*   **OS:** Ubuntu 22.04 LTS

### AWS Firewall (Networking)
Navigate to the **Lightsail Console > Networking** for **ALL INSTANCES**. Add the following IPv4 Firewall rules.

> [!IMPORTANT]
> **Static IPs Required**
> Ensure you attach Static IPs to each node instance so that the addresses do not change upon reboot.

| Protocol | Port Range | Purpose |
| :--- | :--- | :--- |
| **TCP** | `22` | SSH (PuTTY/Ansible) |
| **TCP** | `6817 - 6818` | Slurm Controller |
| **TCP** | `60001 - 60009` | Slurm Data (`srun`) |
| **TCP** | `2049` | NFS Storage |
| **TCP** | `111` | NFS RPC |
| **UDP** | `111` | NFS RPC |

---

## Option 1: Ansible Automation (Recommended)
This method is fully automated, idempotent, and scalable. It handles SSH keys, NFS mounting, and Slurm configuration automatically. It configures the cluster to communicate over **Private IPs** for maximum speed and security.

**Prerequisites:**
*   You must run this from a Linux environment. **Windows users must use WSL (Ubuntu).**
*   You need your AWS `.pem` private key file.

### 1. Setup Environment
Install Ansible and set up your SSH key permissions:
```bash
sudo apt update && sudo apt install ansible -y
mkdir -p ~/.ssh
cp /path/to/your-key.pem ~/.ssh/id_rsa_aws.pem
chmod 400 ~/.ssh/id_rsa_aws.pem
```

### 2. Configure Inventory
Navigate to the `ansible/` folder. Edit `hosts.ini` with your specific IPs.
*   `ansible_host`: The **Public IP** (How Ansible connects).
*   `private_ip`: The **Private IP** (How Slurm nodes talk to each other).

```ini
[head]
ubuntu-1 ansible_host=X.X.X.X private_ip=172.26.x.x

[workers]
ubuntu-2 ansible_host=Y.Y.Y.Y private_ip=172.26.y.y
ubuntu-3 ansible_host=Z.Z.Z.Z private_ip=172.26.z.z
# Additional workers can be added here
```

### 3. Run the Playbook
Execute the deployment to install dependencies, create users, mount storage, and start the cluster.

```bash
ansible-playbook -i hosts.ini site.yml
```

> [!NOTE]
> If the playbook pauses at "Escalation Succeeded" for a long time, the nodes are likely installing automatic Ubuntu security updates. Wait 10-15 minutes and it will proceed.

---

## Option 2: Shell Scripts (Legacy)
Download the shell scripts in this repository.

1.  Modify `0_config.sh` so that the `IP_HEAD` and `IP_WORKER` variables match your **Public IPs**.
2.  Copy these shell scripts to **every** node.

### Execution Steps

**1. On Ubuntu-1 (Head Node):**
```bash
chmod +x 0_config.sh setup_head.sh
./setup_head.sh
```
*(Copy the key block printed at the end of the script).*

**2. On Ubuntu-2 (Worker 1):**
```bash
chmod +x 0_config.sh setup_worker.sh
./setup_worker.sh 2
```
*(Paste the key when prompted).*

**3. On Ubuntu-3 (Worker 2):**
```bash
chmod +x 0_config.sh setup_worker.sh
./setup_worker.sh 3
```
*(Paste the key when prompted).*

---

## Option 3: Manual Configuration

### Step 1: System Prep & Auth

**Set Hostnames** (Run on respective nodes):
```bash
sudo hostnamectl set-hostname ubuntu-1  # On Head Node
sudo hostnamectl set-hostname ubuntu-2  # On Worker 1
sudo hostnamectl set-hostname ubuntu-3  # On Worker 2
```

**Configure DNS** (Run on ALL Nodes):
Edit `/etc/hosts`. Delete the line starting with `127.0.1.1` and add the following at the bottom (Use real Public IPs):
```text
X.X.X.X ubuntu-1
Y.Y.Y.Y ubuntu-2
Z.Z.Z.Z ubuntu-3
```

**SSH Passwordless Auth:**
1.  **On Head Node:** Run `ssh-keygen -t rsa`, press Enter for all prompts, and copy the content of `~/.ssh/id_rsa.pub`.
2.  **On Workers:** Paste the key into `~/.ssh/authorized_keys`.

### Step 2: NFS Shared Storage

**Setup Server (Head Node):**
```bash
sudo apt update && sudo apt install nfs-kernel-server -y
mkdir -p /home/ubuntu/cluster_share
sudo chown ubuntu:ubuntu /home/ubuntu/cluster_share
sudo chmod 777 /home/ubuntu/cluster_share

# Configure Exports
echo "/home/ubuntu/cluster_share ubuntu-2(rw,sync,no_subtree_check) ubuntu-3(rw,sync,no_subtree_check)" | sudo tee -a /etc/exports
sudo exportfs -ra
sudo systemctl restart nfs-kernel-server
```

**Setup Clients (Workers):**
```bash
sudo apt update && sudo apt install nfs-common -y
mkdir -p /home/ubuntu/cluster_share

# Mount (Run once)
sudo mount ubuntu-1:/home/ubuntu/cluster_share /home/ubuntu/cluster_share

# Make Permanent (Add to /etc/fstab)
echo "ubuntu-1:/home/ubuntu/cluster_share /home/ubuntu/cluster_share nfs defaults 0 0" | sudo tee -a /etc/fstab
```

### Step 3: SLURM Installation

**1. Install Software (Run on ALL Nodes):**
```bash
sudo add-apt-repository universe -y
sudo apt update
sudo apt install munge slurm-wlm -y
```

**2. Munge Authentication:**
*   **On Head Node:** Create the key.
    ```bash
    sudo /usr/sbin/create-munge-key -r
    sudo cat /etc/munge/munge.key | base64
    ```
*   **On Workers:** Decode and save the key (Paste the output from Head Node).
    ```bash
    echo "PASTED_TEXT_BLOCK" | base64 -d | sudo tee /etc/munge/munge.key
    ```
*   **On ALL Nodes:** Set permissions.
    ```bash
    sudo chown munge:munge /etc/munge/munge.key
    sudo chmod 400 /etc/munge/munge.key
    sudo systemctl restart munge
    ```

**3. Configure SLURM (Run on ALL Nodes):**
Edit `/etc/slurm/slurm.conf` and paste this exact config:
```text
ClusterName=mycluster
SlurmctldHost=ubuntu-1
MpiDefault=none
ProctrackType=proctrack/pgid
ReturnToService=1
SlurmctldPidFile=/var/run/slurmctld.pid
SlurmdPidFile=/var/run/slurmd.pid
SlurmdSpoolDir=/var/lib/slurm/slurmd
SlurmUser=root
StateSaveLocation=/var/lib/slurm/slurmctld
SwitchType=switch/none
TaskPlugin=task/none

# TIMERS & PORTS
SlurmctldTimeout=300
SlurmdTimeout=300
SrunPortRange=60001-60009

# SCHEDULER
SchedulerType=sched/backfill
SelectType=select/cons_res
SelectTypeParameters=CR_Core

# LOGGING
SlurmctldDebug=3
SlurmctldLogFile=/var/log/slurm/slurmctld.log
SlurmdDebug=3
SlurmdLogFile=/var/log/slurm/slurmd.log

# NODES & PARTITIONS
NodeName=ubuntu-1 CPUs=2 RealMemory=400 State=UNKNOWN
NodeName=ubuntu-2 CPUs=2 RealMemory=400 State=UNKNOWN
NodeName=ubuntu-3 CPUs=2 RealMemory=400 State=UNKNOWN
PartitionName=debug Nodes=ubuntu-[1-3] Default=YES MaxTime=INFINITE State=UP
```

**4. Create Log Dirs & Start (Run on ALL Nodes):**
```bash
sudo mkdir -p /var/log/slurm
sudo chown slurm:slurm /var/log/slurm
sudo systemctl restart slurmd
```
*(On Head Node Only: `sudo systemctl restart slurmctld`)*

**5. Verification:**
On Head Node, run:
```bash
srun -N3 hostname
```
