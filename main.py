# CameraHub Tagger

import configparser
import argparse
import os
import getpass
import requests
import re
from requests.auth import HTTPBasicAuth
from fnmatch import filter
from exif import Image
from uuid import UUID



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
            auth=('username', 'password')
        )

    if r.status_code == 200:
        rv = True
    else:
        rv = False

    return rv


def is_valid_uuid(uuid_to_test, version=4):
    """
    Check if uuid_to_test is a valid UUID.
    
     Parameters
    ----------
    uuid_to_test : str
    version : {1, 2, 3, 4}
    
     Returns
    -------
    `True` if uuid_to_test is a valid UUID, otherwise `False`.
    
     Examples
    --------
    >>> is_valid_uuid('c9bf9e57-1685-4c89-bafb-ff5af830be8a')
    True
    >>> is_valid_uuid('c9bf9e58')
    False
    """
    
    try:
        uuid_obj = UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test


def guess_frame(filename):
    m = re.search('^(\d+)-(\d+).*\.jpe?g$', filename.lower())
    return (m.group(0), m.group(1))
        

def prompt_frame(file):
    film = input("Enter film ID for {}: ".format(file))
    frame = input("Enter frame ID for {}: ".format(film))
    return (film, frame)


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.


# ----------------------------------------------------------------------
if __name__ == '__main__':
    print_hi('PyCharm')

    # Determine path to config file
    home = os.path.expanduser("~")
    path = os.path.join(home, "camerahub.ini")

    # Get our initial connection settings
    # Prompt the user to set them if they don't exist
    server = get_setting(path, 'Settings', 'server')
    username = get_setting(path, 'Settings', 'username')
    password = get_setting(path, 'Settings', 'password')

    #update_setting(path, "Settings", "font_size", "12")

    # Test the credentials we have
    if test_credentials(server, username, password):
        print("Creds OK")
    else:
        print("Creds not OK")


    # Read in args
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--recursive', help="search for scans recursively", action='store_true')
    parser.add_argument('-a', '--auto', help="don't prompt user to identify scans, only guess based on filename", action='store_true')
    parser.add_argument('-y', '--yes', help="accept all changes", action='store_true')
    parser.add_argument('-d', '--dry-run', help="don't write any tags", action='store_true')
    #parser.add_argument('-c', '--config', help="path to config file, default ~/.camerahub")
    parser.add_argument('-f', '--file', help="image file to be tagged", type=str)
    args = parser.parse_args()


# if no args, scan current folder. consider recursive option
# elsif load individual frame
# or quit if none

files = []
if args.file:
    files.append(args.file)
elif args.recursive:
    # recursive search here
    pass
else:
    files = filter(os.listdir('.'), '*.[Jj][Pp][Gg]')

if len(files) == 0:
    print("No files found")
    exit

# foreach found photo:
# read exif data, check for camerahub scan tag
for file in files:
    #print("Found file: {}".format(file))

    # Extract exif data from file
    with open(file, 'rb') as image_file:
        image = Image(image_file)

    if image.has_exif is True and image.image_unique_id and is_valid_uuid(image.image_unique_id):
        # check for presence of custom exif tag for camerahub
        # ImageUniqueID, UserComment, Comment
        # already has a uuid scan id
        print("{} already has an EXIF scan ID".format(file))
    else:
        # need to match it with a neg/print and generate a scan id
        print("{} does not have an EXIF scan ID".format(file))

        # else prompt user to identify the scan
        #	guess film/frame from filename
        (film, frame) = guess_frame(file)
        #	either accept film/frame or just film then prompt frame
        if isinstance(film, int) and isinstance(frame, str):
            # lookup neg id from API
        else:
            (film, frame) = prompt_frame(file)
            # prompt user for film/frame

        #	generate scan id
        #   lookup extended scan details in API


        # prepare diff of tags
        # if non-zero diff, ask user to confirm tag write
