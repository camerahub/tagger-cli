"""
Functions which handle config creation and retrieval for this app
"""

import configparser
import getpass
import os

def create_config(path):
    """
    Create an empty config file in the user's home dir
    """
    config = configparser.ConfigParser()

    with open(path, "w") as config_file:
        config.write(config_file)


def create_profile(l_path, l_config, l_section):
    """
    Create a new config profile in an existing config file
    """

    l_config.add_section(l_section)

    try:
        default = "https://camerahub.info/api"
        l_server = input(f"Enter CameraHub server for profile '{l_section}' (default {default}): ") or default
    except Exception as error:
        print('ERROR', error)
    else:
        l_config.set(l_section, "server", l_server)

    try:
        l_username = input(f"Enter CameraHub username for {l_server}: ")
    except Exception as error:
        print('ERROR', error)
    else:
        l_config.set(l_section, "username", l_username)

    try:
        l_password = getpass.getpass(prompt=f"Enter CameraHub password for {l_server}: ")
    except Exception as error:
        print('ERROR', error)
    else:
        l_config.set(l_section, "password", l_password)

    with open(l_path, "w") as config_file:
        l_config.write(config_file)


def get_config(path, section):
    """
    Returns the config object, creating it if necessary
    """
    # Create the config file if necessary
    if not os.path.exists(path):
        create_config(path)

    config = configparser.ConfigParser()
    config.read(path)

    # Ensure the requested profile exists and create if not
    if not config.has_section(section):
        create_profile(path, config, section)
        config.read(path)

    return config


def get_setting(path, section, setting):
    """
    Get the value of a config setting
    """
    l_config = get_config(path, section)
    l_value = l_config.get(section, setting)
    return l_value
