#!/usr/bin/env python3
"""
cube_utils.py: Core logic for 2x2 Rubik's Cube (QTM).
Verified Move Definitions to ensure geometric consistency.
"""

import sys
import argparse

import colorama
from colorama import Back, Style

colorama.init(autoreset=True)

# 2x2 Cube Layout (24 integers)
#       00 01
#       02 03
# 04 05 08 09 12 13 16 17
# 06 07 10 11 14 15 18 19
#       20 21
#       22 23
SOLVED_STATE = tuple(range(24))

# Base Moves (90 degree clockwise)
# format: new_state[i] = old_state[MOVES_BASE[move][i]]
MOVES_BASE = {
    'U': [2, 0, 3, 1, 8, 9, 6, 7, 12, 13, 10, 11, 16, 17, 14, 15, 4, 5, 18, 19, 20, 21, 22, 23],
    'D': [0, 1, 2, 3, 4, 5, 18, 19, 8, 9, 6, 7, 12, 13, 10, 11, 16, 17, 14, 15, 22, 20, 23, 21],
    'L': [19, 1, 17, 3, 6, 4, 7, 5, 0, 9, 2, 11, 12, 13, 14, 15, 16, 22, 18, 20, 8, 21, 10, 23],
    'R': [0, 9, 2, 11, 4, 5, 6, 7, 8, 21, 10, 23, 14, 12, 15, 13, 3, 17, 1, 19, 20, 18, 22, 16],
    'F': [0, 1, 7, 5, 4, 20, 6, 21, 10, 8, 11, 9, 2, 13, 3, 15, 16, 17, 18, 19, 14, 12, 22, 23],
    'B': [13, 15, 2, 3, 1, 5, 0, 7, 8, 9, 10, 11, 12, 23, 14, 22, 18, 16, 19, 17, 20, 21, 6, 4]
}

ALL_MOVES = {}

def apply_perm(state, perm):
    """Permutes the state tuple based on indices."""
    return tuple(state[i] for i in perm)

def get_inverse_move(move_str):
    """Inverts a move string (e.g., U -> U', U' -> U)."""
    if "'" in move_str:
        return move_str.replace("'", "")
    return move_str + "'"

# Generate Full QTM Move Set (Clockwise + Counter-Clockwise)
for m, p in MOVES_BASE.items():
    # Normal (Clockwise 90)
    ALL_MOVES[m] = p
    # Prime (Counter-Clockwise 90) = 3x Clockwise
    p2 = apply_perm(p, p)
    p3 = apply_perm(p2, p)
    ALL_MOVES[m + "'"] = p3

def apply_move(state, move_name):
    return apply_perm(state, ALL_MOVES[move_name])
	
def visualize_cube(state):
    """
    Prints a visual representation of the 2x2 cube state using colorama.
    """
    
    # Define Block Style (2 spaces for a square look)
    BLOCK = "  "
    
    # Map Colors using Colorama constants
    # NOTE: Standard terminals lack "Orange", so we use MAGENTA for L (Orange).
    COLORS = {
        'U': Back.WHITE,
        'L': Back.MAGENTA,  # Standard fallback for Orange
        'F': Back.GREEN,
        'R': Back.RED,
        'B': Back.BLUE,
        'D': Back.YELLOW
    }

    def get_color_code(val):
        """Maps a state integer (0-23) to its original face color."""
        if 0 <= val <= 3:   return COLORS['U']
        if 4 <= val <= 7:   return COLORS['L']
        if 8 <= val <= 11:  return COLORS['F']
        if 12 <= val <= 15: return COLORS['R']
        if 16 <= val <= 19: return COLORS['B']
        if 20 <= val <= 23: return COLORS['D']
        return Back.RESET # Error case

    def b(index):
        """Returns a colored block for the value at the given state index."""
        color = get_color_code(state[index])
        return f"{color}{BLOCK}{Style.RESET_ALL}"

    # Spacer for the indentation
    S = "    " 

    # Construct lines
    #       00 01
    #       02 03
    # 04 05 08 09 12 13 16 17
    # 06 07 10 11 14 15 18 19
    #       20 21
    #       22 23
    
    print("\nState Visualization:")
    print(f"{S}{b(0)}{b(1)}")          # U Top
    print(f"{S}{b(2)}{b(3)}")          # U Bottom
    
    # Middle Row (L, F, R, B)
    print(f"{b(4)}{b(5)}{b(8)}{b(9)}{b(12)}{b(13)}{b(16)}{b(17)}")
    print(f"{b(6)}{b(7)}{b(10)}{b(11)}{b(14)}{b(15)}{b(18)}{b(19)}")
    
    print(f"{S}{b(20)}{b(21)}")        # D Top
    print(f"{S}{b(22)}{b(23)}")        # D Bottom
    print("") # Newline at end

# --- Test Usage ---
# R L U D F B
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="2x2 Cube Move Applicator")
    parser.add_argument("moves", nargs="*", help="Sequence of moves (e.g. R U R' F)")
    args = parser.parse_args()

    # 1. Start Solved
    current_state = SOLVED_STATE
    
    # 2. Determine Moves
    if args.moves:
        # Flatten list if arguments are passed like: python cube_utils.py R U R'
        # or python cube_utils.py "R U R'"
        raw_input = " ".join(args.moves)
        moves = raw_input.replace(",", " ").split()
    else:
        # Default sequence if no args provided
        moves = ["R", "U", "R'", "F", "U", "F'", "U'", "R'", "F", "R'", "U", "F", "U'"]

    print("Initial State:")
    visualize_cube(current_state)

    print(f"Applying sequence: {' '.join(moves)}")
    
    valid_sequence = True
    for m in moves:
        if m not in ALL_MOVES:
            print(f"Error: Unknown move '{m}'")
            valid_sequence = False
            break
        current_state = apply_move(current_state, m)
    
    if valid_sequence:
        visualize_cube(current_state)
        print("Final State Vector:")
        print(' '.join(map(str, current_state)))