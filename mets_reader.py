import os
import metsrw

downloadDirectory = "downloads/2020-04-05--20:02:45"

with os.scandir(downloadDirectory) as dir:
    for file in dir:
        if file.name.endswith(".xml") and file.is_file():
            mets = metsrw.METSDocument.fromfile(file.path)
            aipUuid = file.name[:-4]

            for aipFile in mets.all_files():

                if aipFile.use == "original":
                    print("AIP uuid: " + aipUuid)
                    print("file type: original")
                    print(
                        "file name: "
                        + aipFile.label
                        + "\n"
                        + "file uuid: "
                        + aipFile.file_uuid
                    )
                    # this exception handler had to be added because METSRW throws
                    # the error: "metsrw/plugins/premisrw/premis.py", line 644, in _to_colon_ns
                    # parts = [x.strip("{") for x in bracket_ns.split("}")]"
                    # AttributeError: 'cython_function_or_method' object has no attribute 'split'
                    # for .iso file types
                    try:
                        for premis_object in aipFile.get_premis_objects():
                            print("puid: " + str(premis_object.format_registry_key))
                            print("file format: " + str(premis_object.format_name))
                            if (
                                str(premis_object.format_version)
                                != "(('format_version',),)"
                            ):
                                print("version: " + str(premis_object.format_version))
                            print("file size: " + str(premis_object.size) + " bytes")
                    except:
                        pass
                    for premis_event in aipFile.get_premis_events():
                        if (str(premis_event.event_type)) == "ingestion":
                            print("ingestion date: " + premis_event.event_date_time)
                    if str(premis_object.related_object_identifier_value) != "()":
                        print(
                            "preservation copy uuid: "
                            + str(premis_object.related_object_identifier_value)
                        )
                    print("")

            for aipFile in mets.all_files():
                if aipFile.use == "preservation":
                    print("AIP uuid: " + aipUuid)
                    print("file type: preservation copy")
                    print(
                        "file name: "
                        + aipFile.label
                        + "\n"
                        + "file uuid: "
                        + aipFile.file_uuid
                    )
                    for premis_object in aipFile.get_premis_objects():
                        print("file format: " + str(premis_object.format_name))
                        if (
                            str(premis_object.format_version)
                            != "(('format_version',),)"
                        ):
                            print("version: " + str(premis_object.format_version))
                        print("file size: " + str(premis_object.size) + " bytes")
                        print("normalization date: " + premis_event.event_date_time)
                    print("")
