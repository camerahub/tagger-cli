"""
CameraHub Tagger
"""

import argparse
import sys
import os
from fnmatch import filter as fnfilter
import pprint
import piexif
from requests.models import HTTPError
from funcs import is_valid_uuid, guess_frame, prompt_frame, api2exif, diff_tags, yes_or_no, api2gps
from config import get_setting
from api import get_negative, get_scan, create_scan, test_credentials

# ----------------------------------------------------------------------
if __name__ == '__main__':
    print("CameraHub Tagger")

    # Read in args
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--recursive', help="search for scans recursively", action='store_true')
    parser.add_argument('-a', '--auto', help="don't prompt user to identify scans, only guess based on filename", action='store_true')
    parser.add_argument('-y', '--yes', help="accept all changes", action='store_true')
    parser.add_argument('-d', '--dry-run', help="don't write any tags", action='store_true')
    parser.add_argument('-f', '--file', help="image file to be tagged", type=str)
    parser.add_argument('-p', '--profile', help="CameraHub connection profile", default='prod', type=str)
    args = parser.parse_args()

    # Determine path to config file
    home = os.path.expanduser("~")
    configpath = os.path.join(home, "camerahub.ini")

    # Get our initial connection settings
    # Prompt the user to set them if they don't exist
    server = get_setting(configpath, args.profile, 'server')
    username = get_setting(configpath, args.profile, 'username')
    password = get_setting(configpath, args.profile, 'password')

    # Create auth object
    auth = (username, password)

    # Test the credentials we have
    try:
        test_credentials(server, auth)
    except:
        print("Creds not OK")
        raise PermissionError
    else:
        print("Creds OK")


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
        files = fnfilter(os.listdir('.'), '*.[Jj][Pp][Gg]')

    if len(files) == 0:
        print("No files found")
        sys.exit

    # foreach found photo:
    # read exif data, check for camerahub scan tag
    for file in files:
        print(f"Processing image {file}")

        # Extract all metadata from file
        image_metadata = piexif.load(file)

        if image_metadata and image_metadata['Exif']['ImageUniqueID'] and is_valid_uuid(image_metadata['Exif']['ImageUniqueID']):
            # check for presence of custom exif tag for camerahub
            # already has a uuid scan id
            print(f"{file} already has an EXIF scan ID")

        else:
            # need to match it with a neg/print and generate a scan id
            print(f"{file} does not have an EXIF scan ID")

            # else prompt user to identify the scan
            #	guess film/frame from filename
            guess = guess_frame(file)
            if guess:
                film, frame = guess
                print(f"Deduced Film ID {film} and Frame {frame}")

            else:
                print(f"{file} does not match FILM-FRAME notation")
                # prompt user for film/frame
                #	either accept film/frame or just film then prompt frame
                film, frame = prompt_frame(file)

            # Lookup Negative from API
            try:
                negative = get_negative(film, frame, server, auth)
            except HTTPError as err:
                print(err)
                continue
            except:
                print(f"Couldn't find Negative ID for {file}")
                continue
            else:
                print(f"{file} corresponds to Negative {negative}")

            # Create Scan record associated with the Negative
            try:
                scan = create_scan(negative, file, server, auth)
            except:
                print(f"Couldn't generate Scan ID for Negative {negative}")
                continue
            else:
                print(f"Created new Scan ID {scan}")

        # Lookup extended Scan details in API
        try:
            apidata = get_scan(scan, server, auth)
        except:
            print(f"Couldn't retrieve data for Scan {scan}")
        else:
            print(f"Got data for Scan {scan}")

            # mangle CameraHub format tags into EXIF and GPS format tags
            api_exif = api2exif(apidata)
            api_gps = api2gps(apidata)

            # prepare diff of tags
            image_exif = {}
            for key, value in image_metadata['Exif']:
                image_exif[key] = value
            image_gps = {}
            for key, value in image_metadata['GPS']:
                image_gps[key] = value            

            diff_exif = diff_tags(image_exif, api_exif)
            diff_gps = diff_tags(image_gps, api_gps)
            diff = diff_exif + diff_gps

        # if non-zero diff, ask user to confirm tag write
        if len(diff) > 0:
            # print diff & confirm write
            pp = pprint.PrettyPrinter()
            pp.pprint(diff)

            if not args.dry_run and yes_or_no("Write this metadata to the file?"):

                    # Apply the changes to the image exif
                    image_exif = image_exif | api_exif
                    image_gps = image_gps | api_gps

                    # Reconstruct the metadata for writing
                    image_metadata = {"Exif": image_exif, "GPS":image_gps}
                    exif_bytes = piexif.dump(image_metadata)

                    # Do the write
                    piexif.insert(exif_bytes, file)
