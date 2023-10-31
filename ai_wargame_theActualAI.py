from __future__ import annotations
import argparse
import copy
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from time import sleep
from typing import Tuple, TypeVar, Type, Iterable, ClassVar
from ai_wargame_config import UnitType, Player, GameType, Options, Stats, HeurType
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
    def score_me(self):
        self.myScore = heuristic_score(self.myGameConfiguration)
        #print(self.myScore)

    def get_move(self) -> Tuple[int, CoordPair | None, float]:
        # Seems to work without knowing the previous board.
        return self.myMove
    
    def to_string(self) -> str:
        return "\nMy move: {}. My Score: {}. My player: {}. My depth: {}".format(self.myMove, self.myScore, self.myGameConfiguration.next_player, self.myDepth)



# Function that explores and lists the possible moves / builds the game tree
def generate_child_nodes(current_player, current_game, current_depth, maxdepth, currentNode = None, generateDescendents = False):
    
    #print("Generating a child at level {}".format(current_depth))
    
    current_game.next_player = current_player # Required to make sure they switch properly.

    # Generate the nodes:
    child_nodes = []
    
    # For each valid potential move...
    for potential_move in current_game.move_candidates():
        # Clone the game/board.
        new_game = current_game.clone()
        
        # Perform the move on it. 
        new_game.perform_move(potential_move, wordy=False)
        
        # Create the node proper.
        new_node = GameTreeNode(current_game = new_game, move = potential_move, parent = currentNode)
        child_nodes.append(new_node)
        
        # If the current depth is lower than the max depth, and isn't a victory state, also generate the nodes' children 
        if generateDescendents == True and new_node.myDepth < maxdepth and new_game.has_winner() == None :
            new_node.myChildren = generate_child_nodes(current_player.next(), new_game, current_depth+1, maxdepth, new_node, generateDescendents = False)
            
    return child_nodes



# Basic recursive minimax algorithm
def move_by_minimax(current_game, current_player, maxdepth): # Should we pass the game itself?
 
    best_move = None
    best_value = MIN_HEURISTIC_SCORE if (current_player == Player.Attacker) else MAX_HEURISTIC_SCORE
    
    
    ## Should we generate the tree as we go along instead?
    # Generate the game tree to the maxdepth.
    initial_children = generate_child_nodes(current_player, current_game, 0, maxdepth, generateDescendents = False) # Or should the current depth be one?
    
    #print("\nThe current player is {}\n".format(current_player))
    
    # If the current player is the attacker, start with min.
    if current_player == Player.Attacker:
        for child in initial_children:
            
            if (Options.alpha_beta == False):
                current_value = minimax(current_player.next(), child, maxdepth)
            else:
                current_value = minimax_pruning(current_player.next(), child, maxdepth, 0, MIN_HEURISTIC_SCORE, MAX_HEURISTIC_SCORE)   
                
            if current_value > best_value:
                best_value = current_value
                best_move = child.get_move()
                
    else: # Else, start with max. 
        for child in initial_children:
            
            if (Options.alpha_beta == False):
                current_value = minimax(current_player.next(), child, maxdepth)
            else:
                current_value = minimax_pruning(current_player.next(), child, maxdepth, 0, MIN_HEURISTIC_SCORE, MAX_HEURISTIC_SCORE)   
            
            if current_value < best_value: # Having the player check above instead of here repeats more code, but ensures we make fewer checks.
                best_value = current_value
                best_move = child.get_move()
    
    return best_value, best_move

    # To do: handle max time elapsed.


def minimax (current_player, current_node, maxdepth):
    
    # Attacker is max, defender is min.
    
    if (current_node.myDepth == maxdepth) or current_node.myGameConfiguration.has_winner() != None: # Have we reached the maximum depth?
        # I'm not sure I'm doing depth the right way. 
        # To do: also check whether the node leads in someone's victory?
        # Do we calculate the score here?
        current_node.score_me()
        return current_node.myScore
    
    current_node.myChildren = generate_child_nodes(current_player.next(), current_node.myGameConfiguration, current_node.myDepth+1, maxdepth, current_node, generateDescendents = False)
    
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


 # Implement optional alpha-beta pruning.
def minimax_pruning (current_player, current_node, maxdepth, current_depth, a, b):
    
    # Attacker is max, defender is min.    
    if (current_node.myDepth == maxdepth) or current_node.myGameConfiguration.has_winner() != None: # Have we reached the maximum depth?
        # I'm not sure I'm doing depth the right way. 
        # To do: also check whether the node leads in someone's victory?
        # Do we calculate the score here?
        current_node.score_me()
        return current_node.myScore
    
    current_node.myChildren = generate_child_nodes(current_player.next(), current_node.myGameConfiguration, current_node.myDepth+1, maxdepth, current_node, generateDescendents = False)
    
    if current_player == Player.Attacker: # Maximizing player
        best_value = MIN_HEURISTIC_SCORE
        
        for child in current_node.myChildren:
            #Implement alphabeta pruning.
            current_value = minimax_pruning(current_player.next(), child, maxdepth, current_depth+1, a, b)
            best_value = max(best_value, current_value)   
            a = max(a, best_value)
            if b <= a :
                break;
        return best_value
    
    else: # Minimizing player.
        best_value = MAX_HEURISTIC_SCORE
        
        for child in current_node.myChildren:
            #Implement alphabeta pruning.
            current_value = minimax_pruning(current_player.next(), child, maxdepth, current_depth+1, a, b)
            best_value = min(best_value, current_value)
            b = min(b, best_value)
            if b <= a:
                break;
        return best_value


# Heuristic function
def heuristic_score(current_game) -> int:
    
    # Score the given board configuration.# 

    # Demo heuristic
    if current_game.options.heuristic_function == HeurType.e0 : 
        
        vp1 = 0
        tp1 = 0
        fp1 = 0
        pp1 = 0
        aip1 = 0
        vp2 = 0
        tp2 = 0
        fp2 = 0
        pp2 = 0
        aip2 = 0
        
        for coords, unit in current_game.player_units(Player.Attacker):
            if unit.type == UnitType.Virus:
                vp1 += 1  
            elif unit.type == UnitType.Tech:
                tp1 += 1
            elif unit.type == UnitType.Firewall:
                fp1 += 1
            elif unit.type == UnitType.Program:
                pp1 += 1
            elif unit.type == UnitType.AI:
                aip1 += 1
        
        for coords, unit in current_game.player_units(Player.Defender):
            if unit.type == UnitType.Virus:
                vp2 += 1
            elif unit.type == UnitType.Tech:
                tp2 += 1
            elif unit.type == UnitType.Firewall:
                fp2 += 1
            elif unit.type == UnitType.Program:
                pp2 += 1
            elif unit.type == UnitType.AI:
                aip2 += 1         
        
        e0 = (3*vp1 + 3*tp1 + 3*fp1 + 3*pp1 + 9999*aip1) - (3*vp2 + 3*tp2 + 3*fp2 + 3*pp2 + 9999*aip2)
        return e0
    
    
    # Total health of one's units vs enemy's, weighted by unit type.
    elif current_game.options.heuristic_function  == HeurType.e1 :
        remaining_hp_attacker = 0
        remaining_hp_defender = 0
        
        for coords, unit in current_game.player_units(Player.Attacker):
            if unit.type == UnitType.Virus:
                remaining_hp_attacker += unit.health * 4.6
            elif unit.type == UnitType.Tech:
                remaining_hp_attacker += unit.health * 2
            elif unit.type == UnitType.Firewall:
                remaining_hp_attacker += unit.health * 1
            else: # AI or program
                remaining_hp_attacker += unit.health * 2.6
        
        current_game.player_units(Player.Defender)
        
        for coords, unit in current_game.player_units(Player.Defender):
            if unit.type == UnitType.Virus:
                remaining_hp_defender += unit.health * 4.6
            elif unit.type == UnitType.Tech:
                remaining_hp_defender += unit.health * 2
            elif unit.type == UnitType.Firewall:
                remaining_hp_defender += unit.health * 1
            else: # AI or program
                remaining_hp_defender += unit.health * 2.6
        
        e1 = (remaining_hp_attacker * 0.829 - remaining_hp_defender)
        # Scale attacker's score to even out the initial health difference. Let's see how that goes.
        
        # Winning is very good!
        if remaining_hp_attacker == 0:
            e1 = e1 - 9999
            
        elif remaining_hp_defender == 0:
            e1 = e1 + 9999
        
        return e1

    
    # Total health of one's units vs enemy's
    elif current_game.options.heuristic_function  == HeurType.e2 :
        
        total_units_attacker = 0
        total_units_defender = 0
        
        remaining_hp_attacker = 0
        remaining_hp_defender = 0
        
        for coords, unit in current_game.player_units(Player.Attacker):
            total_units_attacker += 1
            remaining_hp_attacker += unit.health
        
        for coords, unit in current_game.player_units(Player.Defender):
            total_units_defender += 1
            remaining_hp_defender += unit.health
        
        e2 = (remaining_hp_attacker - remaining_hp_defender)
        
        # Winning is very good!
        if remaining_hp_attacker == 0:
            e2 = e2 - 9999
        elif remaining_hp_defender == 0:
            e2 = e2 + 9999
        
        #print(e2)
        return e2
    


# Average AI damage: 2.6
# Average Virus damage: 4.6
# Average Tech damage: 2
# Average Firewall damage: 1
# Average Program damage: 2.6

# Initial for defender: 100.8
# Initial for attacker: 120.6