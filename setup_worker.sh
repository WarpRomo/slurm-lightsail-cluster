#!/bin/bash
source ./0_config.sh

NODE_NUM=$1

if [[ -z "$NODE_NUM" ]]; then
    echo "ERROR: You must specify the node number (2 or 3)."
    echo "Usage: ./setup_worker.sh 2"
    exit 1
fi

echo ">>> SETTING UP WORKER NODE: UBUNTU-$NODE_NUM ..."

# 1. Hostname & DNS
sudo hostnamectl set-hostname ubuntu-$NODE_NUM
sudo sed -i '/127.0.1.1/d' /etc/hosts
echo "$IP_HEAD ubuntu-1" | sudo tee -a /etc/hosts
echo "$IP_WORKER1 ubuntu-2" | sudo tee -a /etc/hosts
echo "$IP_WORKER2 ubuntu-3" | sudo tee -a /etc/hosts

# 2. Install Dependencies
sudo add-apt-repository universe -y
sudo apt update
sudo apt install munge slurm-wlm nfs-common python3-pip -y
pip3 install torch torchvision

# 3. Setup NFS Client
echo ">>> MOUNTING SHARED STORAGE..."
mkdir -p /home/ubuntu/cluster_share
sudo mount ubuntu-1:/home/ubuntu/cluster_share /home/ubuntu/cluster_share
echo "ubuntu-1:/home/ubuntu/cluster_share /home/ubuntu/cluster_share nfs defaults 0 0" | sudo tee -a /etc/fstab

# 4. Configure Munge (User Paste)
echo ""
echo ">>> PASTE THE MUNGE KEY FROM THE HEAD NODE NOW:"
read -p "Key: " MUNGE_KEY_B64
echo "$MUNGE_KEY_B64" | base64 -d | sudo tee /etc/munge/munge.key > /dev/null

sudo chown munge:munge /etc/munge/munge.key
sudo chmod 400 /etc/munge/munge.key
sudo systemctl restart munge

# 5. Generate SLURM Config (Same as Head)
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
sudo systemctl restart slurmd

echo ">>> WORKER SETUP COMPLETE."