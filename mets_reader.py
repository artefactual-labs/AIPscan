import metsrw

mets = metsrw.METSDocument.fromfile(
    "downloads/2020-03-19--19:54:46/1e11edbd-d19c-4afa-9ac4-cd656f675f68.xml"
)

for file in mets.all_files():
    if file.use == "original":
        print("original: " + file.label + "\n" + "uuid: " + file.file_uuid)
        for premis_object in file.get_premis_objects():
            print("format: " + str(premis_object.format_name))
            if str(premis_object.format_version) != "(('format_version',),)":
                print("version: " + str(premis_object.format_version))
            print("\n")

# f = open("files.txt", "w")
# f.write(str(mets.all_files()))
# f.close()
