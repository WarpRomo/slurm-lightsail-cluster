#!/usr/bin/env python3
"""
mpi_solver.py: Distributed 2x2 Cube Solver using MPI.
Includes automatic state normalization (rotation) using existing moves.
"""
from mpi4py import MPI
import pickle
import sys
import argparse
from collections import deque
from cube_utils import ALL_MOVES, apply_move, get_inverse_move

DB_FILE = "halfway.pkl"

def apply_cube_rotation(state, rot_axis):
    """
    Simulates a whole cube rotation using basic face turns.
    y (Vertical axis)   = U + D'
    x (Horizontal axis) = R + L'
    """
    if rot_axis == 'y':
        # Rotate around U/D axis: Top goes one way, Bottom goes the opposite
        s = apply_move(state, 'U')
        return apply_move(s, "D'")
    elif rot_axis == 'x':
        # Rotate around R/L axis: Right goes one way, Left goes the opposite
        s = apply_move(state, 'R')
        return apply_move(s, "L'")
    return state

def normalize_to_fixed_corner(state):
    """
    Finds a sequence of whole-cube rotations (x, y) to place the
    Back-Down-Left corner stickers (Values 6, 19, 22) into their
    solved indices [6, 19, 22].
    """
    # The Fixed Corner Indices in our restricted move set <R, U, F>
    # are L_BottomLeft(6), B_BottomRight(19), D_BottomLeft(22).
    
    # Check if solved stickers 6, 19, 22 are at these indices.
    def is_normalized(s):
        return (s[6] == 6 and s[19] == 19 and s[22] == 22)

    if is_normalized(state):
        return state, []

    # BFS for orientation
    # We only need x and y rotations to reach all 24 orientations.
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
    """
    Combines the forward path (Start -> Meet) 
    with the backward path (Meet -> Solved).
    """
    full_path = list(forward_path)
    curr = meet_state
    back_moves = []
    
    # Traceback from Meet -> Solved
    while True:
        entry = backward_db.get(curr)
        if not entry or entry[0] is None: 
            break
            
        parent, move = entry
        back_moves.append(get_inverse_move(move))
        curr = parent
        
    return full_path + back_moves

def main():
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    # --- 1. Load Database ---
    backward_db = None
    try:
        with open(DB_FILE, "rb") as f:
            backward_db = pickle.load(f)
    except FileNotFoundError:
        if rank == 0: 
            print(f"Error: {DB_FILE} missing. Run generate_db.py first.")
            comm.Abort(1)
        sys.exit(1)

    # --- 2. Setup Manager (Rank 0) ---
    global_visited = set()
    frontier = [] 
    
    if rank == 0:
        parser = argparse.ArgumentParser()
        parser.add_argument("input", help="State string (space separated) or file path")
        args = parser.parse_args()
        
        try:
            with open(args.input, 'r') as f:
                content = f.read().strip()
                start_state = tuple(map(int, content.split()))
        except FileNotFoundError:
            try:
                start_state = tuple(map(int, args.input.split()))
            except ValueError:
                print("Error: Invalid input format.")
                comm.Abort(1)
        
        # --- NORMALIZATION STEP ---
        try:
            norm_state, setup_moves = normalize_to_fixed_corner(start_state)
            
            if setup_moves:
                print("\n" + "="*40)
                print("PRE-SOLVE ORIENTATION REQUIRED")
                print(f"Hold the cube and rotate: {' '.join(setup_moves)}")
                print("(x = Turn whole cube up, y = Turn whole cube left)")
                print("="*40 + "\n")
            else:
                print("[Manager] Cube already oriented correctly.")
                
            start_state = norm_state
            
        except ValueError as e:
            print(f"Error: {e}")
            comm.Abort(1)

        print(f"[Manager] Solving Normalized State...")
        
        # Check if already in DB
        if start_state in backward_db:
            sol = reconstruct_full_path(start_state, [], backward_db)
            print("\n*** SOLUTION FOUND (In DB) ***")
            print(f"Moves: {' '.join(sol)}")
            comm.bcast("DONE", root=0)
            sys.exit(0)

        frontier = [(start_state, [])]
        global_visited.add(start_state)

    # --- 3. Synchronous BFS Loop ---
    step = 0
    while True:
        instruction = "CONTINUE"
        if rank == 0:
            if not frontier: instruction = "FAIL"
        
        instruction = comm.bcast(instruction, root=0)
        
        if instruction == "DONE": break
        if instruction == "FAIL":
            if rank == 0: print("Search exhausted. No solution.")
            break

        # --- Distribute Frontier ---
        chunks = []
        if rank == 0:
            print(f"[Step {step}] Frontier Size: {len(frontier)}")
            
            pad_needed = (size - (len(frontier) % size)) % size
            frontier.extend([None] * pad_needed)
            
            k = len(frontier) // size
            chunks = [frontier[i * k : (i + 1) * k] for i in range(size)]
        
        local_tasks = comm.scatter(chunks, root=0)

        # --- Compute (Workers) ---
        local_next_level = []
        solution_found = None

        if local_tasks:
            for task in local_tasks:
                if task is None: continue
                
                curr_state, curr_path = task
                
                # OPTIMIZATION:
                # Since we normalized the cube, we only need to search moves
                # that preserve the fixed corner (R, U, F).
                # Moving L, B, or D would break the normalization.
                MOVES_TO_USE = [m for m in ALL_MOVES if m[0] in ['R', 'U', 'F']]
                
                for m_name in MOVES_TO_USE:
                    nxt = apply_move(curr_state, m_name)
                    
                    if nxt in backward_db:
                        solution_found = reconstruct_full_path(nxt, curr_path + [m_name], backward_db)
                        break
                    
                    local_next_level.append((nxt, curr_path + [m_name]))
                
                if solution_found: break

        # --- Gather & Sync ---
        all_solutions = comm.gather(solution_found, root=0)
        all_candidates = comm.gather(local_next_level, root=0)

        # --- Manager Update ---
        if rank == 0:
            final_sol = next((s for s in all_solutions if s), None)
            
            if final_sol:
                print("\n" + "="*40)
                print("*** SOLUTION FOUND ***")
                print(f"Moves: {len(final_sol)}")
                print(f"Sequence: {' '.join(final_sol)}")
                print("="*40)
                comm.bcast("DONE", root=0)
                break
            else:
                comm.bcast("CONTINUE", root=0)

            new_frontier = []
            for batch in all_candidates:
                for state, path in batch:
                    if state not in global_visited:
                        global_visited.add(state)
                        new_frontier.append((state, path))
            
            frontier = new_frontier
            step += 1
        else:
            pass

if __name__ == "__main__":
    main()