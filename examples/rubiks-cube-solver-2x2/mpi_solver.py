#!/usr/bin/env python3
"""
mpi_solver.py: Distributed 2x2 Cube Solver using MPI.
Refactored to prevent deadlocks and ensure statistics printing.
"""
from mpi4py import MPI
import pickle
import sys
import argparse
from collections import deque
from cube_utils import ALL_MOVES, apply_move, get_inverse_move

DB_FILE = "halfway.pkl"

# --- Rotation & Normalization Logic ---
def apply_cube_rotation(state, rot_axis):
    if rot_axis == 'y':
        s = apply_move(state, 'U')
        return apply_move(s, "D'")
    elif rot_axis == 'x':
        s = apply_move(state, 'R')
        return apply_move(s, "L'")
    return state

def normalize_to_fixed_corner(state):
    def is_normalized(s):
        return (s[6] == 6 and s[19] == 19 and s[22] == 22)

    if is_normalized(state):
        return state, []

    queue = deque([(state, [])])
    visited = {state}
    
    while queue:
        curr, path = queue.popleft()
        for rot in ['x', 'y']:
            nxt = apply_cube_rotation(curr, rot)
            if nxt not in visited:
                if is_normalized(nxt):
                    return nxt, path + [rot]
                visited.add(nxt)
                queue.append((nxt, path + [rot]))
    
    raise ValueError("State invalid: Fixed corner (Values 6,19,22) not found together.")

def reconstruct_full_path(meet_state, forward_path, backward_db):
    full_path = list(forward_path)
    curr = meet_state
    back_moves = []
    
    while True:
        entry = backward_db.get(curr)
        if not entry or entry[0] is None: 
            break
        parent, move = entry
        back_moves.append(get_inverse_move(move))
        curr = parent
        
    return full_path + back_moves

def main():
    # --- MPI INIT ---
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    # --- 1. Load Database ---
    backward_db = None
    try:
        with open(DB_FILE, "rb") as f:
            backward_db = pickle.load(f)
    except Exception as e:
        print(f"[Node {rank}] Error loading DB: {e}", flush=True)
        comm.Abort(1)
        sys.exit(1)

    print(f"[Node {rank}] Database loaded. Active.", flush=True)

    # BARRIER 1: Ensure all nodes are ready before Manager starts
    comm.Barrier()

    # --- 2. Setup Manager (Rank 0) ---
    global_visited = set()
    frontier = [] 
    local_state_count = 0 # Stat tracking
    
    # Logic flags
    found_solution_flag = False
    
    if rank == 0:
        parser = argparse.ArgumentParser()
        parser.add_argument("input", help="State string (space separated)")
        args = parser.parse_args()
        
        try:
            # Parse input string
            start_state = tuple(map(int, args.input.split()))
        except Exception:
            print("Error: Invalid input format.", flush=True)
            comm.Abort(1)
        
        # Normalization
        try:
            norm_state, setup_moves = normalize_to_fixed_corner(start_state)
            if setup_moves:
                print("\n" + "="*40, flush=True)
                print("PRE-SOLVE ORIENTATION REQUIRED", flush=True)
                print(f"Rotate: {' '.join(setup_moves)}", flush=True)
                print("="*40 + "\n", flush=True)
            else:
                print("[Manager] Cube oriented correctly.", flush=True)
            start_state = norm_state
        except ValueError as e:
            print(f"Error: {e}", flush=True)
            comm.Abort(1)

        print(f"[Manager] Solving Normalized State...", flush=True)
        
        # Check if start is already in DB
        if start_state in backward_db:
            sol = reconstruct_full_path(start_state, [], backward_db)
            print("\n*** SOLUTION FOUND (In DB) ***", flush=True)
            print(f"Moves: {' '.join(sol)}", flush=True)
            found_solution_flag = True
            # We do NOT exit here. We enter the loop so we can cleanly tell workers to STOP.
        else:
            frontier = [(start_state, [])]
            global_visited.add(start_state)

    # --- 3. Synchronous BFS Loop ---
    step = 0
    while True:
        # --- A. DECISION PHASE (Happens at Top of Loop) ---
        instruction = "SEARCH"
        
        if rank == 0:
            if found_solution_flag:
                instruction = "DONE"
            elif not frontier:
                instruction = "FAIL"
        
        # Broadcast decision to all workers
        instruction = comm.bcast(instruction, root=0)
        
        # Check decision
        if instruction == "DONE":
            break
        if instruction == "FAIL":
            if rank == 0: print("Search exhausted. No solution.", flush=True)
            break

        # --- B. WORK DISTRIBUTION ---
        chunks = []
        if rank == 0:
            print(f"[Step {step}] Frontier Size: {len(frontier)}", flush=True)
            pad_needed = (size - (len(frontier) % size)) % size
            frontier.extend([None] * pad_needed)
            k = len(frontier) // size
            chunks = [frontier[i * k : (i + 1) * k] for i in range(size)]
        
        local_tasks = comm.scatter(chunks, root=0)

        # --- C. LOCAL COMPUTATION ---
        local_next_level = []
        solution_found = None

        if local_tasks:
            for task in local_tasks:
                if task is None: continue
                
                curr_state, curr_path = task
                
                # Use Restricted Move Set (R, U, F) to stay in fixed-corner space
                MOVES_TO_USE = [m for m in ALL_MOVES if m[0] in ['R', 'U', 'F']]
                
                for m_name in MOVES_TO_USE:
                    local_state_count += 1 # Increment counter
                    
                    nxt = apply_move(curr_state, m_name)
                    
                    if nxt in backward_db:
                        solution_found = reconstruct_full_path(nxt, curr_path + [m_name], backward_db)
                        break
                    
                    local_next_level.append((nxt, curr_path + [m_name]))
                
                if solution_found: break

        # --- D. GATHER RESULTS ---
        all_solutions = comm.gather(solution_found, root=0)
        all_candidates = comm.gather(local_next_level, root=0)

        # --- E. MANAGER UPDATE (Rank 0 only) ---
        if rank == 0:
            final_sol = next((s for s in all_solutions if s), None)
            
            if final_sol:
                print("\n" + "="*40, flush=True)
                print("*** SOLUTION FOUND ***", flush=True)
                print(f"Moves: {len(final_sol)}", flush=True)
                print(f"Sequence: {' '.join(final_sol)}", flush=True)
                print("="*40, flush=True)
                found_solution_flag = True
                # Loop will repeat, hit Decision Phase, and broadcast DONE.
            else:
                # Update frontier for next step
                new_frontier = []
                for batch in all_candidates:
                    for state, path in batch:
                        if state not in global_visited:
                            global_visited.add(state)
                            new_frontier.append((state, path))
                frontier = new_frontier
                step += 1
        
        # Workers hit end of loop and return to 'instruction = comm.bcast'
    
    # --- 4. GATHER STATISTICS ---
    # Everyone reaches here after 'break'
    comm.Barrier() # Optional safety
    
    all_counts = comm.gather(local_state_count, root=0)

    if rank == 0:
        print("\n--- Cluster Statistics ---", flush=True)
        total_explored = sum(all_counts)
        print(f"{'Rank':<10} | {'States Explored':<15} | {'Contribution':<12}", flush=True)
        print("-" * 45, flush=True)
        for r, count in enumerate(all_counts):
            pct = (count / total_explored * 100) if total_explored > 0 else 0
            print(f"{r:<10} | {count:<15} | {pct:.1f}%", flush=True)
        print("-" * 45, flush=True)
        print(f"Total States Explored: {total_explored}", flush=True)
        print("-" * 45, flush=True)

if __name__ == "__main__":
    main()