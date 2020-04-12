__author__ = "Peter Van Garderen"
__email__ = "peter@artefactual.com"

import os
import metsrw
import xml.etree.ElementTree as ET
import datetime
from AIPscan import db
from .models import aips, files


def parse_mets(fetchJob):
    with os.scandir(fetchJob.download_directory) as dir:
        for file in dir:
            if file.name.endswith(".xml") and file.is_file():
                print("parsing " + file.name)
                # metsrw library does not give access to original Transfer Name
                # which is often more useful to end-users than the AIP uuid
                # so we'll take the extra processing hit here to retrieve it
                metsTree = ET.parse(file)
                dmdSec1 = metsTree.find(
                    "{http://www.loc.gov/METS/}dmdSec[@ID='dmdSec_1']"
                )
                for element in dmdSec1.getiterator():
                    if element.tag == "{http://www.loc.gov/premis/v3}originalName":
                        originalName = element.text
                        break
                metsDate = metsTree.find("{http://www.loc.gov/METS/}metsHdr").get(
                    "CREATEDATE"
                )
                aip = aips(
                    uuid=file.name[:-4],
                    transfer_name=originalName[:-37],
                    create_date=datetime.datetime.strptime(
                        metsDate, "%Y-%m-%dT%H:%M:%S"
                    ),
                    fetch_job_id=fetchJob.id,
                )
                db.session.add(aip)
                db.session.commit()
    return ()
