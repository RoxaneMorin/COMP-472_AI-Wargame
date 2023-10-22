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


# maximum and minimum values for our heuristic scores (usually represents an end of game condition)
MAX_HEURISTIC_SCORE = 2000000000
MIN_HEURISTIC_SCORE = -2000000000


# Putting these in a separate file for now, but they'll have to go in the main code for ease of reference.
# How should we pass the current player, board, etc?

# What do we need?


# Class for a game tree node.
class GameTreeNode:
    myGameConfiguration = None # configuration of the general game associated with this move, for ease of access.
    myBoardConfiguration = None # configuration of the game board.
    
    myParent = None # parent node
    myChildren = [] # child nodes
    
    myMove = None
    
    myDepth = 0 # int depth
    myScore = 0 # int score
    
    # Node constructor
    def __init__(self, current_game, move, parent = None): # Also needs to know who is the current player?
        self.myGameConfiguration = current_game
        self.myBoardConfiguration = current_game.board
        self.myMove = move
        
        self.myParent = parent
        if (self.myParent != None): self.myDepth = self.myParent.myDepth + 1
        
        #print(self.to_string())
        
    
    # Calculate the node's heuristic score.
    def score_me(self, current_player):
        self.myScore = heuristic_score(current_player, self.myBoardConfiguration)

    def get_move(self) -> Tuple[int, CoordPair | None, float]:
        # Seems to work without knowing the previous board.
        return self.myMove
    
    def to_string(self) -> str:
        return "\nMy move: {}. My Score: {}. My player: {}. My depth: {}".format(self.myMove, self.myScore, self.myGameConfiguration.next_player, self.myDepth)



# Function that explores and lists the possible moves / builds the game tree
def generate_child_nodes(current_player, current_game, current_depth, maxdepth, currentNode = None):
    
    current_game.next_player = current_player # Required to make sure they switch properly.

    # Generate the nodes:
    child_nodes = []
    
    # For each valid potential move...
    for potential_move in current_game.move_candidates():
        # Clone the game/board.
        new_game = current_game.clone()
        
        # Perform the move on it. 
        ## TO DO: perform the move on node_game!
        
        # Create the node proper.
        new_node = GameTreeNode(current_game = new_game, move = potential_move, parent = currentNode)
        child_nodes.append(new_node)
        
        # If the current depth is lower than the max depth, also generate the nodes' children 
        if new_node.myDepth < maxdepth:
            new_node.myChildren = generate_child_nodes(current_player.next(), new_game, current_depth+1, maxdepth, new_node)
            
    return child_nodes



# Basic recursive minimax algorithm
def move_by_minimax(current_game, current_player, maxdepth): # Should we pass the game itself?
 
    best_move = None
    best_value = MIN_HEURISTIC_SCORE if (current_player == Player.Attacker) else MAX_HEURISTIC_SCORE
    
    # Generate the game tree to the maxdepth.
    initial_children = generate_child_nodes(current_player, current_game, 0, maxdepth) # Or should the current depth be one?
    
    #print("\nThe current player is {}\n".format(current_player))
    
    # If the current player is the attacker, start with min.
    if current_player == Player.Attacker:
        for child in initial_children:
            current_value = minimax(current_player.next(), child, maxdepth)
            if current_value > best_value:
                best_value = current_value
                best_move = child.get_move()
                
    else: # Else, start with max. 
        for child in initial_children:
            current_value = minimax(current_player.next(), child, maxdepth)
            if current_value < best_value: # Having the player check above instead of here repeats more code, but ensures we make fewer checks.
                best_value = current_value
                best_move = child.get_move()
    
    return best_value, best_move

    # To do: handle max time elapsed.


def minimax (current_player, current_node, maxdepth):
    
    # Attacker is max, defender is min.
    
    if (current_node.myDepth == maxdepth): # Have we reached the maximum depth?
        # I'm not sure I'm doing depth the right way. 
        # To do: also check whether the node leads in someone's victory?
        # Do we calculate the score here?
        return current_node.myScore
    
    if current_player == Player.Attacker: # Maximizing player
        best_value = MIN_HEURISTIC_SCORE
        
        for child in current_node.myChildren:
            # To do: Implement alphabeta pruning.
            current_value = minimax(current_player.next(), child, maxdepth)
            best_value = max(best_value, current_value)
        return best_value
    
    else: # Minimizing player.
        best_value = MAX_HEURISTIC_SCORE
        
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