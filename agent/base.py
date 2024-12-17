import os
import sys


class Global:
    VERBOSITY = 2
    if os.path.exists("/kaggle_simulations"):
        VERBOSITY = -1

    # Game related constants
    MAX_UNITS = 16
    SPACE_SIZE = 24
    MAX_UNIT_ENERGY = 400
    RELIC_REWARD_RANGE = 2
    MIN_ENERGY_PER_TILE = -20
    MAX_ENERGY_PER_TILE = 20
    MAX_STEPS_IN_MATCH = 100
    UNIT_MOVE_COST = 1  # OPTIONS: list(range(1, 6))
    UNIT_SAP_COST = 30  # OPTIONS: list(range(30, 51))
    UNIT_SAP_RANGE = 3  # OPTIONS: list(range(3, 8))
    UNIT_SENSOR_RANGE = 2  # OPTIONS: list(range(2, 5))

    # Agent parameters
    HIDDEN_NODE_ENERGY = 0
    NEBULA_ENERGY_REDUCTION = 10  # OPTIONS: [0, 10, 25]
    OBSTACLE_MOVEMENT_PERIOD = 20  # OPTIONS: 20, 40
    OBSTACLE_MOVEMENT_DIRECTION = (0, 0)  # OPTIONS: [(1, -1), (-1, 1)]

    # Exploration flags
    ALL_RELICS_FOUND = False
    ALL_REWARDS_FOUND = False
    NEBULA_ENERGY_REDUCTION_FOUND = False
    OBSTACLE_MOVEMENT_PERIOD_FOUND = False
    OBSTACLE_MOVEMENT_DIRECTION_FOUND = False

    # Info about completed matches
    NUM_COMPLETED_MATCHES = 0
    NUM_WINS = 0
    POINTS = []  # points we scored
    OPP_POINTS = []  # points scored by the opponent

    # Game logs:

    # REWARD_RESULTS: [{"nodes": Set[Node], "points": int}, ...]
    # A history of reward events, where each entry contains:
    # - "nodes": A set of nodes where our ships were located.
    # - "points": The number of points scored at that location.
    # This data will help identify which nodes yield points.
    REWARD_RESULTS = []


class Colors:
    red = "\033[91m"
    blue = "\033[94m"
    yellow = "\033[93m"
    green = "\033[92m"
    endc = "\033[0m"


SPACE_SIZE = Global.SPACE_SIZE


def log(*args, level=3):
    # 1 - Error
    # 2 - Info
    # 3 - Debug
    if level <= Global.VERBOSITY:
        if level == 1:
            print(f"{Colors.red}Error{Colors.endc}:", *args, file=sys.stderr)
        else:
            print(*args, file=sys.stderr)


def is_upper_sector(x, y) -> bool:
    return SPACE_SIZE - x - 1 >= y


def is_lower_sector(x, y) -> bool:
    return SPACE_SIZE - x - 1 <= y


def is_middle_line(x, y) -> bool:
    return SPACE_SIZE - x - 1 == y


def is_team_sector(team_id, x, y) -> bool:
    return is_upper_sector(x, y) if team_id == 0 else is_lower_sector(x, y)


def get_opposite(x, y) -> tuple:
    return SPACE_SIZE - y - 1, SPACE_SIZE - x - 1


def is_inside(x, y) -> bool:
    return 0 <= x < SPACE_SIZE and 0 <= y < SPACE_SIZE


def manhattan_distance(a, b) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def chebyshev_distance(a, b) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def nearby_positions(x, y, distance):
    for _x in range(max(0, x - distance), min(SPACE_SIZE, x + distance + 1)):
        for _y in range(max(0, y - distance), min(SPACE_SIZE, y + distance + 1)):
            yield _x, _y


def get_spawn_location(team_id):
    return (0, 0) if team_id == 0 else (SPACE_SIZE - 1, SPACE_SIZE - 1)


def warp_int(x):
    if x >= SPACE_SIZE:
        x -= SPACE_SIZE
    elif x < 0:
        x += SPACE_SIZE
    return x


def warp_point(x, y):
    return warp_int(x), warp_int(y)
