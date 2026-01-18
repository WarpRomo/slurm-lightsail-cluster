#!/bin/bash
#SBATCH --job-name=mnist-ddp
#SBATCH --nodes=4                # Use all 4 worker nodes
#SBATCH --ntasks-per-node=1      # 1 Python process per node (change to 2 or 4 if you have more cores)
#SBATCH --cpus-per-task=1        # CPUs allocated to that process
#SBATCH --chdir=/home/ubuntu/cluster_share   # Work directly inside the shared folder
#SBATCH --output=/home/ubuntu/cluster_share/logs/%x_%j.out  # Standard output
#SBATCH --error=/home/ubuntu/cluster_share/logs/%x_%j.err   # Standard error

# ---------------------------------------------------------
# ENVIRONMENT SETUP
# ---------------------------------------------------------
# Activate the virtual environment located in the shared folder
source /home/ubuntu/cluster_share/venv/bin/activate

# ---------------------------------------------------------
# NETWORK SETUP
# ---------------------------------------------------------
# Get the first node name from the node list (this will be our Master)
nodes=$(scontrol show hostnames "$SLURM_JOB_NODELIST")
nodes_array=($nodes)
head_node=${nodes_array[0]}

# Get the IP address of the master node. 
# Even with static IPs, we dynamically fetch the IP of the *current* job's master node.
head_node_ip=$(srun --nodes=1 --ntasks=1 -w "$head_node" hostname --ip-address)

echo "Nodes allocated: $nodes"
echo "Master node: $head_node"
echo "Master IP: $head_node_ip"

# Export variables for PyTorch DDP
export MASTER_ADDR=$head_node_ip
export MASTER_PORT=29500
export WORLD_SIZE=$SLURM_NTASKS

# ---------------------------------------------------------
# EXECUTION
# ---------------------------------------------------------
mkdir -p logs

# Run the training script
srun python3 mnist_ddp.py