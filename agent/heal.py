import numpy as np
from scipy.ndimage import convolve

from .base import (
    log,
    Global,
    SPACE_SIZE,
    is_inside,
    manhattan_distance,
    get_spawn_location,
)
from .path import (
    DIRECTIONS,
    path_to_actions,
    get_reachable_nodes,
    find_closest_target,
    find_path_in_dynamic_environment,
)
from .space import NodeType
from .base import Task

REWARD_RADIUS = 4
REWARD_NUMBER_RELAXATION = 3
RELAXATION_KERNEL = np.array(
    [
        [0.00, 0.10, 0.11, 0.10, 0.00],
        [0.10, 0.11, 0.11, 0.11, 0.10],
        [0.11, 0.11, 0.11, 0.11, 0.11],
        [0.10, 0.11, 0.11, 0.11, 0.10],
        [0.00, 0.11, 0.11, 0.10, 0.00],
    ],
    dtype=np.float32,
)
BOUNDARY_PENALTY = [0.5, 0.8, 0.95]
ENERGY_MULTIPLIER = 0.25
BUNCHING_PENALTY = 2


class Heal(Task):

    def __init__(self, ship, target=None):
        super().__init__(target)
        self.ship = ship

    def __repr__(self):
        if self.target is None:
            return self.__class__.__name__
        else:
            return f"{self.__class__.__name__}{self.target.coordinates}"

    def completed(self, state, ship):
        return True

    @classmethod
    def generate_tasks(cls, state):
        return [Heal(ship) for ship in state.fleet]

    def evaluate(self, state, _):
        ship = self.ship

        opp_spawn_location = get_spawn_location(state.opp_team_id)
        opp_spawn_distance = manhattan_distance(opp_spawn_location, ship.coordinates)
        ship_energy = ship.energy

        p = Global.Params
        score = (
            p.HEAL_INIT_SCORE
            + opp_spawn_distance * p.HEAL_OPP_SPAWN_DISTANCE_MULTIPLIER
            + ship_energy * p.HEAL_SHIP_ENERGY_MULTIPLIER
        )

        return score

    def apply(self, state, _):
        target = self.find_target(state)
        if not target:
            return False

        ship = self.ship
        path = find_path_in_dynamic_environment(
            state,
            start=ship.coordinates,
            goal=target.coordinates,
            ship_energy=ship.energy,
        )
        if not path:
            return False

        self.target = target
        ship.action_queue = path_to_actions(path)
        return True

    def find_target(self, state):
        ship = self.ship

        score_map = estimate_gather_energy_score_map(state)

        for other_ship in state.fleet:
            if other_ship != ship and other_ship.task is not None:
                if other_ship.task.target is None:
                    log(
                        f"{other_ship} has task {other_ship.task} without target",
                        level=1,
                    )
                else:
                    add_bunching_penalty(score_map, other_ship.task.target.coordinates)

        available_nodes = get_reachable_nodes(state, ship.coordinates)
        targets = get_positions_with_max_energy(available_nodes, score_map)

        target, _ = find_closest_target(state, ship.coordinates, targets)
        if not target:
            return

        if not ship.can_move() and target != ship.coordinates:
            return

        return state.space.get_node(*target)


def get_positions_with_max_energy(nodes, score_map):
    position_to_score = {}
    for node in nodes:
        x, y = node.x, node.y
        position_to_score[(x, y)] = score_map[y][x]

    if not position_to_score:
        return []

    max_score = max(position_to_score.values())

    return [xy for xy, energy in position_to_score.items() if energy >= max_score - 0.5]


def add_bunching_penalty(score_map, position):
    for d in DIRECTIONS[:5]:
        x = position[0] + d[0]
        y = position[1] + d[1]
        if is_inside(x, y):
            score_map[y][x] -= BUNCHING_PENALTY


def estimate_gather_energy_score_map(state):

    reward_map = np.zeros(
        (SPACE_SIZE + 2 * REWARD_RADIUS, SPACE_SIZE + 2 * REWARD_RADIUS), np.int16
    )
    for node in state.space.reward_nodes:
        if node.reward:
            reward_map[node.y + REWARD_RADIUS][node.x + REWARD_RADIUS] = 1

    sub_shape = (REWARD_RADIUS * 2 + 1, REWARD_RADIUS * 2 + 1)
    view_shape = tuple(np.subtract(reward_map.shape, sub_shape) + 1) + sub_shape
    strides = reward_map.strides + reward_map.strides
    sub_matrices = np.lib.stride_tricks.as_strided(reward_map, view_shape, strides)
    score_map = sub_matrices.sum(axis=(2, 3), dtype=np.float32)

    score_map = score_map ** (1 / REWARD_NUMBER_RELAXATION)
    score_map = convolve(score_map, RELAXATION_KERNEL, mode="constant", cval=0)

    for i, x in enumerate(BOUNDARY_PENALTY):
        score_map[i, i : SPACE_SIZE - i] *= x
        score_map[SPACE_SIZE - 1 - i, i : SPACE_SIZE - i] *= x
        score_map[i : SPACE_SIZE - i, i] *= x
        score_map[i : SPACE_SIZE - i, SPACE_SIZE - 1 - i] *= x

    for node in state.space:
        if not node.is_walkable:
            score_map[node.y][node.x] = 0
            continue

        energy = node.energy
        if energy is None:
            continue

        if node.type == NodeType.nebula:
            energy -= Global.NEBULA_ENERGY_REDUCTION

        score_map[node.y][node.x] += energy * ENERGY_MULTIPLIER

    score_map[score_map < 0] = 0

    # map_str = "\n"
    # for y in range(SPACE_SIZE):
    #     s = []
    #     for x in range(SPACE_SIZE):
    #         s.append(f"{score_map[y][x]:.2f}")
    #     map_str += " ".join(s) + "\n"
    #
    # log(map_str)

    return score_map
