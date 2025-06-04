# SINE ÖPGV Boardgame

This repository contains the source code for the new version of boardgame being developed by SINE in
the context of the ÖPGV project.

## Run locally

Make sure you have Python 3.7 or higher installed.

Install dependencies:
```bash
pip install -r requirements.txt
```

Run the game:
```bash
otree devserver
```

## Deployment on Fly.io

Make sure to have flyctl [installed](https://fly.io/docs/flyctl/install/) and that you're [logged
in](https://fly.io/docs/flyctl/auth/).

Deploy the game:
```bash
flyctl deploy
```
