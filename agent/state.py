import copy
import numpy as np
from sys import stderr as err
from collections import defaultdict
from pathfinding.visualization import animate_grid

from .base import Params, get_spawn_location, chebyshev_distance
from .path import ActionType, PathFinder
from .space import Space, NodeType
from .fleet import Fleet


class Colors:
    red = "\033[91m"
    blue = "\033[94m"
    yellow = "\033[93m"
    green = "\033[92m"
    endc = "\033[0m"


class State:
    def __init__(self, team_id):
        self.team_id = team_id
        self.global_step = 0  # global step of the game
        self.match_step = 0  # current step in the match
        self.match_number = 0  # current match number

        self.space = Space()
        self.fleet = Fleet(team_id)
        self.opp_fleet = Fleet(1 - team_id)

        self._obstacles_movement_status = []

    def update(self, obs):
        if obs["steps"] > 0:
            self._update_step_counters()

        assert obs["steps"] == self.global_step
        assert obs["match_steps"] == self.match_step

        if self.match_step == 0:
            self.fleet.clear()
            self.opp_fleet.clear()
            self.space.clear()
            self.space.move_obstacles(self.global_step)
            return

        points = int(obs["team_points"][self.team_id])
        reward = max(0, points - self.fleet.points)

        self.space.update(self.global_step, obs, team_to_reward={self.team_id: reward})
        self.fleet.update(obs, self.space)
        self.opp_fleet.update(obs, self.space)

        if (
            Params.OBSTACLE_MOVEMENT_PERIOD == 0
            or (self.global_step - 1) % Params.OBSTACLE_MOVEMENT_PERIOD != 0
        ):
            self.space.update_nodes_by_expected_sensor_mask(
                self.fleet.expected_sensor_mask()
            )

    def _update_step_counters(self):
        self.global_step += 1
        self.match_step += 1
        if self.match_step > Params.MAX_STEPS_IN_MATCH:
            self.match_step = 0
            self.match_number += 1

    def steps_left_in_match(self) -> int:
        return Params.MAX_STEPS_IN_MATCH - self.match_step

    def copy(self) -> "State":
        return copy.deepcopy(self)

    def create_actions_array(self):
        ships = self.fleet.ships
        actions = np.zeros((len(ships), 3), dtype=int)

        spawn_pointer = self._get_spawn_pointer()
        if spawn_pointer:
            actions[:] = (ActionType.sap, *spawn_pointer)

        for i, ship in enumerate(ships):
            if ship.node is not None:
                actions[i][0] = ActionType.center

            if ship.action_queue:
                a = ship.action_queue[0]
                actions[i] = (a.type.value, a.dx, a.dy)

        return actions

    def _get_spawn_pointer(self):
        spawn_location = get_spawn_location(self.team_id)
        target = None
        min_distance = 0
        for ship in self.fleet:
            next_position = ship.next_position()

            if next_position == spawn_location:
                continue

            distance = chebyshev_distance(spawn_location, next_position)
            if distance > Params.UNIT_SAP_RANGE:
                continue

            if target is None or min_distance > distance:
                min_distance = distance
                target = next_position

        if target:
            return target[0] - spawn_location[0], target[1] - spawn_location[1]

    def show_visible_map(self):
        print("Visible map:", file=err)
        show_map(self.space, self.fleet, self.opp_fleet)

    def show_visible_energy_field(self):
        print("Visible energy field:", file=err)
        show_energy_field(self.space)

    def show_explored_map(self):
        print("Explored map:", file=err)
        show_map(self.space, self.fleet, self.opp_fleet, only_visible=False)

    def show_explored_energy_field(self):
        print("Explored energy field:", file=err)
        show_energy_field(self.space, only_visible=False)

    def show_exploration_info(self):
        print("Exploration info:", file=err)
        show_exploration_info(self.space)

    def show_tasks(self):
        print("Tasks:", file=err)
        for ship in self.fleet:
            print(f" - {ship} : {ship.task}", file=err)

    def to_animation(self, file_name=None):
        if not file_name:
            file_name = f"step_{self.global_step}.mp4"
        finder = PathFinder(self)
        agents = []
        for ship in self.fleet:
            agents.append(
                {"id": ship.unit_id, "start": ship.coordinates, "path": ship.path()}
            )

        anim = animate_grid(
            finder.grid_without_obstacles,
            agents=agents,
            reservation_table=finder.reservation_table,
            show_weights=True,
            size=8,
        )
        anim.save(file_name)


def show_map(space, my_fleet=None, opp_fleet=None, only_visible=True):
    ship_signs = (
        [" "] + [str(x) for x in range(1, 10)] + ["A", "B", "C", "D", "E", "F", "H"]
    )

    my_ships = defaultdict(int)
    for ship in my_fleet or []:
        my_ships[ship.node.coordinates] += 1

    opp_ships = defaultdict(int)
    for ship in opp_fleet or []:
        opp_ships[ship.node.coordinates] += 1

    line = " + " + " ".join([f"{x:>2}" for x in range(Params.SPACE_SIZE)]) + "  +\n"
    str_grid = line
    for y in range(Params.SPACE_SIZE):

        str_row = []

        for x in range(Params.SPACE_SIZE):
            node = space.get_node(x, y)

            if node.type == NodeType.unknown or (only_visible and not node.is_visible):
                str_row.append("..")
                continue

            if node.type == NodeType.nebula:
                s1 = "ñ" if node.relic else "n"
            elif node.type == NodeType.asteroid:
                s1 = "ã" if node.relic else "a"
            else:
                s1 = "~" if node.relic else " "

            if node.reward:
                if s1 == " ":
                    s1 = "_"
                s1 = f"{Colors.yellow}{s1}{Colors.endc}"

            if node.coordinates in my_ships:
                num_ships = my_ships[node.coordinates]
                s2 = f"{Colors.blue}{ship_signs[num_ships]}{Colors.endc}"
            elif node.coordinates in opp_ships:
                num_ships = opp_ships[node.coordinates]
                s2 = f"{Colors.red}{ship_signs[num_ships]}{Colors.endc}"
            else:
                s2 = " "

            str_row.append(s1 + s2)

        str_grid += " ".join([f"{y:>2}", *str_row, f"{y:>2}", "\n"])

    str_grid += line
    print(str_grid, file=err)


def show_energy_field(space, only_visible=True):
    def add_color(i):
        color = Colors.green if i > 0 else Colors.red
        return f"{color}{i:>3}{Colors.endc}"

    line = " + " + " ".join([f"{x:>2}" for x in range(Params.SPACE_SIZE)]) + "  +\n"
    str_grid = line
    for y in range(Params.SPACE_SIZE):

        str_row = []

        for x in range(Params.SPACE_SIZE):
            node = space.get_node(x, y)
            if node.energy is None or (only_visible and not node.is_visible):
                str_row.append(" ..")
            else:
                str_row.append(add_color(node.energy))

        str_grid += "".join([f"{y:>2}", *str_row, f" {y:>2}", "\n"])

    str_grid += line
    print(str_grid, file=err)


def show_exploration_info(space):
    print(
        f"all relics found: {Params.ALL_RELICS_FOUND}, "
        f"all rewards found: {Params.ALL_REWARDS_FOUND}",
        file=err,
    )

    line = " + " + " ".join([f"{x:>2}" for x in range(Params.SPACE_SIZE)]) + "  +\n"
    str_grid = line
    for y in range(Params.SPACE_SIZE):

        str_row = []

        for x in range(Params.SPACE_SIZE):
            node = space.get_node(x, y)
            if not node.explored_for_relic:
                s1 = "."
            else:
                s1 = "R" if node.relic else " "

            if not node.explored_for_reward:
                s2 = "."
            else:
                s2 = "P" if node.reward else " "

            str_row.append(s1 + s2)

        str_grid += " ".join([f"{y:>2}", *str_row, f"{y:>2}", "\n"])

    str_grid += line
    print(str_grid, file=err)
