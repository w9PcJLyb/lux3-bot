from sys import stderr as err

from .base import Params
from .state import State
from .harvest import harvest
from .explore import explore


class Agent:
    def __init__(self, player: str, env_cfg) -> None:
        self.player = player
        self.opp_player = "player_1" if self.player == "player_0" else "player_0"
        self.team_id = 0 if self.player == "player_0" else 1
        self.opp_team_id = 1 if self.team_id == 0 else 0

        Params.MAX_UNITS = env_cfg["max_units"]
        Params.UNIT_MOVE_COST = env_cfg["unit_move_cost"]
        Params.UNIT_SAP_COST = env_cfg["unit_sap_cost"]
        Params.UNIT_SAP_RANGE = env_cfg["unit_sap_range"]
        Params.UNIT_SENSOR_RANGE = env_cfg["unit_sensor_range"]

        self.state = State(self.team_id)
        self.previous_state = self.state.copy()

    def act(self, step: int, obs, remaining_overage_time: int = 60):
        self.state.update(obs)

        # print(
        #     f"start step {self.state.global_step}"
        #     f", match {self.state.match_number}:{self.state.match_step}",
        #     file=err,
        # )

        if self.state.match_step == 0:
            self.previous_state = self.state.copy()

        space = self.state.space
        fleet = self.state.fleet

        # space.show_map(fleet)
        # space.show_energy_field()
        # space.show_exploration_info()

        explore(self.state)
        harvest(self.state)

        # fleet.show_tasks()

        self.previous_state = self.state.copy()
        return fleet.create_actions_array()
