from __future__ import annotations
import argparse
import copy
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from time import sleep
from typing import Tuple, TypeVar, Type, Iterable, ClassVar
from ai_wargame_config import UnitType, Player, GameType, Options, Stats
from ai_wargame_units import Unit
from ai_wargame_coords import Coord, CoordPair


import random
from pip._vendor import requests


# Putting these in a separate file for now, but they'll have to go in the main code for ease of reference.
# How should we pass the current player, board, etc?

# What do we need?


# Class for a game tree node.
class GameTreeNode:
    myBoardConfiguration = None # configuration of the game board
    
    myParent = None # parent node
    myChildren = [] # child nodes
    
    myDepth = 0 # int depth
    myScore = 0 # int score
    
    # Node constructor
    def __init__(self, parent = None): # Also needs to know who is the current player?
        # Where to compute the board configuration?
        self.myParent = parent
        if (self.myParent != None): self.myDepth = self.myParent.myDepth + 1
        
    # Generate the node's children.
    def generate_children(self, current_player, maxdepth):
        self.myChildren = generate_child_nodes(current_player, self, self.myBoardConfiguration, self.myDepth, maxdepth)
    
    # Calculate the node's heuristic score.
    def score_me(self, current_player):
        self.myScore = heuristic_score(current_player, self.myBoardConfiguration)

    def get_move(self, previous_board) -> Tuple[int, CoordPair | None, float]:
        # To do: return the move that transforms the input board into the one represented by this node.
        return
    
    def to_string(self) -> str:
        return "My parent: {}.\nMy depth: {}.".format(self.myParent, self.myDepth)



# Function that explores and lists the possible moves / builds the game tree
def generate_child_nodes(current_player, current_board, current_depth, maxdepth, currentNode = None):
    
    child_nodes = []
    
    # There's already a function that generates the valid potential moves. We only need to draw their boards from there.
    
    # Generate the nodes:
    # for each of the active player's units in the current board.
        # try all moves
        # try all attacks
        # try all heals
        # try all self destructs
    # See the main file for code that already seems to do this.
    # Draw a potential board for each
    
    # If the current depth is lower than the max depth, also generate the nodes' children 
    #if current_depth < maxdepth:
    
    #child_nodes.append(GameTreeNode())

    return child_nodes



# Basic recursive minimax algorithm
def move_by_minimax(current_player, current_board, maxdepth):
 
    best_move = None
    best_value = int('-inf') if (current_player == Player.Attacker) else int('inf')
    
    # Generate the game tree to the maxdepth.
    initial_children = generate_child_nodes(current_player, current_board, 0, maxdepth) # Or should the current depth be one?
    
    # If the current player is the attacker, start with min.
    if current_player == Player.Attacker:
        for child in initial_children:
            current_value = minimax(current_player.next(), child, maxdepth)
            if current_value > best_value:
                best_value = current_value
                best_move = child.get_move(current_board)
    else: # Else, start with max. 
        for child in initial_children:
            current_value = minimax(current_player.next(), child, maxdepth)
            if current_value < best_value: # Having the player check above instead of here repeats more code, but ensures we make fewer checks.
                best_value = current_value
                best_move = child.get_move(current_board)
    
    return best_move

    # To do: handle min depth. I don't think that's actually needed.
    # To do: handle max time elapsed.


def minimax (current_player, current_node, maxdepth):
    
    # Attacker is max, defender is min.
    
    if (current_node.myDepth == maxdepth): # Have we reached the maximum depth?
        # I'm not sure I'm doing depth the right way. 
        # To do: also check whether the node leads in someone's victory?
        # Do we calculate the score here?
        return current_node.myScore
    
    if current_player == Player.Attacker: # Maximizing player
        best_value = int('-inf')
        
        for child in current_node.myChildren:
            # To do: Implement alphabeta pruning.
            current_value = minimax(current_player.next(), child, maxdepth)
            best_value = max(best_value, current_value)
        return best_value
    
    else: # Minimizing player.
        best_value = int('inf')
        
        for child in current_node.myChildren:
            # To do: Implement alphabeta pruning.
            current_value = minimax(current_player.next(), child, maxdepth)
            best_value = min(best_value, current_value)
        return best_value
    
    # To do: implement optional alpha-beta pruning.


# Heuristic function
def heuristic_score(current_player, board_config) -> int:
    
    # Score the given board configuration.
    # 
    
    # Ideas:
        # player vs enemy units left alive
        # total health of one's units vs enemy's (weighted by unit type?)
        # 
    
    return 1