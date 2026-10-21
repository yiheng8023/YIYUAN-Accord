"""Isolated Git environment for disposable repositories owned by tests."""

import os


def owned_git_environment():
    """Route fixture commands independently of the caller's Git configuration."""
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith('GIT_')}
    environment.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                       GIT_CONFIG_SYSTEM=os.devnull, GIT_CONFIG_COUNT='1',
                       GIT_CONFIG_KEY_0='gc.autoDetach', GIT_CONFIG_VALUE_0='false')
    return environment
