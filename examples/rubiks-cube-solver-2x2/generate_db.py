#!/usr/bin/env python3
"""
generate_db.py: Pre-computes states to Depth 8 (QTM).
"""
import pickle
from collections import deque
from cube_utils import SOLVED_STATE, ALL_MOVES, apply_move

DEPTH_LIMIT = 8
DB_FILE = "halfway.pkl"

MOVES_RESTRICTED = {
    k: v for k, v in ALL_MOVES.items() 
    if k[0] in ['R', 'F', 'U']
}

def generate():
    # Visited stores { State : (Parent_State, Move_From_Parent) }
    visited = {SOLVED_STATE: (None, None)}
    queue = deque([(SOLVED_STATE, 0)])
    
    print(f"Generating Database to Depth {DEPTH_LIMIT}...")
    
    count = 0
    depth_counts = {}
    
    while queue:
        curr, depth = queue.popleft()
        
        # Track stats
        depth_counts[depth] = depth_counts.get(depth, 0) + 1
        
        if depth >= DEPTH_LIMIT:
            continue
            
        for m, _ in MOVES_RESTRICTED.items():
            nxt = apply_move(curr, m)
            if nxt not in visited:
                visited[nxt] = (curr, m)
                queue.append((nxt, depth + 1))
                #print(nxt)
                #print(visited[nxt])
				
        count += 1
        if count % 50000 == 0:
            print(depth_counts)
            print(f"Processed {count} states... Current Depth: {depth}")

    print("\nGeneration Complete.")
    print(f"Total Unique States: {len(visited)}")
    print("States per depth:", dict(sorted(depth_counts.items())))
    
    with open(DB_FILE, "wb") as f:
        pickle.dump(visited, f)
    print(f"Saved to {DB_FILE}")

if __name__ == "__main__":
    generate()