"""
Utility functions with few external dependencies
"""

from decimal import Decimal
from uuid import UUID
import re
import piexif

def deg_to_dms(degrees):
    """
    Convert from decimal degrees to degrees, minutes, seconds.
    """
    degrees = Decimal(degrees)
    mins, secs = divmod(abs(degrees)*3600, 60)
    degs, mins = divmod(mins, 60)
    degs, mins = int(degs), int(mins)
    return degs, mins, secs


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
        for key, value in indict.items():
            if isinstance(value, dict):
                for d in walk(value, pre + [key]):
                    yield d
            elif isinstance(value, (list, tuple)):
                for v in value:
                    for d in walk(v, pre + [key]):
                        yield d
            else:
                yield pre + [key, value]
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
    l_film = input(f"Enter film ID for {filename}: ")
    l_frame = input(f"Enter frame ID for {l_film}: ")
    return (l_film, l_frame)


def sort_tags(l_apidata):
    """
    Given a list of tags from the API, sort them into EXIF tags
    and GPS tags, and return two lists
    """

    # Supported tags
    valid_ifd_tags = ['Make', 'Model', 'Copyright', 'ImageDescription', 'Artist']
    valid_exif_tags = ['ImageUniqueID', 'BodySerialNumber', 'UserComment', 'FocalLength', 'FocalLengthIn35mmFilm', 'ShutterSpeedValue',  'ISOSpeed',  'LensSerialNumber', 'LensModel', 'LensMake', 'FNumber', 'MaxApertureValue', 'DateTimeOriginal', 'ExposureProgram', 'MeteringMode', 'Flash']
    valid_gps_tags = ['GPSLatitude', 'GPSLongitude']

    l_ifddata = {}
    l_exifdata = {}
    l_gpsdata = {}

    for (tag, value) in l_apidata.items():
        if (value is None or value == ''):
            continue

        if tag in valid_ifd_tags:
            l_ifddata[tag] = value
        elif tag in valid_exif_tags:
            l_exifdata[tag] = value
        elif tag in valid_gps_tags:
            l_gpsdata[tag] = value

    return l_ifddata, l_exifdata, l_gpsdata


def encode_ifd(l_apidata):
    """
    Take a dict of tags and map them to Piexif properties
    """

    zeroth_ifd = {
        piexif.ImageIFD.Make: l_apidata.get('Make'),
        piexif.ImageIFD.Model: l_apidata.get('Model'),
        piexif.ImageIFD.Copyright: l_apidata.get('Copyright'),
        piexif.ImageIFD.ImageDescription: l_apidata.get('ImageDescription'),
        piexif.ImageIFD.Artist: l_apidata.get('Artist'),
    }

    sanitised = {}
    for (tag, value) in zeroth_ifd.items():
        if value:
            sanitised[tag] = value

    return sanitised


def encode_exif(l_apidata):
    """
    Take a dict of tags and map them to Piexif properties
    """

    exif_ifd = {
        piexif.ExifIFD.ImageUniqueID: l_apidata.get('ImageUniqueID'),
        piexif.ExifIFD.BodySerialNumber: l_apidata.get('BodySerialNumber'),
        piexif.ExifIFD.UserComment: l_apidata.get('UserComment'),
        piexif.ExifIFD.FocalLength: l_apidata.get('FocalLength'),
        piexif.ExifIFD.FocalLengthIn35mmFilm: l_apidata.get('FocalLengthIn35mmFilm'),
        piexif.ExifIFD.ShutterSpeedValue: l_apidata.get('ShutterSpeedValue'),
        piexif.ExifIFD.ISOSpeed: l_apidata.get('ISOSpeed'),
        piexif.ExifIFD.LensSerialNumber: l_apidata.get('LensSerialNumber'),
        piexif.ExifIFD.LensModel: l_apidata.get('LensModel'),
        piexif.ExifIFD.LensMake: l_apidata.get('LensMake'),
        piexif.ExifIFD.FNumber: l_apidata.get('FNumber'),
        piexif.ExifIFD.MaxApertureValue: l_apidata.get('MaxApertureValue'),
        piexif.ExifIFD.DateTimeOriginal: l_apidata.get('DateTimeOriginal'),
        piexif.ExifIFD.ExposureProgram: l_apidata.get('ExposureProgram'),
        piexif.ExifIFD.MeteringMode: l_apidata.get('MeteringMode'),
        piexif.ExifIFD.Flash: l_apidata.get('Flash'),
    }

    sanitised = {}
    for (tag, value) in exif_ifd.items():
        if value:
            sanitised[tag] = value

    return sanitised


def encode_gps(l_apidata):
    """
    Take a dict of tags and map them to Piexif properties
    """

    gps_ifd = {
        piexif.GPSIFD.GPSLatitude: l_apidata.get('GPSLatitude'),
        piexif.GPSIFD.GPSLongitude: l_apidata.get('GPSLongitude'),
    }

    sanitised = {}
    for (tag, value) in gps_ifd.items():
        if value:
            sanitised[tag] = value

    return sanitised
