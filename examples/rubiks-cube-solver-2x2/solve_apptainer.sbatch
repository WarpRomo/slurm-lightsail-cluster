#!/bin/bash
#SBATCH --output=./logs/solver.out
#SBATCH --error=./logs/solver.err
#SBATCH --job-name=cube_solver
#SBATCH --nodes=5
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1

# ------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------
# Explicitly set the path so all nodes find the files
# Change this if your path is different
PROJECT_DIR="/home/ubuntu/cluster_share" 
IMAGE_PATH="$PROJECT_DIR/rubiks_solver.sif"

cd $PROJECT_DIR
mkdir -p logs

# 1. Validation: Ensure a scramble was passed
if [ -z "$1" ]; then
    echo "Error: No scramble provided."
    echo "Usage: sbatch solve.sbatch \"0 1 2 3...\""
    exit 1
fi

SCRAMBLE="$1"

echo "Job ID: $SLURM_JOB_ID"
echo "Master Node: $(hostname)"
echo "Scramble Input: $SCRAMBLE"
echo "Container: $IMAGE_PATH"

# 2. Setup: Generate DB if missing (One-time check)
# We run python INSIDE the container to generate the pickle file
if [ ! -f "halfway.pkl" ]; then
    echo "Database missing. Generating via Apptainer..."
    apptainer exec "$IMAGE_PATH" python3 -u generate_db.py
fi

# 3. Execution: Run Distributed Solver
# -u ensures output is flushed immediately
echo "Starting MPI Solver..."

# EXPLANATION OF COMMAND:
# mpirun ...       -> Tells all nodes to listen
# apptainer exec   -> Starts the container on every node
# python3 ...      -> Runs the code inside that container
mpirun -np $SLURM_NTASKS \
    apptainer exec "$IMAGE_PATH" \
    python3 -u mpi_solver.py "$SCRAMBLE"