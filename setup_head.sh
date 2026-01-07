#!/bin/bash
source ./0_config.sh

echo ">>> SETTING UP HEAD NODE (UBUNTU-1)..."

# 1. Hostname & DNS
sudo hostnamectl set-hostname ubuntu-1
sudo sed -i '/127.0.1.1/d' /etc/hosts
echo "$IP_HEAD ubuntu-1" | sudo tee -a /etc/hosts
echo "$IP_WORKER1 ubuntu-2" | sudo tee -a /etc/hosts
echo "$IP_WORKER2 ubuntu-3" | sudo tee -a /etc/hosts

# 2. Install Dependencies
sudo add-apt-repository universe -y
sudo apt update
sudo apt install munge slurm-wlm nfs-kernel-server python3-pip -y
pip3 install torch torchvision

# 3. Setup NFS Server
echo ">>> CONFIGURING NFS SERVER..."
mkdir -p /home/ubuntu/cluster_share
sudo chown ubuntu:ubuntu /home/ubuntu/cluster_share
sudo chmod 777 /home/ubuntu/cluster_share
echo "/home/ubuntu/cluster_share ubuntu-2(rw,sync,no_subtree_check) ubuntu-3(rw,sync,no_subtree_check)" | sudo tee /etc/exports
sudo exportfs -ra
sudo systemctl restart nfs-kernel-server

# 4. Generate Munge Key
echo ">>> GENERATING MUNGE KEY..."
sudo /usr/sbin/create-munge-key -r
sudo chown munge:munge /etc/munge/munge.key
sudo chmod 400 /etc/munge/munge.key
sudo systemctl restart munge

# 5. Generate SLURM Config
echo ">>> GENERATING SLURM CONFIG..."
sudo mkdir -p /var/log/slurm
sudo chown slurm:slurm /var/log/slurm

cat <<EOF | sudo tee /etc/slurm/slurm.conf
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
SlurmctldTimeout=300
SlurmdTimeout=300
SrunPortRange=$SLURM_PORTS
SchedulerType=sched/backfill
SelectType=select/cons_res
SelectTypeParameters=CR_Core
SlurmctldDebug=3
SlurmctldLogFile=/var/log/slurm/slurmctld.log
SlurmdDebug=3
SlurmdLogFile=/var/log/slurm/slurmd.log
NodeName=ubuntu-1 CPUs=2 RealMemory=400 State=UNKNOWN
NodeName=ubuntu-2 CPUs=2 RealMemory=400 State=UNKNOWN
NodeName=ubuntu-3 CPUs=2 RealMemory=400 State=UNKNOWN
PartitionName=debug Nodes=ubuntu-[1-3] Default=YES MaxTime=INFINITE State=UP
EOF

# 6. Start Services
sudo systemctl restart slurmctld
sudo systemctl restart slurmd

# 7. Output Key for Workers
echo ""
echo "======================================================="
echo "SETUP COMPLETE."
echo "COPY THE KEY BELOW (You need it for the worker script):"
echo "======================================================="
sudo cat /etc/munge/munge.key | base64
echo "======================================================="