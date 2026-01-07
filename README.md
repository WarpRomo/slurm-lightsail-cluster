### Infrastructure Overview
*   **Head Node:** `ubuntu-1` (Public IP: `X.X.X.X`)
*   **Worker 1:** `ubuntu-2` (Public IP: `Y.Y.Y.Y`)
*   **Worker 2:** `ubuntu-3` (Public IP: `Z.Z.Z.Z`)
*   **OS:** Ubuntu 22.04 LTS

---

### Phase 1: AWS Firewall (Networking)
Go to the **Lightsail Console > Networking** for **ALL 3 INSTANCES**. Add these IPv4 Firewall rules.
*For maximum security, restrict these ports to the Public IPs of your other 2 nodes.*

| Protocol | Port Range | Purpose |
| :--- | :--- | :--- |
| **TCP** | `22` | SSH (PuTTY) |
| **TCP** | `6817 - 6818` | Slurm Controller |
| **TCP** | `60001 - 60009` | Slurm Data (`srun`) |
| **TCP** | `60010` | PyTorch Master |
| **TCP** | `60011 - 60020`| PyTorch Workers |
| **TCP** | `2049` | NFS Storage |
| **TCP** | `111` | NFS RPC |
| **UDP** | `111` | NFS RPC |

---

### Phase 2: System Prep & Auth
**1. Set Hostnames (Run on respective nodes):**
```bash
sudo hostnamectl set-hostname ubuntu-1  # On Head Node
sudo hostnamectl set-hostname ubuntu-2  # On Worker 1
sudo hostnamectl set-hostname ubuntu-3  # On Worker 2
```

**2. Configure DNS (Run on ALL 3 Nodes):**
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

### Phase 3: NFS Shared Storage
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

### Phase 4: SLURM Installation
**1. Install Software (Run on ALL 3 Nodes):**
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
*   **On ALL 3 Nodes:**
    ```bash
    sudo chown munge:munge /etc/munge/munge.key
    sudo chmod 400 /etc/munge/munge.key
    sudo systemctl restart munge
    ```

**3. Configure SLURM (Run on ALL 3 Nodes):**
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

**4. Create Log Dirs & Start (Run on ALL 3 Nodes):**
```bash
sudo mkdir -p /var/log/slurm
sudo chown slurm:slurm /var/log/slurm
sudo systemctl restart slurmd
```
*(On Head Node Only: `sudo systemctl restart slurmctld`)*

**5. Test:**
On Head Node: `srun -N3 hostname`

---
