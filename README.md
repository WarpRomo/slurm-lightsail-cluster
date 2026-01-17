# Slurm Lightsail Cluster
This project deploys a High-Performance Computing (HPC) cluster on AWS Lightsail, utilizing SLURM for centralized job scheduling and NFS for shared storage across a Head Node and multiple Worker Nodes. The repository provides a comprehensive Ansible playbook to fully automate the setup, handling Munge authentication, DNS configuration, and service orchestration to enable secure, synchronized communication over private internal networking.

# Demo
Demonstration of slurm commands, NFS shared storage, and running python script on the cluster.

<img width="982" height="605" alt="image" src="https://github.com/user-attachments/assets/310ff299-7ae3-42ee-9289-daeccd097724" />

https://github.com/user-attachments/assets/423419ec-421d-4a34-8db0-ea8ac98f3a0d

# Setup Guide
## Infrastructure Overview
*   **Head Node:** `ubuntu-1`
*   **Worker Nodes:** `ubuntu-2`, `ubuntu-3`, `ubuntu-4`...
*   **OS:** Ubuntu 22.04 LTS

### Step 1: AWS Firewall (Networking)
Go to the **Lightsail Console > Networking** for **ALL INSTANCES**. Add these IPv4 Firewall rules.
**Make sure to attach Static IPs to each node instance so that the addresses don't change.**

| Protocol | Port Range | Purpose |
| :--- | :--- | :--- |
| **TCP** | `22` | SSH (PuTTY/Ansible) |
| **TCP** | `6817 - 6818` | Slurm Controller |
| **TCP** | `60001 - 60009` | Slurm Data (`srun`) |
| **TCP** | `2049` | NFS Storage |
| **TCP** | `111` | NFS RPC |
| **UDP** | `111` | NFS RPC 

---

## Option 1: Ansible Automation (Recommended)
This method is fully automated, idempotent, and scalable. It handles SSH keys, NFS mounting, and Slurm configuration automatically. It configures the cluster to communicate over **Private IPs** for maximum speed and security.

**Prerequisites:**
*   You must run this from a Linux environment. **Windows users must use WSL (Ubuntu).**
*   You need your AWS `.pem` private key file.

### 1. Setup Environment (WSL/Linux)
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
# You can add more workers here easily!
```

### 3. Run the Playbook
Run the deployment. This will install dependencies, create users, mount storage, and start the cluster.
```bash
ansible-playbook -i hosts.ini site.yml
```
*Note: If the playbook pauses at "Escalation Succeeded" for a long time, the nodes are likely installing automatic Ubuntu security updates. Wait 10-15 minutes and it will proceed.*

---

## Option 2: Shell Scripts (Legacy)
Download the shell scripts in this repository. 

1.  Modify `0_config.sh` so that the `IP_HEAD` and `IP_WORKER` variables match your **Public IPs**.
2.  Copy these shell scripts to **every** node.

### How to Run

1.  **On Ubuntu-1 (Head):**
    ```bash
    chmod +x 0_config.sh setup_head.sh
    ./setup_head.sh
    ```
    *(At the end, copy the big block of random text it prints).*

2.  **On Ubuntu-2:**
    ```bash
    chmod +x 0_config.sh setup_worker.sh
    ./setup_worker.sh 2
    ```
    *(Paste the key when asked).*

3.  **On Ubuntu-3:**
    ```bash
    chmod +x 0_config.sh setup_worker.sh
    ./setup_worker.sh 3
    ```
    *(Paste the key when asked).*

---

## Option 3: Manual Configuration

### Step 2: System Prep & Auth
**1. Set Hostnames (Run on respective nodes):**
```bash
sudo hostnamectl set-hostname ubuntu-1  # On Head Node
sudo hostnamectl set-hostname ubuntu-2  # On Worker 1
sudo hostnamectl set-hostname ubuntu-3  # On Worker 2
```

**2. Configure DNS (Run on ALL Nodes):**
`sudo nano /etc/hosts`
*   **Delete** the line starting with `127.0.1.1`.
*   **Add** these lines at the bottom (Use real Public IPs):
    ```text
    X.X.X.X ubuntu-1
    Y.Y.Y.Y ubuntu-2
    Z.Z.Z.Z ubuntu-3
    ```

**3. SSH Passwordless Auth:**
*   **On Head Node:**
    ```bash
    ssh-keygen -t rsa  # Press Enter for all prompts
    cat ~/.ssh/id_rsa.pub
    ```
    *(Copy the output).*
*   **On Workers (`ubuntu-2` & `3`):**
    `nano ~/.ssh/authorized_keys` -> Paste the key at the bottom.

---

### Step 3: NFS Shared Storage
**1. Setup Server (Head Node):**
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

**2. Setup Clients (Workers):**
```bash
sudo apt update && sudo apt install nfs-common -y
mkdir -p /home/ubuntu/cluster_share

# Mount (Run once)
sudo mount ubuntu-1:/home/ubuntu/cluster_share /home/ubuntu/cluster_share

# Make Permanent (Add to /etc/fstab)
echo "ubuntu-1:/home/ubuntu/cluster_share /home/ubuntu/cluster_share nfs defaults 0 0" | sudo tee -a /etc/fstab
```

---

### Step 4: SLURM Installation
**1. Install Software (Run on ALL Nodes):**
```bash
sudo add-apt-repository universe -y
sudo apt update
sudo apt install munge slurm-wlm -y
```

**2. Munge Authentication:**
*   **On Head Node:**
    ```bash
    # Create and encode key
    sudo /usr/sbin/create-munge-key -r
    sudo cat /etc/munge/munge.key | base64
    ```
    *(Copy the text block)*.
*   **On Workers:**
    ```bash
    # Decode and save key
    echo "PASTED_TEXT_BLOCK" | base64 -d | sudo tee /etc/munge/munge.key
    ```
*   **On ALL Nodes:**
    ```bash
    sudo chown munge:munge /etc/munge/munge.key
    sudo chmod 400 /etc/munge/munge.key
    sudo systemctl restart munge
    ```

**3. Configure SLURM (Run on ALL Nodes):**
`sudo nano /etc/slurm/slurm.conf` -> Paste this exact config:
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

**5. Test:**
On Head Node: `srun -N3 hostname`
