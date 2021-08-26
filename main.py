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
from requests.models import HTTPError
from datetime import date



def create_config(path):
    """
    Create a config file in the user's home dir
    """
    config = configparser.ConfigParser()
    config.add_section("Settings")
    config.set("Settings", "server", "https://camerahub.info/api")

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


def test_credentials(l_server):
    """
    Validate a set of credentials
    :param server:
    :param username:
    :param password:
    :return: Bool
    """

    response = requests.get(
            l_server+'/camera',
            auth=auth
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
    if match and match.group(0) and match.group(1):
        returnval = (match.group(0), match.group(1))
    else:
        returnval = None
    return returnval


def prompt_frame(filename):
    """
    Prompt user to enter film id and frame id
    At the moment these questions are asked sequentially
    TODO: be able to parse compact film/frame format
    """
    l_film = input("Enter film ID for {}: ".format(filename))
    l_frame = input("Enter frame ID for {}: ".format(l_film))
    return (l_film, l_frame)

def create_scan(l_negative, l_filename):
    """
    Creates a new Scan record in CameraHub, associated with a Negative record
    Returns the uuid of the new Scan record
    {
        "negative": null,
        "print": null,
        "filename": "",
        "date": null
    }
    """

    # Create dict
    data = {
        'negative': l_negative,
        'filename': l_filename,
        'date': date.today()}
    url = server+'/scan/'
    response = requests.post(url, auth=auth, data = data)
    response.raise_for_status()
    data=json.loads(response.text)
    return data["uuid"]


def get_scan(l_scan):
    """
    Get all details about a scan record in CameraHub
    """
    payload = {'uuid': l_scan}
    url = server+'/scan/'
    response = requests.get(url, auth=auth, params=payload)
    response.raise_for_status()

    data=json.loads(response.text)
    if data["count"] == 1:
        scan = data["results"][0]

    return scan


def get_negative(l_film, l_frame):
    """
    Find the negative slug for a negative based on its film slug and frame
    """
    # TODO: complete this function with API lookup
    payload = {'film': l_film, 'frame': l_frame}
    url = server+'/negative/'
    response = requests.get(url, auth=auth, params=payload)
    response.raise_for_status()

    data=json.loads(response.text)
    if data["count"] == 1:
        negative = data["results"][0]["slug"]

    return negative


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

    # Get our initial connection settings
    # Prompt the user to set them if they don't exist
    server = get_setting(configpath, 'Settings', 'server')
    username = get_setting(configpath, 'Settings', 'username')
    password = get_setting(configpath, 'Settings', 'password')

    # Create auth object
    auth = (username, password)

    # Test the credentials we have
    try:
        test_credentials(server, username, password)
    except:
        print("Creds not OK")
    else:
        print("Creds OK")

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

            # else prompt user to identify the scan
            #	guess film/frame from filename
            guess = guess_frame(file)
            if guess:
                film, frame = guess
                print("Deduced Film ID {} and Frame {}".format(film, frame))

            else:
                print("{} does not match FILM-FRAME notation".format(file))
                # prompt user for film/frame
                #	either accept film/frame or just film then prompt frame
                film, frame = prompt_frame(file)

            # Lookup Negative from API
            try:
                negative = get_negative(film, frame)
            except HTTPError as err:
                print(err)
                continue
            except:
                print("Couldn't find Negative ID for {}".format(file))
                continue
            else:
                print("{} corresponds to Negative {}".format(file, negative))

            # Create Scan record associated with the Negative
            try:
                scan = create_scan(negative, file)
            except:
                print("Couldn't generate Scan ID for Negative {}".format(negative))
                continue
            else:
                print("Created new Scan ID {}".format(scan))

            # Lookup extended Scan details in API
            try:
                apidata = get_scan(scan)
            except:
                print("Couldn't retrieve data for Scan {}".format(scan))
            else:
                print("Got data for Scan {}".format(scan))

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
