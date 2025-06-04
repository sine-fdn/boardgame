from os import environ

SESSION_CONFIGS = [
    dict(
        name="cooperation_with_the_future",
        app_sequence=["G1"],
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
LANGUAGE_CODE = "en"

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = "EUR"
USE_POINTS = True
POINTS_CUSTOM_NAME = "Utility Points"

ADMIN_USERNAME = "admin"
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get("OTREE_ADMIN_PASSWORD")

DEMO_PAGE_INTRO_HTML = """ """

SECRET_KEY = "9993749924114"

DEBUG = False
