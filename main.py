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
from datetime import date
from decimal import Decimal
import pprint
from exif import Image
import requests
from requests.models import HTTPError



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
        l_scan = data["results"][0]

    return l_scan


def get_negative(l_film, l_frame):
    """
    Find the negative slug for a negative based on its film slug and frame
    """
    payload = {'film': l_film, 'frame': l_frame}
    url = server+'/negative/'
    response = requests.get(url, auth=auth, params=payload)
    response.raise_for_status()

    data=json.loads(response.text)
    if data["count"] == 1:
        l_negative = data["results"][0]["slug"]

    return l_negative


def api2exif(l_apidata):
    """
    Reformat CameraHub format tags into EXIF format tags.
    CameraHub tags from the API will be JSON-formatted whereas EXIF
    tags are formatted as a simple dictionary. This will also translate
    tags that have different names.
    """
    # Retrieve the flattened walk data as a list of lists
    data = walk(l_apidata)

    # Make a new dictionary of EXIF data to return
    l_exifdata = {}

    # Each item is one member of the nested structure
    for row in data:
        # The value is the last member of the list
        l_value = row.pop()

        # If the value is not None, build its key by concating the path
        if l_value is not None:
            l_key = ('.'.join(row))

            # Check for "special" tags that need computation
            if l_key == 'negative.latitude':
                l_exifdata['gps_latitude'] = deg_to_dms(l_value)
                l_exifdata['gps_latitude_ref'] = gps_ref('latitude', l_value)
            elif l_key == 'negative.longitude':
                l_exifdata['gps_longitude'] = deg_to_dms(l_value)
                l_exifdata['gps_longitude_ref'] = gps_ref('longitude', l_value)
            else:
                # Otherwise do a 1:1 mapping
                exifkey = apitag2exiftag(l_key)
                if exifkey is not None:
                    l_exifdata[exifkey] = l_value

    return l_exifdata


def apitag2exiftag(apitag):
    """
    When given a CameraHub API tag, flattened and formatted with dots,
    map it to its equivalent EXIF tag, or return None
    https://exif.readthedocs.io/en/latest/api_reference.html#image-attributes
    """

    #'Lens',
    #'FNumber'

    # Static mapping of tags
    mapping = {
        'uuid': 'image_unique_id',
        'negative.film.camera.cameramodel.manufacturer.name': 'make',
        'negative.film.camera.cameramodel.lens_manufacturer': 'lens_make',
        'negative.film.camera.cameramodel.model': 'model',
        'negative.film.camera.serial': 'body_serial_number',
        'negative.film.exposed_at': 'iso_speed',
        'negative.lens.lensmodel.model': 'lens_model',
        'negative.lens.lensmodel.manufacturer.name': 'lens_make',
        'negative.exposure_program': 'exposure_program',
        'negative.metering_mode': 'metering_mode',
        'negative.caption': 'image_description',
        'negative.date': 'datetime_original',
        'negative.aperture': 'f_number',
        'negative.notes': 'user_comment',
        'negative.focal_length': 'focal_length',
        'negative.flash': 'flash',
        'negative.photographer.name': 'artist',
        'negative.lens.serial': 'lens_serial_number',
        'negative.shutter_speed': 'shutter_speed_value',
        'negative.lens.lensmodel.max_aperture': 'max_aperture_value',
        'negative.copyright': 'copyright',
        'negative.focal_length_35mm': 'focal_length_in_35mm_film',
    }

    exiftag = mapping.get(apitag)
    return exiftag


def deg_to_dms(decimal):
    """
    Convert from decimal degrees to degrees, minutes, seconds.
    """
    decimal = Decimal(decimal)
    minute, second = divmod(abs(decimal)*3600, 60)
    degree, minute = divmod(minute, 60)
    degree, minute = int(degree), int(minute)
    return degree, minute, second


def gps_ref(direction, angle):
    """
    Return the direction of a GPS coordinate
    """
    angle=Decimal(angle)
    if direction == 'latitude':
        hemi = 'N' if angle>=0 else 'S'
    elif direction == 'longitude':
        hemi = 'E' if angle>=0 else 'W'
    else:
        hemi = None
    return hemi


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


def walk(indict, pre=None):
    """
    Walk a structured, nested dictionary and it return it as a flattened list
    Each item in the stucture is returned as a list consisting of each part of
    the hierarchy and finally the value. For example,
    """
    pre = pre[:] if pre else []
    if isinstance(indict, dict):
        for l_key, l_value in indict.items():
            if isinstance(l_value, dict):
                for l_dict in walk(l_value, pre + [l_key]):
                    yield l_dict
            elif isinstance(l_value, list) or isinstance(l_value, tuple):
                for val in l_value:
                    for l_dict in walk(val, pre + [l_key]):
                        yield l_dict
            else:
                yield pre + [l_key, l_value]
    else:
        yield pre + [indict]


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
        test_credentials(server)
    except:
        print("Creds not OK")
    else:
        print("Creds OK")

    # Read in args
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--recursive',
        help="search for scans recursively", action='store_true')
    parser.add_argument('-a', '--auto', action='store_true',
        help="don't prompt user to identify scans, only guess based on filename")
    parser.add_argument('-y', '--yes',
        help="accept all changes", action='store_true')
    parser.add_argument('-d', '--dry-run',
        help="don't write any tags", action='store_true')
    parser.add_argument('-c', '--config',
        help="path to config file", default=configpath)
    parser.add_argument('-f', '--file',
        help="image file to be tagged", type=str)
    parser.add_argument('-s', '--server',
        help="CameraHub server to connect to", default="https://camerahub.info/api", type=str)
    args = parser.parse_args()

    # Get our initial connection settings
    # Prompt the user to set them if they don't exist
    server = get_setting(args.config, 'Settings', 'server')
    username = get_setting(args.config, 'Settings', 'username')
    password = get_setting(args.config, 'Settings', 'password')

    # Test the credentials we have
    if test_credentials(server):
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
            existing = image.get_all()
            diff = diff_tags(existing, exifdata)

            # if non-zero diff, ask user to confirm tag write
            if len(diff) > 0:
                # print diff & confirm write
                pp = pprint.PrettyPrinter()
                pp.pprint(diff)

                if not args.dry_run and yes_or_no("Write this metadata to the file?"):

                    # Apply the diff to the image
                    for key, value in diff.items():
                        image.set(key, value)

                    # do the write
                    with open(file, 'wb') as image_file:
                        image_file.write(image.get_file())
