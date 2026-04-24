"""Entry point: python -m dashboard"""
from dashboard.app import main
from dashboard.config import load_config

if __name__ == "__main__":
    main(load_config())
