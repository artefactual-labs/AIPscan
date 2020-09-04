# -*- coding: utf-8 -*-

"""Collects a number of reusable components of tasks.py. Also ensures
the module remains clean and easy to refactor over time.
"""
import os


def get_mets_url(api_url, package_uuid, path_to_mets):
    """Construct a URL from which we can download the METS files that
    we are interested in.
    """
    am_url = "baseUrl"
    user_name = "userName"
    api_key = "apiKey"

    mets_url = "{}/api/v2/file/{}/extract_file/?relative_path_to_file={}&username={}&api_key={}".format(
        api_url[am_url],
        package_uuid,
        path_to_mets,
        api_url[user_name],
        api_url[api_key],
    )
    return mets_url


def create_numbered_subdirs(timestamp, package_list_number):
    """Check for the existence and create a container folder for our
    METS files as required.
    """
    AGGREGATOR_DOWNLOADS = os.path.join("AIPscan", "Aggregator", "downloads")
    METS_FOLDER = "mets"

    # Create a package list numbered subdirectory if it doesn't exist.
    numbered_subdir = os.path.join(
        AGGREGATOR_DOWNLOADS, timestamp, METS_FOLDER, str(package_list_number)
    )
    if not os.path.exists(numbered_subdir):
        os.makedirs(numbered_subdir)

    return numbered_subdir
