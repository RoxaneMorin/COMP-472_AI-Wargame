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
from ai_wargame_theActualAI import GameTreeNode
from copy import deepcopy


import random
from pip._vendor import requests

#
#Team members:
#- Roxane Morin, 40191881.
#- Duc Bui, 40061043.
#- Brianna Malpartida, 40045115.
#

@dataclass()
class Game:
    """Representation of the game state."""
    board: list[list[Unit | None]] = field(default_factory=list)
    next_player: Player = Player.Attacker
    turns_played : int = 0
    options: Options = field(default_factory=Options)
    stats: Stats = field(default_factory=Stats)
    _attacker_has_ai : bool = True
    _defender_has_ai : bool = True

    #create file to write output game trace
    file = open("gametrace-f-5-100.txt", 'w')

    def __post_init__(self):
        """Automatically called after class init to set up the default board state."""
        dim = self.options.dim
        self.board = [[None for _ in range(dim)] for _ in range(dim)]
        md = dim-1
        self.set(Coord(0,0),Unit(player=Player.Defender,type=UnitType.AI))
        self.set(Coord(1,0),Unit(player=Player.Defender,type=UnitType.Tech))
        self.set(Coord(0,1),Unit(player=Player.Defender,type=UnitType.Tech))
        self.set(Coord(2,0),Unit(player=Player.Defender,type=UnitType.Firewall))
        self.set(Coord(0,2),Unit(player=Player.Defender,type=UnitType.Firewall))
        self.set(Coord(1,1),Unit(player=Player.Defender,type=UnitType.Program))
        self.set(Coord(md,md),Unit(player=Player.Attacker,type=UnitType.AI))
        self.set(Coord(md-1,md),Unit(player=Player.Attacker,type=UnitType.Virus))
        self.set(Coord(md,md-1),Unit(player=Player.Attacker,type=UnitType.Virus))
        self.set(Coord(md-2,md),Unit(player=Player.Attacker,type=UnitType.Program))
        self.set(Coord(md,md-2),Unit(player=Player.Attacker,type=UnitType.Program))
        self.set(Coord(md-1,md-1),Unit(player=Player.Attacker,type=UnitType.Firewall))

    def clone(self) -> Game:
        # Make a new copy of a game for minimax recursion.
        # Shallow copy of everything except the board (options and stats are shared).
        new = copy.copy(self)
        new.board = copy.deepcopy(self.board)
        return new


    def is_empty(self, coord : Coord) -> bool:
        """Check if contents of a board cell of the game at Coord is empty (must be valid coord)."""
        return self.board[coord.row][coord.col] is None

    def get(self, coord : Coord) -> Unit | None:
        """Get contents of a board cell of the game at Coord."""
        if self.is_valid_coord(coord):
            return self.board[coord.row][coord.col]
        else:
            return None

    def set(self, coord : Coord, unit : Unit | None):
        """Set contents of a board cell of the game at Coord."""
        if self.is_valid_coord(coord):
            self.board[coord.row][coord.col] = unit

    def remove_dead(self, coord: Coord):
        """Remove unit at Coord if dead."""
        unit = self.get(coord)
        if unit is not None and not unit.is_alive():
            self.set(coord,None)
            if unit.type == UnitType.AI:
                if unit.player == Player.Attacker:
                    self._attacker_has_ai = False
                else:
                    self._defender_has_ai = False

    def mod_health(self, coord : Coord, health_delta : int):
        """Modify health of unit at Coord (positive or negative delta)."""
        target = self.get(coord)
        if target is not None:
            target.mod_health(health_delta)
            self.remove_dead(coord)
    
    
    def is_valid_move_preliminary(self, coords : CoordPair, wordy=True) -> bool:
        """Validate a move expressed as a CoordPair. Done by Roxane and Duc."""
        
        #print("coords in is_valid_move_preliminary: {}".format(coords))
        
        # Are the coords valid?
        if not self.is_valid_coord(coords.src) or not self.is_valid_coord(coords.dst):
            if wordy: print("These coordinates are not valid.")
            return False
        
        # Is the player targeting one of their units?
        unit = self.get(coords.src)
        if unit is None or unit.player != self.next_player:
            if wordy: print("This is not a unit belonging to the active player.")
            return False
        
        # Is the destination adjacent to the unit? 
        if not(coords.dst in coords.src.iter_adjacent()) and (coords.src != coords.dst):
            if wordy: print("This destination is not adjacent to the unit's current location.")
            return False
        
        return True
        
    
    def is_valid_move(self, coords : CoordPair, wordy=True) -> bool:
        """Validate a move expressed as a CoordPair. Done by Roxane."""
        # Is the destination free?
        # When it is not, interpret the movement as an attack or a heal.
        # Check for its own validity.
        target = self.get(coords.dst)
        if not(target is None):
            if wordy: print("The targeted desination is occupied.")
            return False
        #return (unit is None)
        
        # What are we? 
        # Techs and Viruses can always move in all directions.E2
        if (self.board[coords.src.row][coords.src.col].type == UnitType.Tech) or (self.board[coords.src.row][coords.src.col].type == UnitType.Virus):
            return True
        
        # Else,
        # AI, Firewall and Program units cannot move when an adversary unit is adjacent.
        for u in coords.src.iter_adjacent():
            #if wordy: print("Observing the tile {}".format(u))
            try: # There's likely a better way to do this, humm.
                if (self.board[coords.src.row][coords.src.col].player != self.board[u.row][u.col].player) and ('f' not in u.to_string()):
                    # Fixed the 'wrapping around', but it's pretty hacky. Should review in the future.
                    if wordy: print("This unit cannot move as it is engaged in combat.")
                    return False
            except: continue

        # The Attacker's Ai, Firewall and Program units can only move up or left.
        if (self.board[coords.src.row][coords.src.col].player == Player.Attacker and coords.src.col < coords.dst.col) or (self.board[coords.src.row][coords.src.col].player == Player.Attacker and coords.src.row < coords.dst.row):
            if wordy: print("Attacker's AI, Firewall and Program units can only move up or left.")
            return False
        
        # The Defender's Ai, Firewall and Programs can only move down or right.
        if (self.board[coords.src.row][coords.src.col].player == Player.Defender and coords.src.col > coords.dst.col) or (self.board[coords.src.row][coords.src.col].player == Player.Defender and coords.src.row > coords.dst.row):
            if wordy: print("Defender's AI, Firewall and Program units can only move down or right.")
            return False
        
        # All clear!
        return True

    def is_valid_attack(self, coords : CoordPair, wordy=True) -> bool :
        """Validate an attack expressed as a CoordPair. Done by Duc"""
        #verify that coordinates are occupied by enemies / not the same player
        target = self.get(coords.dst)
        if target is None or target.player == self.next_player:
            if wordy: print("The target is not a valid unit to attack.")
            return False
        
        return True
    
    def is_valid_repair(self, coords : CoordPair, wordy=True) -> bool :
        """Validate a repair expressed as a CoordPair. Done by Duc"""
        #verify that coordinates belongs to player
        target = self.get(coords.dst)
        if target is None or target.player != self.next_player:
            if wordy: print("The target is not a valid unit to repair.")
            return False
        
        #verify that repair would heal, so only AI -> Virus or Tech & Tech -> AI, Firewall, or Program
        unit = self.get(coords.src)
        ai = UnitType.AI
        firewall = UnitType.Firewall
        program = UnitType.Program
        tech = UnitType.Tech
        virus = UnitType.Virus
        if not(unit.type == ai and (target.type == virus or target.type == tech)) and not(unit.type == tech and (target.type == ai or target.type == firewall or target.type == program)):
            if wordy: print("The repairing unit or repaired unit is of the wrong type of unit.")
            return False
        
        #verify that repair target is not at max health
        if target.health == 9:
            if wordy: print("This unit does not need to be repaired.")
            return False    

        return True
    
    def is_valid_move_any(self, coords : CoordPair, wordy=False) -> bool :
        # The premilinary checks are not actually needed here.
        
        # Hacky way to filter out the invalid coords that get generated.
        if ('Z' in coords.to_string()) or ('f' in coords.to_string()):
            return False
        
        # Check using our various is_valid_x functions.
        if self.is_valid_move(coords, wordy) or self.is_valid_attack(coords, wordy) or self.is_valid_repair(coords, wordy):
            return True
        # Else, check for self destructuon.
        elif (coords.src == coords.dst):
            return True
        
        # Else, return false.
        return False
    
    def perform_move(self, coords : CoordPair, wordy=True) -> Tuple[bool,str]:
        """Validate and perform a move expressed as a CoordPair. Written by Duc and Roxane."""

        #Preliminary checks used by all actions.
        if self.is_valid_move_preliminary(coords):
            
            if wordy: print("") # Skip a line.
            
            #perform move action
            if self.is_valid_move(coords):
                self.set(coords.dst,self.get(coords.src))
                self.set(coords.src,None)
                if wordy: self.file.write("\n\nMove Played: " + str(coords.src) + " " + str(coords.dst))
                self.clone()  #clone the board

                return (True,"Move successful ({}).".format(coords.to_string()))
            
            #perform attack actione2 e1

            elif self.is_valid_attack(coords):        
                attacker = self.get(coords.src)
                defender = self.get(coords.dst)
                
                #reduce attacker & defender HP by damage table 
                a_to_d = attacker.damage_amount(defender)
                d_to_a = defender.damage_amount(attacker)
                
                #fix attacker & defender HP
                self.mod_health(coords.src, -d_to_a)
                self.mod_health(coords.dst, -a_to_d)
                if wordy: self.file.write("\n\nMove Played: " + str(coords.src) + " " + str(coords.dst))
                return (True,"Attack successful ({}).".format(coords.to_string()))
            
            #perform repair action
            elif self.is_valid_repair(coords):      
                healer = self.get(coords.src)
                target = self.get(coords.dst)
                
                #repair target HP by repair table
                heal_amount = healer.repair_amount(target)
                
                #fix target HP
                target.mod_health(+heal_amount)
                if wordy: self.file.write("\n\nMove Played: " + str(coords.src) + " " + str(coords.dst))
                return (True,"Repair successful ({}).".format(coords.to_string()))
            
            # perform self destruct
            elif (coords.src == coords.dst):
                self.mod_health(coords.dst, -9)
                for u in coords.src.iter_adjacent_diags():
                    try:
                        self.mod_health(u, -2)
                    except: continue
                return (True,"The targeted unit has self destructed ({}).".format(coords.to_string()))
        
        return (False,"Invalid move")

    def next_turn(self):
        """Transitions game to the next turn."""
        self.next_player = self.next_player.next()
        self.turns_played += 1

    def write_to_file(self,output):
        if self.is_finished():
            with open('gametrace-f-5-100.txt', 'a') as file:  
                winner = self.has_winner()
                if winner:
                    file.write(winner.name + " wins in " + str(self.turns_played) + " moves!")
                else:
                    file.write("The game ended in a draw after " + str(self.turns_played) + " moves.")
                file.flush()
        else:
            with open('gametrace-f-5-100.txt', 'a') as file: 
                if self.turns_played == 0:
                    file.write("Initial Board Configuration: \n\n" + output)
                else:
                    file.write("\nCurrent Board Information: \n\n" + output)
                file.flush()
        

    def to_string(self) -> str:
        """Pretty text representation of the game."""
        dim = self.options.dim
        output = ""
        output += f"Next player: {self.next_player.name}\n"
        output += f"Turns played: {self.turns_played}\n"
        output += f"Remaining turns: {self.options.max_turns - self.turns_played}\n"
        coord = Coord()
        output += "\n   "
        for col in range(dim):
            coord.col = col
            label = coord.col_string()
            output += f"{label:^3} "
        output += "\n"
        for row in range(dim):
            coord.row = row
            label = coord.row_string()
            output += f"{label}: "
            for col in range(dim):
                coord.col = col
                unit = self.get(coord)
                if unit is None:
                    output += " .  "
                else:
                    output += f"{str(unit):^3} "
            output += "\n"
        self.write_to_file(output)
        return output

    def __str__(self) -> str:
        """Default string representation of a game."""
        return self.to_string()
    
    def is_valid_coord(self, coord: Coord) -> bool:
        """Check if a Coord is valid within out board dimensions."""
        dim = self.options.dim
        if coord.row < 0 or coord.row >= dim or coord.col < 0 or coord.col >= dim:
            return False
        return True

    def read_move(self) -> CoordPair:
        """Read a move from keyboard and return as a CoordPair."""
        while True:
            s = input(F'Player {self.next_player.name}, enter your move: ')
            coords = CoordPair.from_string(s)
            if coords is not None and self.is_valid_coord(coords.src) and self.is_valid_coord(coords.dst):
                return coords
            else:
                print('Invalid coordinates! Try again.')
    
    def human_turn(self, wordy=True):
        """Human player plays a move (or get via broker)."""
        if self.options.broker is not None:
            if wordy: print("Getting next move with auto-retry from game broker...")
            while True:
                mv = self.get_move_from_broker()
                if mv is not None:
                    (success,result) = self.perform_move(mv)
                    if wordy: 
                        print(f"Broker {self.next_player.name}: ",end='')
                        print(result)
                    if success:
                        self.next_turn()
                        break
                sleep(0.1)
        else:
            while True:
                mv = self.read_move()
                (success,result) = self.perform_move(mv)
                if success:
                    if wordy: 
                        print(f"Player {self.next_player.name}: ",end='')
                        print(result)
                    self.next_turn()
                    break
                else:
                    print("The move is not valid! Try again.")

    def computer_turn(self, wordy=True) -> CoordPair | None:
        """Computer plays a move."""
        mv = self.suggest_move()
        if mv is not None:
            (success,result) = self.perform_move(mv)
            if success:
                if wordy: 
                    print(f"Computer {self.next_player.name}: ",end='')
                    print(result)
                self.next_turn()
        return mv

    def player_units(self, player: Player) -> Iterable[Tuple[Coord,Unit]]:
        """Iterates over all units belonging to a player."""
        for coord in CoordPair.from_dim(self.options.dim).iter_rectangle():
            unit = self.get(coord)
            if unit is not None and unit.player == player:
                yield (coord,unit)

    def is_finished(self) -> bool:
        """Check if the game is over."""
        return self.has_winner() is not None
    
    def has_winner(self) -> Player | None:
        """Check if the game is over and returns winner"""
        remaining_attacker = sum(1 for _ in self.player_units(Player.Attacker))
        remaining_defender = sum(1 for _ in self.player_units(Player.Defender))
        
        #print("Remaining attacker units: {}".format(remaining_attacker))
        #print("Remaining defender units: {}".format(remaining_defender))
        
        if remaining_attacker == 0:
            #print("No attacker units left.")
            return Player.Defender
        elif remaining_defender == 0:
            #print("No deffender units left.")
            return Player.Attacker
        
        #print("Remaining turns: {}".format(self.options.max_turns - self.turns_played))
        
        if self.options.max_turns is not None and self.turns_played >= self.options.max_turns:
            # If the game runs out of turns, whoever has the most units remaining wins.
            #print("The max number of turns has been reached.")
            if (remaining_attacker > remaining_defender): 
                #print("The attacker has more remaining units.")
                return Player.Attacker
            # Ties go to the defender.
            else:
                #print("The defender is still holding strong.")
                return Player.Defender

        #if self._attacker_has_ai:
        #    if self._defender_has_ai:
        #        return None
        #    else:
        #        return Player.Attacker    
        
        # Else, no victor yet. Return None.
        return None

    def move_candidates(self) -> Iterable[CoordPair]:
        """Generate valid move candidates for the next player."""
        move = CoordPair()
        for (src,_) in self.player_units(self.next_player):
            move.src = src
            for dst in src.iter_adjacent():
                move.dst = dst
                if self.is_valid_move_any(move, wordy=False): # Should do for integrating our stuff.
                    yield move.clone()
            move.dst = src
            yield move.clone()

    def random_move(self) -> Tuple[int, CoordPair | None, float]:
        """Returns a random move."""
        move_candidates = list(self.move_candidates())
        random.shuffle(move_candidates)
        if len(move_candidates) > 0:
            return (0, move_candidates[0], 1)
        else:
            return (0, None, 0)

    def suggest_move(self) -> CoordPair | None:
        """Suggest the next move using minimax alpha beta. TODO: REPLACE RANDOM_MOVE WITH PROPER GAME LOGIC!!!"""
        start_time = datetime.now()
        
        ## Line where we replace the random move.
        #(score, move, avg_depth) = self.random_move()
        (score, move) = ai_wargame_theActualAI.move_by_minimax(self.clone(), self.next_player, self.options.max_depth)
        
        
        elapsed_seconds = (datetime.now() - start_time).total_seconds()
        self.stats.total_seconds += elapsed_seconds
        
        print(f"Heuristic score: {score}")
        #print(f"Average recursive depth: {avg_depth:0.1f}")
        print(f"Evals per depth: ",end='')
        
        for k in sorted(self.stats.evaluations_per_depth.keys()):
            print(f"{k}:{self.stats.evaluations_per_depth[k]} ",end='')
        print()
        
        total_evals = sum(self.stats.evaluations_per_depth.values())
        
        if self.stats.total_seconds > 0:
            print(f"Eval perf.: {total_evals/self.stats.total_seconds/1000:0.1f}k/s")
            
        print(f"Elapsed time: {elapsed_seconds:0.1f}s")
        return move

    def post_move_to_broker(self, move: CoordPair):
        """Send a move to the game broker."""
        if self.options.broker is None:
            return
        data = {
            "from": {"row": move.src.row, "col": move.src.col},
            "to": {"row": move.dst.row, "col": move.dst.col},
            "turn": self.turns_played
        }
        try:
            r = requests.post(self.options.broker, json=data)
            if r.status_code == 200 and r.json()['success'] and r.json()['data'] == data:
                # print(f"Sent move to broker: {move}")
                pass
            else:
                print(f"Broker error: status code: {r.status_code}, response: {r.json()}")
        except Exception as error:
            print(f"Broker error: {error}")

    def get_move_from_broker(self) -> CoordPair | None:
        """Get a move from the game broker."""
        if self.options.broker is None:
            return None
        headers = {'Accept': 'application/json'}
        try:
            r = requests.get(self.options.broker, headers=headers)
            if r.status_code == 200 and r.json()['success']:
                data = r.json()['data']
                if data is not None:
                    if data['turn'] == self.turns_played+1:
                        move = CoordPair(
                            Coord(data['from']['row'],data['from']['col']),
                            Coord(data['to']['row'],data['to']['col'])
                        )
                        print(f"Got move from broker: {move}")
                        return move
                    else:
                        # print("Got broker data for wrong turn.")
                        # print(f"Wanted {self.turns_played+1}, got {data['turn']}")
                        pass
                else:
                    # print("Got no data from broker")
                    pass
            else:
                print(f"Broker error: status code: {r.status_code}, response: {r.json()}")
        except Exception as error:
            print(f"Broker error: {error}")
        return None
    

##############################################################################################################

def main():
    # parse command line arguments
    parser = argparse.ArgumentParser(
        prog='ai_wargame',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--max_depth', type=int, help='maximum search depth')
    parser.add_argument('--max_time', type=float, help='maximum search time')
    parser.add_argument('--game_type', type=str, default="manual", help='game type: auto|attacker|defender|manual')
    parser.add_argument('--broker', type=str, help='play via a game broker')
    parser.add_argument('--heuristic_function', type=str, default="e0", help='heuristic functions: e0|e1|e2')
    args = parser.parse_args()

    # parse the game type
    if args.game_type == "attacker":
        game_type = GameType.AttackerVsComp
    elif args.game_type == "defender":
        game_type = GameType.CompVsDefender
    elif args.game_type == "manual":
        game_type = GameType.AttackerVsDefender
    else:
        game_type = GameType.CompVsComp
        
    # parse the heuristic function
    if args.heuristic_function == "e0" : 
        heuristic_function = HeurType.e0
    elif args.heuristic_function == "e1" :
        heuristic_function = HeurType.e1
    elif args.heuristic_function == "e2" :
        heuristic_function = HeurType.e2

    # set up game options
    options = Options(game_type=game_type, heuristic_function=heuristic_function)

    # override class defaults via command line options
    if args.max_depth is not None:
        options.max_depth = args.max_depth
    if args.max_time is not None:
        options.max_time = args.max_time
    if args.broker is not None:
        options.broker = args.broker

    # create a new game
    game = Game(options=options)

    # the main game loop
    while True:
        print()
        print(game)
        winner = game.has_winner()
        if winner is not None:
            print(f"{winner.name} wins!")
            break
        if game.options.game_type == GameType.AttackerVsDefender:
            game.human_turn()
        elif game.options.game_type == GameType.AttackerVsComp and game.next_player == Player.Attacker:
            game.human_turn()
        elif game.options.game_type == GameType.CompVsDefender and game.next_player == Player.Defender:
            game.human_turn()
        else:
            player = game.next_player # Not sure this is actually being used.
            move = game.computer_turn()
            if move is not None:
                game.post_move_to_broker(move)
            else:
                print("Computer doesn't know what to do!!!")
                exit(1)


##############################################################################################################

if __name__ == '__main__':
    main()