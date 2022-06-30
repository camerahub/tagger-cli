"""
Functions which interact with the CameraHub API
"""

from datetime import date
import json
import requests

def test_credentials(l_server, l_auth):
    """
    Validate a set of credentials
    :param server:
    :param username:
    :param password:
    :return: Bool
    """

    response = requests.get(
            l_server+'/camera',
            auth=l_auth
        )

    return bool(response.status_code == 200)


def create_scan(l_negative, l_filename, l_server, l_auth):
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
    url = l_server+'/scan/'
    response = requests.post(url, auth=l_auth, data = data)
    response.raise_for_status()
    data=json.loads(response.text)
    return data["uuid"]


def get_scan(l_scan, l_server, l_auth):
    """
    Get all details about a scan record in CameraHub
    """
    payload = {'uuid': l_scan}
    url = l_server+'/exif/'
    response = requests.get(url, auth=l_auth, params=payload)
    response.raise_for_status()

    data=json.loads(response.text)
    if data["count"] == 1:
        scan = data["results"][0]

    return scan


def get_negative(l_film, l_frame, l_server, l_auth):
    """
    Find the negative slug for a negative based on its film slug and frame
    """
    # TODO: complete this function with API lookup
    slug = f"{l_film}.{l_frame}"
    payload = {'slug': slug}
    url = l_server+'/negative/'
    response = requests.get(url, auth=l_auth, params=payload)
    response.raise_for_status()

    data=json.loads(response.text)
    if data["count"] == 1:
        negative = data["results"][0]["slug"]

    return negative
