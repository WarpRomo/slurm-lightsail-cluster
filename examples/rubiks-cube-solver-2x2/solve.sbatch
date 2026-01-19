#!/bin/bash
#SBATCH --job-name=cube_solver
#SBATCH --nodes=5
#SBATCH --ntasks-per-node=1
#SBATCH --output=solution-%j.out
#SBATCH --error=solution-%j.err

# 1. Validation: Ensure a scramble was passed
if [ -z "$1" ]; then
    echo "Error: No scramble provided."
    echo "Usage: sbatch solve.slurm \"0 1 2 3...\""
    exit 1
fi

SCRAMBLE="$1"

echo "Job ID: $SLURM_JOB_ID"
echo "Master Node: $(hostname)"
echo "Scramble Input: $SCRAMBLE"

# 2. Setup: Generate DB if missing (One-time check)
if [ ! -f "halfway.pkl" ]; then
    echo "Database missing. Generating..."
    python3 -u generate_db.py
fi

# 3. Execution: Run Distributed Solver
# -u ensures output is flushed immediately to the .out file
echo "Starting MPI Solver..."
mpirun python3 -u mpi_solver.py "$SCRAMBLE"