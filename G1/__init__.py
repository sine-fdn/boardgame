from dataclasses import dataclass
import json
from typing import List
from otree.api import *

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


class C(BaseConstants):
    NAME_IN_URL = "data_sharing"
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 5
    DATA_POINTS = 100  # Tokens to be contributed for the public good mechanism
    PLAYER_SHARES = [0.5, 0.4, 0.4, 0.3]  # Shares from the public good
    MULTIPLIER = 1.6  # Must match the sum of player shares
    INITIAL_UTILITY = cu(
        100
    )  # Benefits and costs from the public good are deducted here. Tokens that can be invested
    # to reduce contribution costs
    CONTRIBUTION_COSTS = [
        1,
        1,
        1,
        2,
    ]  # Costs (per data point contributed) deducted from INITIAL_UTILITY
    THRESHOLD = cu(150)  # Threshold to remove contribution costs
    MAX_INVESTMENT = cu(100)  # Maximum amount that one player can invest
    DATA_SETS: dict[str, List[DataSet]] = {
        "player 1": [
            DataSet(
                name="Mobility Data",
                icon="🚎",
                data_points=10,
                description="Data about mobility patterns in urban areas.",
                initial_sharing_costs=2,
                post_invest_sharing_costs=1,
                cost_description="Privacy concerns and data security.",
            ),
            DataSet(
                name="Health Data",
                icon="🏥",
                data_points=20,
                description="Data about health and wellness.",
                initial_sharing_costs=3,
                post_invest_sharing_costs=2,
                cost_description="Privacy concerns and data security.",
            ),
            DataSet(
                name="Weather Data",
                icon="☀️",
                data_points=15,
                description="Data about weather patterns and forecasts.",
                initial_sharing_costs=1,
                post_invest_sharing_costs=0,
                cost_description="Privacy concerns and data security.",
            ),
            DataSet(
                name="Traffic Data",
                icon="🚦",
                data_points=25,
                description="Data about traffic patterns and congestion.",
                initial_sharing_costs=2,
                post_invest_sharing_costs=1,
                cost_description="Privacy concerns and data security.",
            ),
        ],
        "player 2": [
            DataSet(
                name="Education Data",
                icon="🎓",
                data_points=10,
                description="Data about educational attainment and performance.",
                initial_sharing_costs=2,
                post_invest_sharing_costs=1,
                cost_description="Privacy concerns and data security.",
            ),
            DataSet(
                name="Social Media Data",
                icon="📱",
                data_points=20,
                description="Data about social media usage and interactions.",
                initial_sharing_costs=3,
                post_invest_sharing_costs=2,
                cost_description="Privacy concerns and data security.",
            ),
            DataSet(
                name="Financial Data",
                icon="💰",
                data_points=15,
                description="Data about financial transactions and investments.",
                initial_sharing_costs=4,
                post_invest_sharing_costs=2,
                cost_description="Privacy concerns and data security.",
            ),
            DataSet(
                name="Environmental Data",
                icon="🌍",
                data_points=25,
                description="Data about environmental conditions and changes.",
                initial_sharing_costs=2,
                post_invest_sharing_costs=1,
                cost_description="Privacy concerns and data security.",
            ),
        ],
    }


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
        label="How much would you like to invest to decrease the data sharing costs of Player 4?",
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
        data_sets = C.DATA_SETS.get(f"player {self.id_in_group}", [])
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
        player.contribution_cost_per = C.CONTRIBUTION_COSTS[i]
        player.public_good_share_per = C.PLAYER_SHARES[i]


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

    # Retrieve the session-wide cost_eliminated status
    cost_eliminated = group.session.vars.get("cost_eliminated", False)

    for i, player in enumerate(players):
        if cost_eliminated:
            player.contribution_cost = player.contribution
        else:
            player.contribution_cost = C.CONTRIBUTION_COSTS[i] * player.contribution

        player.public_good_share = C.PLAYER_SHARES[i] * group.total_contribution

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
        return {
            "players_data": players_data,
            "current_balance": current_balance,
            "round_number": player.round_number,
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
    form_fields = ["contribution"]

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
    Verification,
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
