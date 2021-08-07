"""
CameraHub Tagger
"""

import configparser
import argparse
import os
import sys
import getpass
import re
import json
from fnmatch import filter
from uuid import UUID
from exif import Image
import requests



def create_config(path):
    """
    Create a config file in the user's home dir
    """
    config = configparser.ConfigParser()
    config.add_section("Settings")
    config.set("Settings", "server", args.server)

    print("Enter your login details for CameraHub.")

    try:
        l_username = input("Enter CameraHub username: ")
    except Exception as error:
        print('ERROR', error)
    else:
        config.set("Settings", "username", l_username)

    try:
        l_password = getpass.getpass(prompt="Enter CameraHub password: ")
    except Exception as error:
        print('ERROR', error)
    else:
        config.set("Settings", "password", l_password)

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
    Get the value of a config setting
    """
    l_config = get_config(path)
    l_value = l_config.get(section, setting)
    return l_value


def update_setting(l_path, l_section, l_setting, l_value):
    """
    Update a setting
    """
    config = get_config(l_path)
    config.set(l_section, l_setting, l_value)
    with open(l_path, "w") as config_file:
        config.write(config_file)


def test_credentials(l_server, l_username, l_password):
    """
    Validate a set of credentials
    :param server:
    :param username:
    :param password:
    :return: Bool
    """

    response = requests.get(
            l_server+'/camera',
            auth=(l_username, l_password)
        )

    return bool(response.status_code == 200)


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
    """

    try:
        uuid_obj = UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test


def guess_frame(filename):
    """
    Guess a negative's film id and frame id based on its filename
    Assumes a format of [film]-[frame]-title.jpg
    for example 123-22-holiday.jpg
    """
    match = re.search(r'^(\d+)-(\d+).*\.jpe?g$', filename.lower())
    if match:
    return (match.group(0), match.group(1))
    else:
        return


def prompt_frame(filename):
    """
    Prompt user to enter film id and frame id
    At the moment these questions are asked sequentially
    TODO: be able to parse compact film/frame format
    """
    l_film = input("Enter film ID for {}: ".format(filename))
    l_frame = input("Enter frame ID for {}: ".format(l_film))
    return (l_film, l_frame)

def create_scan(l_negative):
    """
    Create a new Scan record in CameraHub, associated with the Negative record
    POST to https://camerahub.info/api/scan/
    {
        "negative": null,
        "print": null,
        "filename": "",
        "date": null
    }
    """

    # Create dict
    data = {'negative': l_negative}
    url = 'https://dev.camerahub.info/api/scan/'
    response = requests.post(url, data = data)
    # TODO: extract new scan id from response

    return response


def get_scan(l_scan):
    """
    Get all details about a scan record in CameraHub
    GET https://dev.camerahub.info/api/scan/?uuid=07c1c01c-0092-4025-8b0f-4513ff6d327b
    or POST a json object
    """
    print(l_scan)
    return l_scan


def get_negative(l_film, l_frame):
    """
    Find the negative ID for a negative based on its film ID and frame ID
    """
    print(l_film)
    print(l_frame)
    return l_film


def api2exif(l_apidata):
    """
    Reformat CameraHub format tags into EXIF format tags.
    CameraHub tags from the API will be JSON-formatted whereas EXIF
    tags are formatted as a simple dictionary. This will also translate
    tags that have different names.
    """
    l_exifdata = l_apidata
    return l_exifdata


def diff_tags(dicta, dictb):
    """
    Compare two dictionaries of EXIF tags and return a dictionary which contains
    the diff required to apply b's data to a, without destroying data in a.
    This uses a symmetric difference operator:
    https://docs.python.org/3/library/stdtypes.html#frozenset.symmetric_difference
    """
    seta = set(dicta.items())
    setb = set(dictb.items())
    return dict(seta ^ setb)


def yes_or_no(question):
    """
    Prompt for a yes/no answer
    https://gist.github.com/garrettdreyfus/8153571#gistcomment-2586248
    """
    answer = input(question + "(y/n): ").lower().strip()
    print("")
    while not answer in ('y', 'yes', 'n', 'no'):
        print("Input yes or no")
        answer = input(question + "(y/n):").lower().strip()
        print("")
    return bool(answer[0] == "y")

# ----------------------------------------------------------------------
if __name__ == '__main__':
    print("CameraHub Tagger")

    # Determine path to config file
    home = os.path.expanduser("~")
    configpath = os.path.join(home, "camerahub.ini")

    # Read in args
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--recursive', help="search for scans recursively", action='store_true')
    parser.add_argument('-a', '--auto', help="don't prompt user to identify scans, only guess based on filename", action='store_true')
    parser.add_argument('-y', '--yes', help="accept all changes", action='store_true')
    parser.add_argument('-d', '--dry-run', help="don't write any tags", action='store_true')
    parser.add_argument('-c', '--config', help="path to config file", default=configpath)
    parser.add_argument('-f', '--file', help="image file to be tagged", type=str)
    parser.add_argument('-s', '--server', help="CameraHub server to connect to", default="https://camerahub.info/api", type=str)
    args = parser.parse_args()

    # Get our initial connection settings
    # Prompt the user to set them if they don't exist
    server = get_setting(args.config, 'Settings', 'server')
    username = get_setting(args.config, 'Settings', 'username')
    password = get_setting(args.config, 'Settings', 'password')

    # Test the credentials we have
    if test_credentials(server, username, password):
        print("Creds OK")
    else:
        print("Creds not OK")

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
        sys.exit

    # foreach found photo:
    # read exif data, check for camerahub scan tag
    for file in files:
        print("Processing image {}".format(file))

        # Extract exif data from file
        with open(file, 'rb') as image_file:
            image = Image(image_file)

        if image.has_exif is True and image.get("image_unique_id") and is_valid_uuid(image.image_unique_id):
            # check for presence of custom exif tag for camerahub
            # ImageUniqueID, UserComment, Comment
            # already has a uuid scan id
            print("{} already has an EXIF scan ID".format(file))
        else:
            # need to match it with a neg/print and generate a scan id
            print("{} does not have an EXIF scan ID".format(file))

            try:
                # guess film/frame from filename
            film, frame = guess_frame(file)
            except:
                film, frame = prompt_frame(file)

            # lookup neg id from API
            negative = get_negative(film, frame, username, password)

            #	generate scan id
            scan = create_scan(negative)

            #   lookup extended scan details in API
            apidata = get_scan(scan)

            # mangle CameraHub format tags into EXIF format tags
            exifdata = api2exif(apidata)

            # prepare diff of tags
            diff = diff_tags(image, exifdata)

            # if non-zero diff, ask user to confirm tag write
            if len(diff.keys) > 0:
                # print diff & confirm write
                print(diff)

                if not args.dry_run and yes_or_no("Write this metadata to the file?"):

                    # Apply the diff to the image
                    for key, value in diff.items():
                        image.set(key, value)

                    # do the write
                    with open(file, 'wb') as image_file:
                        image = Image(image_file)
                        image_file.write(image.get_file())
