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
                mets = metsrw.METSDocument.fromfile(file.path)
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
                aip = aips(
                    uuid=file.name[:-4],
                    transfer_name=originalName[:-37],
                    create_date=datetime.datetime.strptime(
                        mets.createdate, "%Y-%m-%dT%H:%M:%S"
                    ),
                    fetch_job_id=fetchJob.id,
                )
                db.session.add(aip)
                db.session.commit()

                for aipFile in mets.all_files():
                    if (aipFile.use == "original") or (aipFile.use == "preservation"):
                        name = aipFile.label
                        type = aipFile.use
                        uuid = aipFile.file_uuid
                        puid = None
                        formatVersion = None
                        relatedUuid = None
                        creationDate = None
                        ingestionDate = None
                        normalizationDate = None

                        # this exception handler had to be added because METSRW throws
                        # the error: "metsrw/plugins/premisrw/premis.py", line 644, in _to_colon_ns
                        # parts = [x.strip("{") for x in bracket_ns.split("}")]"
                        # AttributeError: 'cython_function_or_method' object has no attribute 'split'
                        # for .iso file types
                        # try:
                        for premis_object in aipFile.get_premis_objects():
                            size = premis_object.size
                            if (
                                str(premis_object.format_registry_key)
                            ) != "(('format_registry_key',),)":
                                if (str(premis_object.format_registry_key)) != "()":
                                    puid = premis_object.format_registry_key
                            format = premis_object.format_name
                            if (
                                str(premis_object.format_version)
                            ) != "(('format_version',),)":
                                if (str(premis_object.format_version)) != "()":
                                    formatVersion = premis_object.format_version
                            if (
                                str(premis_object.related_object_identifier_value)
                                != "()"
                            ):
                                relatedUuid = (
                                    premis_object.related_object_identifier_value
                                )
                            if aipFile.use == "original":
                                creationDate = str(
                                    premis_object.date_created_by_application
                                )
                        # except:
                        # pass

                        for premis_event in aipFile.get_premis_events():
                            if (premis_event.event_type) == "ingestion":
                                ingestionDate = premis_event.event_date_time
                            if (premis_event.event_type) == "creation":
                                normalizationDate = premis_event.event_date_time
                        file = files(
                            name=name,
                            type=type,
                            uuid=uuid,
                            size=size,
                            puid=puid,
                            format=format,
                            format_version=formatVersion,
                            related_uuid=relatedUuid,
                            creation_date=creationDate,
                            ingestion_date=ingestionDate,
                            normalization_date=normalizationDate,
                            aip_id=aip.id,
                        )
                        db.session.add(file)
                        db.session.commit()
    return ()
