import metsrw

mets = metsrw.METSDocument.fromfile(
    "downloads/2020-03-19--19:54:46/3706e0f8-5ab5-4a26-8927-2a7796a24043.xml"
)

# f = open("files.txt", "w")
# f.write(str(mets.all_files()))
# f.close()

for file in mets.all_files():
    if file.use == "original":
        print("original file: " + file.label + "\n" + "file uuid: " + file.file_uuid)
        for premis_object in file.get_premis_objects():
            print("puid: " + str(premis_object.format_registry_key))
            print("file format: " + str(premis_object.format_name))
            if str(premis_object.format_version) != "(('format_version',),)":
                print("version: " + str(premis_object.format_version))
            if str(premis_object.related_object_identifier_value) != "()":
                print(
                    "preservation copy uuid: "
                    + str(premis_object.related_object_identifier_value)
                )
            print("")

for file in mets.all_files():
    if file.use == "preservation":
        print(
            "preservation copy: " + file.label + "\n" + "file uuid: " + file.file_uuid
        )
        for premis_object in file.get_premis_objects():
            print("file format: " + str(premis_object.format_name))
            if str(premis_object.format_version) != "(('format_version',),)":
                print("version: " + str(premis_object.format_version))
            print("")
