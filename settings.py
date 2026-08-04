from os import environ
from urllib.parse import urlparse
import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


SESSION_CONFIGS = [
    dict(
        name="data_sharing_game",
        app_sequence=["T1"],  # T1 = with the opportunity to decrease data sharing costs
        num_demo_participants=None,
    ),
]

ROOMS = [
    dict(name="econ_lab", display_name="Experiment"),
]
# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1, participation_fee=0.00, doc=""
)

PARTICIPANT_FIELDS = []  # active_punishment only needed for survey
SESSION_FIELDS = []

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = "de"

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = "EUR"
USE_POINTS = True
POINTS_CUSTOM_NAME = "Punkte"

ADMIN_USERNAME = environ.get("OTREE_ADMIN_USERNAME", "admin")

ADMIN_PASSWORD = environ["OTREE_ADMIN_PASSWORD"]

DEMO_PAGE_INTRO_HTML = """ """

SECRET_KEY = environ["OTREE_SECRET_KEY"]

DEBUG = False

AUTH_LEVEL = "STUDY"
