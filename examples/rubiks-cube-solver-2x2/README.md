# Distributed 2x2 Rubik's Cube Solver

This directory contains a high-performance, distributed solver for the 2x2 Rubik's Cube (Pocket Cube). It utilizes **MPI (Message Passing Interface)** to parallelize the search space across multiple nodes in a Slurm cluster, employing a **Bidirectional Breadth-First Search (Meet-in-the-Middle)** algorithm.

## Overview

This example demonstrates:
*   **Distributed Computing:** Using `mpi4py` to scatter search frontiers across worker nodes.
*   **Algorithmic Optimization:** Implementing a "Fixed Corner" strategy to reduce state space redundancy by normalizing cube orientation.
*   **Pattern Databases:** Pre-computing the back-half of the search tree to instant lookup tables.
*   **State Visualization:** Terminal-based colored visualization of the cube state.

## Demo

Below are examples of the solver running on the cluster, distributing the workload, and finding the optimal solution.

<div align="center">
  <img width="1000" alt="cube1" src="https://github.com/user-attachments/assets/2c2990ac-7403-42a6-a5f2-fe76cefa935d" />
  <img width="1000" alt="cube2" src="https://github.com/user-attachments/assets/0d3c07b3-f838-47f1-aaac-669e51e3194c" />
</div>

## Files

| File | Description |
| :--- | :--- |
| `mpi_solver.py` | The main distributed solver. It coordinates workers, manages the search frontier, and reconstructs the solution path. |
| `generate_db.py` | Pre-computes the "God's Number" database up to depth 8 (halfway) and saves it as `halfway.pkl`. |
| `solve.sbatch` | The Slurm submission script. It handles environment setup, MPI execution, and node allocation. |
| `cube_utils.py` | Core logic library containing move definitions, state transitions, and visualization tools. |
| `regular_solver.py` | A single-threaded version of the solver useful for local debugging without MPI. |

## How it Works

The 2x2 Cube has approximately 3.6 million unique states. To solve it efficiently, we use a **Bidirectional Search**:

1.  **Phase 1 (Pre-computation):** We generate a database (`halfway.pkl`) starting from the **Solved State** and working backwards up to depth 8. This stores every position reachable within 8 moves.
2.  **Phase 2 (Normalization):** When a scrambled state is input, the solver rotates the entire cube so that the **Back-Down-Left** corner is fixed in place. This drastically reduces the search space by eliminating rotational symmetry.
3.  **Phase 3 (Distributed Search):** The cluster searches *forwards* from the scrambled state. As soon as a node finds a state that exists in the pre-computed database, the two paths are stitched together to form the full solution.

## Prerequisites

Ensure your cluster is set up with the shared NFS directory mounted at `/home/ubuntu/cluster_share`.

### 1. Python Environment
You must create a virtual environment in the shared folder so all nodes can access the same dependencies (`mpi4py` is required).

```bash
cd /home/ubuntu/cluster_share
python3 -m venv venv
source venv/bin/activate
```

### 2. Installation
Install the required libraries.

```bash
pip install mpi4py colorama
```

## Usage

### 1. Generate the Database
Before running any solves, you must generate the pattern database. This only needs to be done once.

```bash
cd /home/ubuntu/cluster_share/examples/rubiks-cube-solver-2x2
python3 generate_db.py
```
*This will create a `halfway.pkl` file (~10MB).*

### 2. Submit a Job
To solve a cube, submit the `solve.sbatch` script with a scramble sequence (represented as 24 integers).

**Example Scramble:**
```bash
# Scramble representation: integers 0-23 representing the stickers on the faces
SCRAMBLE="2 18 21 1 8 14 6 10 11 13 20 3 16 15 12 17 23 5 0 19 7 9 22 4"

sbatch solve.sbatch "$SCRAMBLE"
```

### 3. View Results
Check the output log to see the solution sequence and cluster statistics.

```bash
cat slurm-<JOB_ID>.out
```

**Sample Output:**
```text
Master Node: ubuntu-1
Nodes Allocated: ubuntu-1, ubuntu-2, ubuntu-3, ubuntu-4, ubuntu-5
...
[Step 2] Frontier Size: 27

========================================
*** SOLUTION FOUND ***
Moves: 11
Sequence: U U R F U R U' F U R' F'
========================================

--- Cluster Statistics ---
Rank       | States Explored | Contribution
---------------------------------------------
0          | 2450            | 21.5%
1          | 2310            | 20.1%
...
```

> [!NOTE]
> **Normalization**
> If the input state is not oriented correctly (the fixed corner is in the wrong spot), the solver will print "PRE-SOLVE ORIENTATION REQUIRED" and automatically handle the rotation internally before solving. Also, Magenta is used to represent Orange, as Orange is not present in colorama.

> [!IMPORTANT]
> **Performance**
> This solver is optimized for finding the *optimal* (shortest) solution. Using more nodes significantly reduces the time per depth level.
