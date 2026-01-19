#!/usr/bin/env python3
"""
regular_solver.py: Single-machine 2x2 Cube Solver (Debugging Version).
Uses the same logic as mpi_solver.py but without MPI dependencies.
"""
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
        # Rotate around U/D axis
        s = apply_move(state, 'U')
        return apply_move(s, "D'")
    elif rot_axis == 'x':
        # Rotate around R/L axis
        s = apply_move(state, 'R')
        return apply_move(s, "L'")
    return state

def normalize_to_fixed_corner(state):
    """
    Finds a sequence of whole-cube rotations (x, y) to place the
    Back-Down-Left corner stickers (Values 6, 19, 22) into their
    solved indices [6, 19, 22].
    """
    # Check if solved stickers 6, 19, 22 are at these indices.
    def is_normalized(s):
        return (s[6] == 6 and s[19] == 19 and s[22] == 22)

    if is_normalized(state):
        return state, []

    # BFS for orientation using virtual rotations
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
    # --- 1. Load Database ---
    print(f"Loading {DB_FILE}...")
    try:
        with open(DB_FILE, "rb") as f:
            backward_db = pickle.load(f)
    except FileNotFoundError:
        print(f"Error: {DB_FILE} missing. Run generate_db.py first.")
        sys.exit(1)
    print("Database loaded.")

    # --- 2. Setup Input ---
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
            sys.exit(1)

    print(f"[Solver] Raw State loaded.")

    # --- 3. Normalization Step ---
    try:
        norm_state, setup_moves = normalize_to_fixed_corner(start_state)
        
        if setup_moves:
            print("\n" + "="*40)
            print("PRE-SOLVE ORIENTATION REQUIRED")
            print(f"Hold the cube and rotate: {' '.join(setup_moves)}")
            print("(x = Turn whole cube up, y = Turn whole cube left)")
            print("="*40 + "\n")
        else:
            print("[Solver] Cube already oriented correctly.")
            
        start_state = norm_state
        
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"[Solver] Solving Normalized State...")

    # --- 4. Search Loop (Standard BFS) ---
    
    # Check if start is already in DB
    if start_state in backward_db:
        sol = reconstruct_full_path(start_state, [], backward_db)
        print("\n*** SOLUTION FOUND (In DB) ***")
        print(f"Moves: {' '.join(sol)}")
        sys.exit(0)

    # Define Restricted Moves (Must match DB generation)
    MOVES_TO_USE = [m for m in ALL_MOVES if m[0] in ['R', 'U', 'F']]

    frontier = [(start_state, [])]
    global_visited = {start_state}
    step = 0

    while frontier:
        print(f"[Step {step}] Frontier Size: {len(frontier)}")
        next_frontier = []
        
        for curr_state, curr_path in frontier:
            
            # Expand using restricted moves
            for m_name in MOVES_TO_USE:
                nxt = apply_move(curr_state, m_name)
                
                # Check Intersection
                if nxt in backward_db:
                    final_sol = reconstruct_full_path(nxt, curr_path + [m_name], backward_db)
                    print("\n" + "="*40)
                    print("*** SOLUTION FOUND ***")
                    print(f"Moves: {len(final_sol)}")
                    print(f"Sequence: {' '.join(final_sol)}")
                    print("="*40)
                    sys.exit(0)
                
                # Add to next level if not visited
                if nxt not in global_visited:
                    global_visited.add(nxt)
                    next_frontier.append((nxt, curr_path + [m_name]))
        
        frontier = next_frontier
        step += 1

    print("Search exhausted. No solution found (within reasonable depth).")

if __name__ == "__main__":
    main()