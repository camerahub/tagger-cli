# CameraHub Tagger

import configparser
import os
import getpass
import requests
from requests.auth import HTTPBasicAuth


def create_config(path):
    """
    Create a config file in the user's home dir
    """
    config = configparser.ConfigParser()
    config.add_section("Settings")
    config.set("Settings", "server", "https://camerahub.info/api")

    print("Enter your login details for CameraHub.")

    try:
        u = input("Enter CameraHub username: ")
    except Exception as error:
        print('ERROR', error)
    else:
        config.set("Settings", "username", u)

    try:
        p = getpass.getpass(prompt="Enter CameraHub password: ")
    except Exception as error:
        print('ERROR', error)
    else:
        config.set("Settings", "password", p)

    with open(path, "w") as config_file:
        config.write(config_file)


def get_config(path):
    """
    Returns the config object, creating it if necessary
    """
    if not os.path.exists(path):
        create_config(path)

    config = configparser.ConfigParser()
    config.read(path)
    return config


def get_setting(path, section, setting):
    """
    Print out a setting
    """
    config = get_config(path)
    value = config.get(section, setting)
    print
    "{section} {setting} is {value}".format(
        section=section, setting=setting, value=value)
    return value


def update_setting(path, section, setting, value):
    """
    Update a setting
    """
    config = get_config(path)
    config.set(section, setting, value)
    with open(path, "w") as config_file:
        config.write(config_file)


def test_credentials(server, username, password):
    """
    Validate a set of credentials
    :param server:
    :param username:
    :param password:
    :return: Bool
    """

    r = requests.get(
            server+'/camera',
            auth=HTTPBasicAuth('username', 'password')
        )

    if r.status_code == 200:
        rv = True
    else:
        rv = False

    return rv


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.


# ----------------------------------------------------------------------
if __name__ == '__main__':
    print_hi('PyCharm')

    home = os.path.expanduser("~")
    path = os.path.join(home, "camerahub.ini")
    server = get_setting(path, 'Settings', 'server')
    username = get_setting(path, 'Settings', 'username')
    password = get_setting(path, 'Settings', 'password')

    #update_setting(path, "Settings", "font_size", "12")

    #print("Credentials we would have used: SERVER {} PASS {} USER {}".format(server, username, password))
    if test_credentials(server, username, password):
        print("Creds OK")
    else:
        print("Creds not OK")


# TODO check for config/creds
# if none, prompt to create and test

# if no args, scan current folder. consider recursive option
# elsif load individual frame
# or quit if none

# foreach found photo:
# read exif data, check for camerahub scan tag

# if has existing scan
# else prompt user to identify the scan
#	guess film/frame from filename
#	either accept film/frame or just film then prompt frame
#	generate scan id

# lookup scan id in API
# prepare diff of tags
# if non-zero diff, ask user to confirm tag write