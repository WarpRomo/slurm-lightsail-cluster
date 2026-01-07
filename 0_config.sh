#!/bin/bash

# ==========================================
# CONFIGURATION - EDIT THESE IPS
# ==========================================
IP_HEAD="X.X.X.X"   # Replace with Ubuntu-1 Public IP
IP_WORKER1="Y.Y.Y.Y" # Replace with Ubuntu-2 Public IP
IP_WORKER2="Z.Z.Z.Z"  # Replace with Ubuntu-3 Public IP

# Defines the specific ports
SLURM_PORTS="60001-60009"
PYTORCH_MASTER_PORT="60010"