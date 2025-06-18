from dataclasses import dataclass
from typing import List
from otree.api import *
import json
import os

doc = """
Your app description
"""


@dataclass
class DataSet:
    name: str
    icon: str
    data_points: int
    description: str
    initial_sharing_costs: int
    post_invest_sharing_costs: int
    cost_description: str


@dataclass
class Player:
    id: str
    player_benefit: float
    data_sets: List[DataSet]


@dataclass
class GameConfig:
    intro: str
    num_of_players: int
    initial_utility: float
    investment_threshold: int
    players: List[Player]


def load_game_config():
    path = os.path.join(os.path.dirname(__file__), "../game_config.json")
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if int(raw["num_of_players"]) != len(raw["players"]):
        raise ValueError(
            f"num_of_players ({raw['num_of_players']}) does not match number of players in array ({len(raw['players'])})"
        )
    game_config = {
        "intro": raw["intro"],
        "num_of_players": int(raw["num_of_players"]),
        "initial_utility": float(raw["initial_utility"]),
        "investment_threshold": int(raw["investment_threshold"]),
        "players": [
            Player(
                id=player["id"],
                player_benefit=float(player["player_benefit"]),
                data_sets=[DataSet(**ds) for ds in player["data_sets"]],
            )
            for player in raw["players"]
        ],
    }
    # TODO: Should DATA_POINTS also be determined in the game_config.json file?
    for player in game_config["players"]:
        total_data_points = sum(ds.data_points for ds in player.data_sets)
        if total_data_points != 100:
            raise ValueError(
                f"Total data points for player {player.id} ({total_data_points}) is not 100"
            )
    return GameConfig(**game_config)


def get_player_shares(players: List[Player]):
    return [player.player_benefit for player in players]


class C(BaseConstants):
    GAME_CONFIG: GameConfig = load_game_config()
    DATA_POINTS = 100  # Tokens to be contributed for the public good mechanism
    NAME_IN_URL = "data_sharing"
    PLAYERS_PER_GROUP = GAME_CONFIG.num_of_players  # Set to 4 when not developing
    NUM_ROUNDS = 5
    MULTIPLIER = float(
        sum(get_player_shares(GAME_CONFIG.players))
    )  # Must match the sum of player shares
    INITIAL_UTILITY = cu(
        float(GAME_CONFIG.initial_utility)
    )  # Benefits and costs from the public good are deducted here. Tokens that can be invested
    # to reduce contribution costs
    THRESHOLD = (
        GAME_CONFIG.investment_threshold
    )  # Threshold to remove contribution costs
    MAX_INVESTMENT = cu(100)  # Maximum amount that one player can invest


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    total_contribution = models.IntegerField()
    total_investment = models.CurrencyField(inital=0)


class Player(BasePlayer):
    contribution = models.IntegerField(
        min=0,
        max=C.DATA_POINTS,
        label="",  # Leave this empty to avoid a visible label
    )
    investment = models.CurrencyField(
        min=0,
        max=C.MAX_INVESTMENT,
        label="How much would you like to invest to decrease these data sharing costs?",
    )
    public_good_share = models.CurrencyField()  # Total amount paid out
    public_good_share_per = models.FloatField(
        initial=0.00
    )  # Marginal share coming from PLAYER_SHARES

    contribution_cost = models.CurrencyField()  # Total costs
    contribution_cost_per = models.FloatField(
        initial=0.00
    )  # Marginal costs coming from CONTRIBUTION_COSTS

    def get_data_sets(self):
        player = next(
            (p for p in C.GAME_CONFIG.players if int(p.id) == self.id_in_group), None
        )

        data_sets = player.data_sets if player else []

        return [
            {
                "name": ds.name,
                "icon": ds.icon,
                "data_points": ds.data_points,
                "description": ds.description,
                "sharing_costs": (
                    ds.post_invest_sharing_costs
                    if self.session.vars.get("cost_eliminated", False)
                    else ds.initial_sharing_costs
                ),
                "reduced_costs": ds.initial_sharing_costs > ds.post_invest_sharing_costs,
                "cost_description": ds.cost_description,
            }
            for ds in data_sets
        ]


def set_endowments(group: Group):
    # Set current balance initally
    if group.subsession.round_number == 1:
        for player in group.get_players():
            player.participant.vars["current_balance"] = C.INITIAL_UTILITY

    # Set marginal costs and shares for each player
    for i, player in enumerate(group.get_players()):
        player.public_good_share_per = get_player_shares(C.GAME_CONFIG.players)[i]


def set_investments(group: Group):
    # Skip if cost_eliminated is already True
    if group.session.vars.get("cost_eliminated", False):
        print("Cost already eliminated. Skipping set_investments.")
        return

    players = group.get_players()
    group.total_investment = sum(p.field_maybe_none("investment") or 0 for p in players)

    for player in players:
        current_balance = player.participant.vars.get("current_balance", 0)
        player.participant.vars["current_balance"] = current_balance - (
            player.field_maybe_none("investment") or 0
        )

    if group.total_investment >= C.THRESHOLD:
        group.session.vars["cost_eliminated"] = True
        print("Threshold met: Cost eliminated!")


def set_payoffs(group: Group):
    players = group.get_players()

    group.total_contribution = sum(p.contribution for p in players)

    for i, player in enumerate(players):

        player.public_good_share = (
            get_player_shares(C.GAME_CONFIG.players)[i] * group.total_contribution
        )

        # Calculate the player's payout
        player.payoff += -player.contribution_cost + player.public_good_share

        current_balance = player.participant.vars.get(
            "current_balance", 0
        )  # Default to 0 if not set
        player.participant.vars["current_balance"] = current_balance + player.payoff


# PAGES
class EndowmentWaitPage(WaitPage):
    after_all_players_arrive = set_endowments


class Intro(Page):
    @staticmethod
    def is_displayed(player: Player):
        """
        Show this page only in the first round.
        """
        return player.round_number == 1

    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        players_data = []
        for p in group.get_players():
            players_data.append(
                {
                    "id_in_group": p.id_in_group,
                    "contribution_cost_per": -p.contribution_cost_per,
                    "public_good_share_per": p.public_good_share_per,
                    "contribution_effect": f"{-p.contribution_cost_per + p.public_good_share_per:.2f}",
                    "contribution_effect_other": f"{C.MULTIPLIER - p.public_good_share_per:.2f}",
                }
            )
        return {
            "players_data": players_data,
            "round_number": player.round_number,
        }


class Verification(Page):
    form_model = "player"

    @staticmethod
    def is_displayed(player: Player):
        """
        Show this page only in the first round.
        """
        return player.round_number == 1


class CommsWaitPage(WaitPage):
    pass


class Communication(Page):
    form_model = "player"
    timeout_seconds = 120  # 2 minutes timer

    @staticmethod
    def is_displayed(player: Player):
        # Display the page only in rounds 3, 4, and 5
        return player.round_number >= 3


class Investment(Page):
    form_model = "player"
    form_fields = ["investment"]

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number >= 2 and not player.session.vars.get(
            "cost_eliminated", False
        )

    @staticmethod
    def vars_for_template(player: Player):
        current_balance = player.participant.vars.get("current_balance", 0)
        group = player.group
        players_data = []
        for p in group.get_players():
            players_data.append(
                {
                    "id_in_group": p.id_in_group,
                    "contribution_effect": f"{-p.contribution_cost_per + p.public_good_share_per:.2f}",
                    "contribution_effect_other": f"{C.MULTIPLIER - p.public_good_share_per:.2f}",
                }
            )
        data_sets = []
        for p in C.GAME_CONFIG.players:
            filtered_data_sets = [
                {
                    "name": d.name,
                    "icon": d.icon,
                    "data_points": d.data_points,
                    "description": d.description,
                    "initial_sharing_costs": d.initial_sharing_costs,
                    "post_invest_sharing_costs": d.post_invest_sharing_costs,
                    "diff_sharing_costs": d.initial_sharing_costs
                    - d.post_invest_sharing_costs,
                    "cost_description": d.cost_description,
                }
                for d in p.data_sets
                if d.initial_sharing_costs > d.post_invest_sharing_costs
            ]
            if filtered_data_sets:
                data_sets.append(
                    {
                        "player_id": int(p.id),
                        "data_sets": filtered_data_sets,
                    }
                )

        return {
            "players_data": players_data,
            "current_balance": current_balance,
            "round_number": player.round_number,
            "data_sets_per_player": data_sets,
        }


class InvestmentWaitPage(WaitPage):
    after_all_players_arrive = set_investments


class ThresholdExceeded(Page):
    @staticmethod
    def is_displayed(player: Player):
        """
        Show this page only if the total investment exceeds the threshold.
        """
        group = player.group
        total_investment = group.field_maybe_none("total_investment") or 0
        return total_investment >= C.THRESHOLD

    @staticmethod
    def vars_for_template(player: Player):
        current_balance = player.participant.vars.get("current_balance", 0)
        return {
            "current_balance": current_balance,
        }


class Contribution(Page):
    form_model = "player"
    form_fields = ["contribution", "contribution_cost"]

    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        players_data = []
        for p in group.get_players():
            players_data.append(
                {
                    "id_in_group": p.id_in_group,
                }
            )

        return {
            "current_balance": player.participant.vars.get("current_balance", 0),
            "cost_eliminated": player.session.vars.get("cost_eliminated", False),
            "contribution_effect": f"{-player.contribution_cost_per:.2f}",
            "contribution_effect_other": f"{C.MULTIPLIER:.2f}",
            "round_number": player.round_number,
            "data_sets": player.get_data_sets(),
        }


class ResultsWaitPage(WaitPage):
    after_all_players_arrive = set_payoffs


class Results(Page):
    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        players_data = []
        for p in group.get_players():
            players_data.append(
                {
                    "id_in_group": p.id_in_group,
                    "contribution": p.contribution,
                    "contribution_cost": p.contribution_cost,
                    "public_good_share": p.public_good_share,
                    "current_balance": p.participant.vars.get("current_balance", 0),
                }
            )
        return {
            "total_contribution": group.total_contribution,
            "players_data": players_data,
            "round_number": player.round_number,
            "cost_eliminated": player.session.vars.get("cost_eliminated", False),
            "current_balance": player.participant.vars.get("current_balance", 0),
            "total_value": round(group.total_contribution * C.MULTIPLIER),
        }


class Summary(Page):
    @staticmethod
    def is_displayed(player: Player):
        """
        Show this page only in the last round.
        """
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        players_data = []
        total_current_balance = 0  # Initialize the total balance
        comparison_value = 1390  # The value to compare against

        for p in group.get_players():
            current_balance = p.participant.vars.get("current_balance", 0)
            players_data.append(
                {
                    "id_in_group": p.id_in_group,
                    "current_balance": current_balance,
                }
            )
            total_current_balance += (
                current_balance  # Add each player's balance to the total
            )

        # Avoid division by zero and calculate percentage
        percentage_of_target = (
            (float(total_current_balance) / float(comparison_value)) * 100
            if comparison_value > 0
            else 0
        )

        return {
            "players_data": players_data,
            "total_current_balance": total_current_balance,
            "percentage_of_target": round(
                percentage_of_target, 2
            ),  # Round to 2 decimal places
            "comparison_value": comparison_value,
        }


page_sequence = [
    EndowmentWaitPage,
    Intro,
    CommsWaitPage,
    Communication,
    Investment,
    InvestmentWaitPage,
    ThresholdExceeded,
    Contribution,
    ResultsWaitPage,
    Results,
    Summary,
]
