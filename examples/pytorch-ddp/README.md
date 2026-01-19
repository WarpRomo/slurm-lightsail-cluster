# PyTorch Distributed Data Parallel (DDP)

This directory contains a complete project of training a Convolutional Neural Network (CNN) on the MNIST dataset using **PyTorch DDP**. It is optimized for CPU-only clusters (like standard AWS Lightsail instances) using the **Gloo** backend.

## Overview

This project demonstrates:
*   **Multi-Node Training:** Synchronizing gradients across multiple worker nodes.
*   **Shared Storage:** Using NFS at `/home/ubuntu/cluster_share` for datasets and checkpoints.
*   **Real-time Monitoring:** Custom TensorBoard logging with fast refresh rates.
*   **Fault Tolerance:** Handling process rank and world size via Slurm environment variables.

## Files

| File | Description |
| :--- | :--- |
| `mnist_ddp.py` | The main training script. It handles data downloading (on Rank 0), distributed sampling, and logging to TensorBoard. |
| `run_training.sbatch` | The Slurm submission script. It defines the resource allocation and sets up the execution environment. |
| `tensorboard.sh` | A helper script to launch TensorBoard with a fast reload interval for real-time monitoring. |

## Demo

Below are examples of the training process viewed through TensorBoard.

<div align="center">
  <img width="1000" alt="image" src="https://github.com/user-attachments/assets/a1c6be2a-66d5-49be-bd9d-40468d706e60" />
  <img width="1000" alt="image" src="https://github.com/user-attachments/assets/422a4e2d-9b48-4be2-b1be-7fa2c2712b70" />
</div>

## Prerequisites

Ensure your cluster is set up with the shared NFS directory mounted at `/home/ubuntu/cluster_share`.

### 1. Python Environment
You must create a virtual environment in the shared folder so all nodes can access the same dependencies.

```bash
cd /home/ubuntu/cluster_share
python3 -m venv venv
source venv/bin/activate
```

### 2. Installation
Install PyTorch (CPU version) and TensorBoard. The `--no-cache-dir` flag and specific index URL are recommended to save disk space and prevent memory issues on small instances.

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu --no-cache-dir
pip install tensorboard
```

## Usage

### 1. Submit the Job
The Slurm script is configured to use absolute paths. Submit it from anywhere:

```bash
cd /home/ubuntu/cluster_share/projects/pytorch-ddp
sbatch run_training.sbatch
```

### 2. Monitor with TensorBoard
To view the training progress, loss curves, and text logs in real-time, start the TensorBoard server on the head node.

**On the Head Node:**
```bash
./tensorboard.sh
```
*Note: This runs on port 6006 with a 1-second reload interval.*

**On Your Local Machine:**
Create an SSH tunnel to forward the port to your local browser:

```bash
ssh -L 6006:localhost:6006 ubuntu@<HEAD_NODE_IP>
```

Open your web browser to [http://localhost:6006](http://localhost:6006).

> [!NOTE]
> **Data Synchronization**
> The script is designed so that Rank 0 (Master) downloads the dataset to the shared folder first. All other nodes wait at a `dist.barrier()` until the download is complete before starting training.

> [!IMPORTANT]
> **Memory Usage**
> If your workers are small instances (e.g., 512MB or 1GB RAM), ensure you have enabled **Swap Memory** on all nodes, otherwise the Python processes may be killed by the OS.
