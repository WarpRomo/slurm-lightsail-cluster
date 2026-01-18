import os
import time
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets, transforms
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data.distributed import DistributedSampler
from torch.utils.tensorboard import SummaryWriter

# ---------------------------------------------------------
# CUSTOM LOGGER
# ---------------------------------------------------------
# This function prints to console AND logs to TensorBoard
def log_event(writer, step, message):
    # 1. Print to console (so you have a backup)
    print(f"{message}", flush=True)
    
    # 2. Send to TensorBoard "Text" tab
    if writer:
        # We use a markdown table format for cleaner looking logs
        writer.add_text("Training Logs", message, step)
        writer.flush()

def setup():
    if "SLURM_PROCID" in os.environ:
        rank = int(os.environ["SLURM_PROCID"])
        world_size = int(os.environ["SLURM_NTASKS"])
        os.environ["RANK"] = str(rank)
        os.environ["WORLD_SIZE"] = str(world_size)
        os.environ["LOCAL_RANK"] = os.environ["SLURM_LOCALID"]
        
        if "MASTER_ADDR" not in os.environ:
            os.environ["MASTER_ADDR"] = "localhost" 
        if "MASTER_PORT" not in os.environ:
            os.environ["MASTER_PORT"] = "29500"
            
        print(f"Slurm detected: Rank {rank} of {world_size}", flush=True)

    print(f"Initializing Process Group...", flush=True)
    dist.init_process_group(backend="gloo")
    print(f"Process Group Initialized successfully.", flush=True)

def cleanup():
    dist.destroy_process_group()

class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, 3, 1)
        self.conv2 = nn.Conv2d(32, 64, 3, 1)
        self.dropout1 = nn.Dropout(0.25)
        self.dropout2 = nn.Dropout(0.5)
        self.fc1 = nn.Linear(9216, 128)
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        x = self.conv1(x)
        x = F.relu(x)
        x = self.conv2(x)
        x = F.relu(x)
        x = F.max_pool2d(x, 2)
        x = self.dropout1(x)
        x = torch.flatten(x, 1)
        x = self.fc1(x)
        x = F.relu(x)
        x = self.dropout2(x)
        x = self.fc2(x)
        output = F.log_softmax(x, dim=1)
        return output

def train(rank, model, device, train_loader, optimizer, epoch, writer):
    model.train()
    for batch_idx, (data, target) in enumerate(train_loader):
        data, target = data.to(device), target.to(device)
        optimizer.zero_grad()
        output = model(data)
        loss = F.nll_loss(output, target)
        loss.backward()
        optimizer.step()
        
        # Calculate a global step for plotting
        step = (epoch - 1) * len(train_loader) + batch_idx

        # Only Rank 0 logs data
        if rank == 0:
            # Log heavily at the start (every batch for first 5), then every 2
            if batch_idx < 5 or batch_idx % 2 == 0:
                msg = f"Epoch: {epoch} [{batch_idx}/{len(train_loader)}] Loss: {loss.item():.6f}"
                log_event(writer, step, msg)
                
                # Also log the scalar graph
                writer.add_scalar('Training Loss', loss.item(), step)

def main():
    setup()
    rank = dist.get_rank()
    world_size = dist.get_world_size()
    
    # Define data path
    data_path = "/home/ubuntu/cluster_share/data"
    device = torch.device("cpu")

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])

    # Setup Writer (Only on Rank 0)
    writer = None
    if rank == 0:
        log_dir = '/home/ubuntu/cluster_share/runs/mnist_experiment'
        # We start with step 0
        writer = SummaryWriter(log_dir)
        log_event(writer, 0, f"**Run Started** | Rank: {rank} | World Size: {world_size}")

    # ---------------------------------------------------------
    # DATA DOWNLOAD
    # ---------------------------------------------------------
    if rank == 0:
        log_event(writer, 1, "Checking/Downloading dataset...")
        if not os.path.exists(data_path):
            os.makedirs(data_path)
        datasets.MNIST(data_path, train=True, download=True, transform=transform)
        log_event(writer, 2, "Download complete. Releasing barrier.")
    
    # Barrier: Everyone waits here
    dist.barrier()
    
    if rank == 0:
        log_event(writer, 3, "Barrier passed. All nodes have data.")

    # ---------------------------------------------------------
    # DATA LOADER
    # ---------------------------------------------------------
    dataset1 = datasets.MNIST(data_path, train=True, download=False, transform=transform)
    sampler1 = DistributedSampler(dataset1, num_replicas=world_size, rank=rank)
    train_loader = torch.utils.data.DataLoader(dataset1, batch_size=64, sampler=sampler1, num_workers=0)
    
    if rank == 0:
        log_event(writer, 4, "DataLoader ready.")

    # ---------------------------------------------------------
    # MODEL
    # ---------------------------------------------------------
    model = Net().to(device)
    model = DDP(model)
    optimizer = optim.Adadelta(model.parameters(), lr=1.0)
    
    if rank == 0:
        log_event(writer, 5, "Model initialized & DDP wrapped. Starting Training Loop...")

    # ---------------------------------------------------------
    # TRAINING
    # ---------------------------------------------------------
    for epoch in range(1, 1000):
        sampler1.set_epoch(epoch)
        if rank == 0:
            log_event(writer, epoch*1000, f"Starting Epoch {epoch}")
            
        train(rank, model, device, train_loader, optimizer, epoch, writer)
        
        if rank == 0:
            log_event(writer, (epoch+1)*1000, f"End of Epoch {epoch}. Saving checkpoint...")
            writer.add_scalar('Epoch', epoch, epoch)
            torch.save(model.state_dict(), "/home/ubuntu/cluster_share/mnist_cnn.pt")

    if rank == 0:
        log_event(writer, 999999, "Training complete.")
        writer.close()

    cleanup()

if __name__ == '__main__':
    main()