<div align="center">

# Slurm Lightsail Cluster

[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Platform](https://img.shields.io/badge/platform-AWS%20Lightsail-orange.svg)](https://aws.amazon.com/lightsail/)
[![Ansible](https://img.shields.io/badge/ansible-automated-red.svg)](https://www.ansible.com/)
[![Slurm](https://img.shields.io/badge/scheduler-SLURM-blue.svg)](https://slurm.schedmd.com/)

**High-Performance Computing (HPC) cluster deployment on AWS Lightsail.**
<br>
Utilizes SLURM for centralized job scheduling and NFS for shared storage across a Head Node and multiple Worker Nodes.

[Demo](#demo) • [Infrastructure](#infrastructure-overview) • [Ansible Automation](#option-1-ansible-automation-recommended) • [Shell Setup](#option-2-shell-scripts)

</div>

---

## Overview
The repository provides a comprehensive Ansible playbook to fully automate the setup, handling Munge authentication, DNS configuration, and service orchestration to enable secure, synchronized communication over private internal networking.

Alongside this infrastructure, this repository has HPC examples to demonstrate cluster capabilities:

| Example Project | Description | Key Technologies |
| :--- | :--- | :--- |
| **[PyTorch DDP](./examples/pytorch-ddp)** | Distributed training of a CNN on the MNIST dataset with real-time TensorBoard monitoring. | PyTorch DDP, NFS, Gloo |
| **[Rubik's Cube Solver](./examples/rubiks-cube-solver-2x2)** | High-performance distributed solver utilizing Bidirectional BFS and MPI pattern databases. | MPI (`mpi4py`), Algorithms, Python |

## Demo
Demonstration of slurm commands, NFS shared storage, and running a python script on the cluster.

<div align="center">
  <img width="995" height="722" alt="image" src="https://github.com/user-attachments/assets/26bd7631-7c68-435b-b235-c3c3a10a0d5f" />
  <img width="2306" height="258" alt="image" src="https://github.com/user-attachments/assets/80be19b2-645a-4e61-8f46-f092112724eb" />
  <img width="1112" height="453" alt="image" src="https://github.com/user-attachments/assets/34dba87c-3df4-46e5-a161-a038718cc49f" />
</div>


> **Watch the full recording:** [View Demo Video](https://github.com/user-attachments/assets/423419ec-421d-4a34-8db0-ea8ac98f3a0d)

---

## Setup Guide

### Infrastructure Overview
*   **Head Node:** `ubuntu-1`
*   **Worker Nodes:** `ubuntu-2`, `ubuntu-3`, `ubuntu-4`...
*   **OS:** Ubuntu 22.04 LTS

### AWS Firewall (Networking)
You are required to do this step if you would like nodes to work cross-region. Otherwise, if all nodes are in the same region, you may skip this step. 
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
Navigate to the `shell/` folder in this repository, and download the shell scripts.

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

> [!NOTE]
> The Shell script version of this project only supports 1 Head node and 2 Worker nodes. If you would like unlimited nodes, use the Ansible Playbook provided in this repository. 
