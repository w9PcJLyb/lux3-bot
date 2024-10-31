import numpy as np
from copy import deepcopy
from sys import stderr as err
from enum import IntEnum

from .base import Params, SPACE_SIZE, get_opposite, warp_point


class NodeType(IntEnum):
    unknown = -1
    empty = 0
    nebula = 1
    asteroid = 2

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


class Node:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.type = NodeType.unknown
        self.energy = None
        self.is_visible = False

        self._relic = False
        self._reward = False
        self._explored_for_relic = False
        self._explored_for_reward = False

    def __repr__(self):
        return f"Node({self.x}, {self.y}, {self.type})"

    def __hash__(self):
        return self.coordinates.__hash__()

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    @property
    def relic(self):
        return self._relic

    @property
    def reward(self):
        return self._reward

    @property
    def explored_for_relic(self):
        return self._explored_for_relic

    @property
    def explored_for_reward(self):
        return self._explored_for_reward

    def update_relic_status(self, status: bool):
        if self._explored_for_relic and self._relic != status:
            raise ValueError(
                f"Can't change the relic status for {self}"
                ", the tile has already been explored"
            )

        self._relic = status
        self._explored_for_relic = True

    def update_reward_status(self, status: bool):
        if self._explored_for_reward and self._reward != status:
            raise ValueError(
                f"Can't change the reward status for {self}"
                ", the tile has already been explored"
            )

        self._reward = status
        self._explored_for_reward = True

    @property
    def is_unknown(self) -> bool:
        return self.type == NodeType.unknown

    @property
    def is_walkable(self) -> bool:
        return self.type != NodeType.asteroid

    @property
    def coordinates(self) -> tuple[int, int]:
        return self.x, self.y

    def manhattan_distance(self, other: "Node") -> int:
        return abs(self.x - other.x) + abs(self.y - other.y)


class Space:
    def __init__(self):
        self._nodes: list[list[Node]] = []
        for y in range(SPACE_SIZE):
            row = [Node(x, y) for x in range(SPACE_SIZE)]
            self._nodes.append(row)

        self._relic_id_to_node = {}
        self._relic_nodes: set[Node] = set()
        self._reward_nodes: set[Node] = set()
        self._reward_results = []
        self._obstacles_movement_status = []

    def __repr__(self) -> str:
        return f"Space({SPACE_SIZE}x{SPACE_SIZE})"

    def __iter__(self):
        for row in self._nodes:
            yield from row

    def get_node(self, x, y) -> Node:
        return self._nodes[y][x]

    def get_node_energy(self, x, y) -> int:
        return self._nodes[y][x].energy

    def get_node_type(self, x, y) -> NodeType:
        return self._nodes[y][x].type

    def get_opposite_node(self, x, y) -> Node:
        return self.get_node(*get_opposite(x, y))

    def update(self, global_step, obs, team_to_reward=None):
        self.move_obstacles(global_step)
        self._update_map(obs)

        for relic_id, (mask, xy) in enumerate(
            zip(obs["relic_nodes_mask"], obs["relic_nodes"])
        ):
            if mask:
                self._update_relic_status(*xy, status=True)
                self._relic_id_to_node[relic_id] = self.get_node(*xy)

        all_relics_found = True
        all_rewards_found = True
        for node in self:
            if node.is_visible and not node.explored_for_relic:
                self._update_relic_status(*node.coordinates, status=False)

            if not node.explored_for_relic:
                all_relics_found = False

            if not node.explored_for_reward:
                all_rewards_found = False

        Params.ALL_RELICS_FOUND = all_relics_found
        Params.ALL_REWARDS_FOUND = all_rewards_found

        if not Params.ALL_RELICS_FOUND:
            if self.num_relics_found == len(obs["relic_nodes_mask"]):
                # all relics found, mark all nodes as explored for relics
                Params.ALL_RELICS_FOUND = True
                for node in self:
                    if not node.explored_for_relic:
                        self._update_relic_status(*node.coordinates, status=False)

        if not Params.ALL_REWARDS_FOUND:
            self._update_reward_status_from_relics_distribution()

            if team_to_reward:
                self._update_reward_results(obs, team_to_reward)

            self._update_reward_status_from_reward_results()

    def _update_map(self, obs):
        sensor_mask = obs["sensor_mask"]
        obs_energy = obs["map_features"]["energy"]
        obs_tile_type = obs["map_features"]["tile_type"]

        obstacles_shifted = False
        energy_nodes_shifted = False
        for node in self:
            x, y = node.coordinates
            is_visible = sensor_mask[x, y]

            if (
                is_visible
                and not node.is_unknown
                and node.type.value != obs_tile_type[x, y]
            ):
                obstacles_shifted = True

            if (
                is_visible
                and node.energy is not None
                and node.energy != obs_energy[x, y]
            ):
                energy_nodes_shifted = True

        # print(
        #     f"obstacles_shifted = {obstacles_shifted}, energy_nodes_shifted = {energy_nodes_shifted}",
        #     file=err,
        # )

        self._obstacles_movement_status.append(obstacles_shifted)
        if not Params.OBSTACLE_MOVEMENT_PERIOD_FOUND:
            period = _get_obstacle_movement_period(self._obstacles_movement_status)
            if period is not None:
                Params.OBSTACLE_MOVEMENT_PERIOD_FOUND = True
                Params.OBSTACLE_MOVEMENT_PERIOD = period
                print(
                    f"Find param OBSTACLE_MOVEMENT_PERIOD = {period}",
                    file=err,
                )

        if not Params.OBSTACLE_MOVEMENT_DIRECTION_FOUND and obstacles_shifted:
            direction = _get_obstacle_movement_direction(self, obs)
            if direction:
                Params.OBSTACLE_MOVEMENT_DIRECTION_FOUND = True
                Params.OBSTACLE_MOVEMENT_DIRECTION = direction
                print(
                    f"Find param OBSTACLE_MOVEMENT_DIRECTION = {direction}",
                    file=err,
                )

                self.move(*Params.OBSTACLE_MOVEMENT_DIRECTION, inplace=True)
                obstacles_shifted = False
            else:
                print("WARNING: Can't find OBSTACLE_MOVEMENT_DIRECTION", file=err)
                for node in self:
                    node.type = NodeType.unknown

        if (
            obstacles_shifted
            and Params.OBSTACLE_MOVEMENT_PERIOD_FOUND
            and Params.OBSTACLE_MOVEMENT_DIRECTION_FOUND
        ):
            print("WARNING: OBSTACLE_MOVEMENTS params are incorrect", file=err)
            for node in self:
                node.type = NodeType.unknown

        for node in self:
            x, y = node.coordinates
            is_visible = bool(sensor_mask[x, y])

            node.is_visible = is_visible

            if is_visible:
                node.energy = int(obs_energy[x, y])
            elif energy_nodes_shifted:
                node.energy = None

            if is_visible and node.is_unknown:
                node.type = NodeType(int(obs_tile_type[x, y]))
                self.get_opposite_node(x, y).type = node.type

    def move_obstacles(self, global_step):
        if (
            Params.OBSTACLE_MOVEMENT_PERIOD_FOUND
            and Params.OBSTACLE_MOVEMENT_DIRECTION_FOUND
            and Params.OBSTACLE_MOVEMENT_PERIOD > 0
            and (global_step - 1) % Params.OBSTACLE_MOVEMENT_PERIOD == 0
        ):
            self.move(*Params.OBSTACLE_MOVEMENT_DIRECTION, inplace=True)

    def _update_reward_status_from_relics_distribution(self):
        r = Params.RELIC_REWARD_RANGE
        relic_map = np.zeros((SPACE_SIZE + 2 * r, SPACE_SIZE + 2 * r), np.int16)
        for node in self:
            if node.relic or not node.explored_for_relic:
                relic_map[node.y + r][node.x + r] = 1

        sub_shape = (r * 2 + 1, r * 2 + 1)
        view_shape = tuple(np.subtract(relic_map.shape, sub_shape) + 1) + sub_shape
        strides = relic_map.strides + relic_map.strides
        sub_matrices = np.lib.stride_tricks.as_strided(relic_map, view_shape, strides)
        reward_map = sub_matrices.sum(axis=(2, 3))

        for node in self:
            if reward_map[node.y][node.x] == 0:
                # no relics in range RELIC_REWARD_RANGE
                node.update_reward_status(False)

    def _update_reward_results(self, obs, team_to_reward):
        for team_id, team_reward in team_to_reward.items():
            ship_nodes = set()
            for active, position in zip(
                obs["units_mask"][team_id], obs["units"]["position"][team_id]
            ):
                if active:
                    ship_nodes.add(self.get_node(*position))

            if not ship_nodes:
                continue

            self._reward_results.append({"nodes": ship_nodes, "reward": team_reward})
        # print(self._reward_results, file=err)

    def _update_reward_status_from_reward_results(self):
        filtered_results = []
        for result in self._reward_results:
            if result["reward"] == 0:
                for node in result["nodes"]:
                    self._update_reward_status(*node.coordinates, status=False)
                continue

            nodes = set()
            known_reward = 0
            for n in result["nodes"]:
                if n.explored_for_reward and not n.reward:
                    continue

                if n.reward:
                    known_reward += 1
                    continue

                nodes.add(n)

            if not nodes:
                continue

            reward = result["reward"] - known_reward

            if reward == 0:
                for node in nodes:
                    self._update_reward_status(*node.coordinates, status=False)
                continue

            if reward == len(nodes):
                for node in nodes:
                    self._update_reward_status(*node.coordinates, status=True)
                continue

            if reward > len(nodes):
                print(
                    f"WARNING! Something wrong with reward result: {result}"
                    ", this result will be ignored.",
                    file=err,
                )
                continue

            filtered_results.append({"nodes": nodes, "reward": reward})

        self._reward_results = filtered_results

    def _update_relic_status(self, x, y, status):
        node = self.get_node(x, y)
        node.update_relic_status(status)

        opp_node = self.get_opposite_node(x, y)
        opp_node.update_relic_status(status)

        if status:
            self._relic_nodes.add(node)
            self._relic_nodes.add(opp_node)

    def _update_reward_status(self, x, y, status):
        node = self.get_node(x, y)
        node.update_reward_status(status)

        opp_node = self.get_opposite_node(x, y)
        opp_node.update_reward_status(status)

        if status:
            self._reward_nodes.add(node)
            self._reward_nodes.add(opp_node)

    @property
    def num_relics_found(self) -> int:
        return len(self._relic_nodes)

    @property
    def relic_nodes(self) -> set[Node]:
        return self._relic_nodes

    @property
    def reward_nodes(self) -> set[Node]:
        return self._reward_nodes

    def clear(self):
        for node in self:
            node.is_visible = False

    def update_nodes_by_expected_sensor_mask(self, expected_sensor_mask):
        for y in range(SPACE_SIZE):
            for x in range(SPACE_SIZE):
                if expected_sensor_mask[y][x] == 1 and self.get_node(x, y).is_unknown:
                    self.get_node(x, y).type = NodeType.nebula

    def is_walkable(self, x, y):
        return self.get_node(x, y).is_walkable

    def move(self, dx: int, dy: int, *, inplace=False) -> "Space":
        if not inplace:
            new_space = deepcopy(self)
            for node in self:
                x, y = warp_point(node.x + dx, node.y + dy)
                new_space.get_node(x, y).type = node.type
            return new_space
        else:
            types = [n.type for n in self]
            for node, node_type in zip(self, types):
                x, y = warp_point(node.x + dx, node.y + dy)
                self.get_node(x, y).type = node_type
            return self


def _get_obstacle_movement_direction(space, obs):
    sensor_mask = obs["sensor_mask"]
    obs_tile_type = obs["map_features"]["tile_type"]

    suitable_directions = []
    for direction in [(1, -1), (-1, 1)]:
        moved_space = space.move(*direction, inplace=False)

        match = True
        for node in moved_space:
            x, y = node.coordinates
            if (
                sensor_mask[x, y]
                and not node.is_unknown
                and obs_tile_type[x, y] != node.type.value
            ):
                match = False
                break

        if match:
            suitable_directions.append(direction)

    if len(suitable_directions) == 1:
        return suitable_directions[0]


def _get_obstacle_movement_period(obstacles_movement_status):
    if not obstacles_movement_status:
        return

    if obstacles_movement_status[-1] is True:
        if len(obstacles_movement_status) - 21 % 40 < 20:
            return 20
        else:
            return 40
