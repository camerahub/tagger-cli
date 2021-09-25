# CameraHub Tagger

Command-line app to tag JPG scans of negatives with EXIF metadata from the CameraHub API.
This means you can organise your film scans in a digital photo management app with full metadata.

## Installation

This app will be available on PyPI when it is finished.

## Usage

### `-r --recursive`

Search for scans recursively from current directory

### `-a --auto`

Don't prompt user to identify scans, only guess based on filename

### `-y --yes`

Accept all changes

### `-d --dry-run`

Don't write any tags

### `-f --file`

Image file to be tagged. If not supplied, tag everything in the current directory.

### `-p' --profile`

CameraHub connection profile. Default: `prod`.
