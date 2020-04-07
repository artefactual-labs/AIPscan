__author__ = "Peter Van Garderen"
__email__ = "peter@artefactual.com"

import os
import metsrw
import json
import xml.etree.ElementTree as ET

downloadDirectory = "downloads/2020-04-05--20:02:45"
aipFilesInfo = {}

with os.scandir(downloadDirectory) as dir:
    for file in dir:
        if file.name.endswith(".xml") and file.is_file():
            mets = metsrw.METSDocument.fromfile(file.path)
            aipUuid = file.name[:-4]

            # metsrw library does not give access to original Transfer Name
            # which is often more useful to end-users than the AIP uuid
            # so we'll take the extra processing hit here to retrieve it
            metsTree = ET.parse(file)
            metsRoot = metsTree.find("{http://www.loc.gov/METS/}dmdSec[@ID='dmdSec_1']")
            for element in metsRoot.getiterator():
                if element.tag == "{http://www.loc.gov/premis/v3}originalName":
                    originalName = element.text
                    break
            transferName = originalName[:-37]

            for aipFile in mets.all_files():

                if aipFile.use == "original":
                    aipFilesInfo[aipFile.file_uuid] = []
                    aipFilesInfo[aipFile.file_uuid].append(
                        {
                            "file name": aipFile.label,
                            "file type": "original",
                            "transfer name": transferName,
                            "AIP uuid": aipUuid,
                        }
                    )
                    # this exception handler had to be added because METSRW throws
                    # the error: "metsrw/plugins/premisrw/premis.py", line 644, in _to_colon_ns
                    # parts = [x.strip("{") for x in bracket_ns.split("}")]"
                    # AttributeError: 'cython_function_or_method' object has no attribute 'split'
                    # for .iso file types
                    try:
                        for premis_object in aipFile.get_premis_objects():
                            # it would be nice if we could access premis_object.original_name
                            # this would allow us to parse a human readable name for the AIP
                            aipFilesInfo[aipFile.file_uuid].append(
                                {
                                    "file size": str(premis_object.size) + " bytes",
                                    "puid": str(premis_object.format_registry_key),
                                    "file format": str(premis_object.format_name),
                                }
                            )
                            if (
                                str(premis_object.format_version)
                                != "(('format_version',),)"
                            ):
                                aipFilesInfo[aipFile.file_uuid].append(
                                    {
                                        "file format version": str(
                                            premis_object.format_version
                                        )
                                    }
                                )
                    except:
                        pass
                    for premis_event in aipFile.get_premis_events():
                        if (str(premis_event.event_type)) == "ingestion":
                            aipFilesInfo[aipFile.file_uuid].append(
                                {"ingestion date": premis_event.event_date_time}
                            )
                    if str(premis_object.related_object_identifier_value) != "()":
                        aipFilesInfo[aipFile.file_uuid].append(
                            {
                                "preservation copy uuid": str(
                                    premis_object.related_object_identifier_value
                                )
                            }
                        )

            for aipFile in mets.all_files():
                if aipFile.use == "preservation":
                    aipFilesInfo[aipFile.file_uuid] = []
                    aipFilesInfo[aipFile.file_uuid].append(
                        {
                            "file name": aipFile.label,
                            "file type": "preservation copy",
                            "transfer name": transferName,
                            "AIP uuid": aipUuid,
                        }
                    )
                    for premis_object in aipFile.get_premis_objects():
                        aipFilesInfo[aipFile.file_uuid].append(
                            {
                                "file size": str(premis_object.size) + " bytes",
                                "normalization date": premis_event.event_date_time,
                                "file format": str(premis_object.format_name),
                            }
                        )
                        if (
                            str(premis_object.format_version)
                            != "(('format_version',),)"
                        ):
                            aipFilesInfo[aipFile.file_uuid].append(
                                {"version: " + str(premis_object.format_version)}
                            )

with open(downloadDirectory + "/_aip-file-info.json", "w") as json_file:
    json.dump(aipFilesInfo, json_file, indent=4)
