from dataclasses import dataclass
from typing import List, Dict
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
class PlayerConfig:
    id: str
    player_benefit: float
    rounds: Dict[int, List[DataSet]]


@dataclass
class GameConfig:
    intro: str
    num_of_players: int
    initial_utility: float
    investment_threshold: int
    players: List[PlayerConfig]


def load_game_config():
    path = os.path.join(os.path.dirname(__file__), "../game_config.json")
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if int(raw["num_of_players"]) != len(raw["players"]):
        raise ValueError(
            f"num_of_players ({raw['num_of_players']}) does not match number of players in array ({len(raw['players'])})"
        )

    players = []
    for player in raw["players"]:
        rounds = {}
        for round_num, datasets in player["rounds"].items():
            rounds[int(round_num)] = [DataSet(**ds) for ds in datasets]
        players.append(PlayerConfig(
            id=player["id"],
            player_benefit=float(player["player_benefit"]),
            rounds=rounds
        ))

    return GameConfig(
        intro=raw["intro"],
        num_of_players=int(raw["num_of_players"]),
        initial_utility=float(raw["initial_utility"]),
        investment_threshold=int(raw["investment_threshold"]),
        players=players,
    )


def get_player_shares(players: List[PlayerConfig]):
    return [player.player_benefit for player in players]


class C(BaseConstants):
    GAME_CONFIG: GameConfig = load_game_config()
    DATA_POINTS = 100
    NAME_IN_URL = "data_sharing"
    PLAYERS_PER_GROUP = GAME_CONFIG.num_of_players
    NUM_ROUNDS = 4
    MULTIPLIER = float(sum(get_player_shares(GAME_CONFIG.players)))
    INITIAL_UTILITY = cu(float(GAME_CONFIG.initial_utility))
    THRESHOLD = GAME_CONFIG.investment_threshold
    THRESHOLD_ROUND = 4
    MAX_INVESTMENT = cu(20)


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    total_contribution = models.IntegerField()
    total_investment = models.CurrencyField(initial=0)


class Player(BasePlayer):
    contribution = models.IntegerField(min=0, max=C.DATA_POINTS, label="")
    investment = models.CurrencyField(min=0, max=C.MAX_INVESTMENT, label="How much would you like to invest?")
    public_good_share = models.CurrencyField()
    public_good_share_per = models.FloatField(initial=0.00)
    contribution_cost = models.CurrencyField()
    contribution_cost_per = models.FloatField(initial=0.00)

    def get_savings(self, ds: DataSet):
        print("Calculating savings for dataset:", ds.name)
        return ds.initial_sharing_costs - ds.post_invest_sharing_costs

    def get_sharing_costs(self, ds: DataSet):
        if self.session.vars.get("cost_eliminated", False):
            return ds.post_invest_sharing_costs
        else:
            return ds.initial_sharing_costs

    def get_data_sets(self):
        player = next((p for p in C.GAME_CONFIG.players if int(p.id) == self.id_in_group), None)
        if not player:
            return []

        round_number = self.round_number
        data_sets = player.rounds.get(round_number, [])

        return [
            {
                "name": ds.name,
                "icon": ds.icon,
                "data_points": ds.data_points,
                "description": ds.description,
                "sharing_costs": self.get_sharing_costs(ds),
                "post_invest_costs": ds.post_invest_sharing_costs,
                "reduced_costs": ds.initial_sharing_costs > self.get_sharing_costs(ds),
                "cost_description": ds.cost_description,
                "savings": self.get_savings(ds),
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


class a_Intro1(Page):
    @staticmethod
    def is_displayed(player: Player):
        """
        Show this page only in the first round.
        """
        return player.round_number == 1

class b_Intro2(Page):
    @staticmethod
    def is_displayed(player: Player):
        """
        Show this page only in the first round.
        """
        return player.round_number == 1

class c_Intro3(Page):
    @staticmethod
    def is_displayed(player: Player):
        """
        Show this page only in the first round.
        """
        return player.round_number == 1

class d_Intro4(Page):
    @staticmethod
    def is_displayed(player: Player):
         """
         Show this page only in the first round.
         """
         return player.round_number == 1

class e_Intro5(Page):
    @staticmethod
    def is_displayed(player: Player):
         """
         Show this page only in the first round.
         """
         return player.round_number == 1

class UseCaseWaitPage(WaitPage):
    pass

class f_UseCaseIntro(Page):
    form_model = "player"

class g_Investment(Page):
    form_model = 'player'
    form_fields = ['investment']

    @staticmethod
    def is_displayed(player: Player):
        """
        Show this page only in the first round.
        """
        return player.round_number >= C.THRESHOLD_ROUND

    @staticmethod
    def vars_for_template(player: Player):
        data_sets = player.get_data_sets()

        total_savings = sum(ds["savings"] for ds in data_sets)

        return {
            # Aktueller Kontostand des Spielers
            "current_balance": player.participant.vars.get("current_balance", 0),
            # Ob in der vorherigen Runde die Investitionskosten eliminiert wurden
            "cost_eliminated": player.session.vars.get("cost_eliminated", False),
            # Werte aus der Public-Good-Mechanik (können im Template genutzt werden)
            "contribution_effect": f"{-player.contribution_cost_per:.2f}",
            "contribution_effect_other": f"{C.MULTIPLIER:.2f}",
            # Rundenzähler
            "round_number": player.round_number,
            "num_rounds": C.NUM_ROUNDS,
            # Schwellenwert für die Investition (optional für Anzeige)
            "threshold": C.THRESHOLD,
            # Die Datensätze des Spielers mit allen nötigen Feldern,
            # inklusive initial_sharing_costs und post_invest_sharing_costs
            "data_sets": player.get_data_sets(),
            "total_savings": total_savings
        }

class InvestmentWaitPage(WaitPage):
    after_all_players_arrive = set_investments


class g_ThresholdExceeded(Page):
    form_model = "player"

    @staticmethod
    def is_displayed(player: Player):
        """
        Show this page only in the first round.
        """
        return player.round_number >= C.THRESHOLD_ROUND

    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        return {
            "total_investment": group.field_maybe_none("total_investment") or 0,
            "threshold": C.THRESHOLD,
        }


class h_Contribution(Page):
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


class i_Results(Page):
    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        players = group.get_players()

        players_data = []
        for p in players:
            players_data.append(
                {
                    "id_in_group": p.id_in_group,
                    "contribution": p.contribution,
                    "contribution_cost": p.contribution_cost,
                    "public_good_share": p.public_good_share,
                    "ergebnis": p.public_good_share - p.contribution_cost,  # Ergebnis wird hier berechnet
                    "current_balance": p.participant.vars.get("current_balance", 0),
                }
            )

        total_contribution = group.total_contribution
        total_value = round(total_contribution * C.MULTIPLIER)
        anteil_pro_amt = total_value / C.PLAYERS_PER_GROUP if C.PLAYERS_PER_GROUP else 0

        return {
            "total_contribution": total_contribution,
            "players_data": players_data,
            "round_number": player.round_number,
            "cost_eliminated": player.session.vars.get("cost_eliminated", False),
            "current_balance": player.participant.vars.get("current_balance", 0),
            "total_value": total_value,
            "anteil_pro_amt": anteil_pro_amt,
        }

class j_Summary(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        players = group.get_players()

        # Label-Funktion
        def dept_label(pid):
            return (
                "🌿 Umwelt" if pid == 1 else
                "❤️ Soziales" if pid == 2 else
                "🚦 Verkehr"  if pid == 3 else
                "🛡 Sicherheit" if pid == 4 else
                f"Amt {pid}"
            )

        # Ranking nach aktuellem Kontostand
        players_ranking = []
        total_current_balance = 0
        for p in players:
            bal = p.participant.vars.get("current_balance", 0)
            players_ranking.append({
                "id_in_group": p.id_in_group,
                "dept": dept_label(p.id_in_group),
                "current_balance": bal,
            })
            total_current_balance += bal
        players_ranking.sort(key=lambda x: x["current_balance"], reverse=True)

        # Theoretisches Optimum (mit erfolgreichen Investitionen)
        # Ein Datensatz ist "teilenswert", wenn:
        #  - kollektiv rational:  C.MULTIPLIER * Punkte >= post_cost, oder
        #  - individuell rational: player_benefit * Punkte >= post_cost
        optimum_points_sum = 0
        optimum_post_costs_sum = 0
        for pconf in C.GAME_CONFIG.players:
            benefit = float(pconf.player_benefit)
            for rnd, sets in pconf.rounds.items():
                for ds in sets:
                    points = int(ds.data_points)
                    post_cost = int(ds.post_invest_sharing_costs)
                    group_gain = C.MULTIPLIER * points
                    indiv_gain = benefit * points
                    if group_gain >= post_cost or indiv_gain >= post_cost:
                        optimum_points_sum += points
                        optimum_post_costs_sum += post_cost

        optimum_brutto_value = int(round(optimum_points_sum * C.MULTIPLIER))
        optimum_investment_cost = int(C.THRESHOLD)
        optimum_net_value = C.INITIAL_UTILITY + optimum_brutto_value - optimum_post_costs_sum - optimum_investment_cost

        return {
            # Ranking & Ist
            "players_ranking": players_ranking,
            "total_current_balance": total_current_balance,

            # Optimum (Komponenten + Netto)
            "optimum_points_sum":         optimum_points_sum,
            "optimum_brutto_value":       optimum_brutto_value,
            "optimum_post_costs_sum":     optimum_post_costs_sum,
            "optimum_investment_cost":    optimum_investment_cost,
            "optimum_net_value":          optimum_net_value,

            # Meta
            "multiplier": C.MULTIPLIER,
        }



page_sequence = [
    EndowmentWaitPage,
    a_Intro1,
    b_Intro2,
    c_Intro3,
    d_Intro4,
    e_Intro5,
    UseCaseWaitPage,
    f_UseCaseIntro,
    g_Investment,
    InvestmentWaitPage,
    g_ThresholdExceeded,
    h_Contribution,
    ResultsWaitPage,
    i_Results,
    j_Summary,
]
