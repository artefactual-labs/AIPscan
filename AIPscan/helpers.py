def GetHumanReadableFilesize(size, precision=2):
    suffixes = ["B", "KiB", "MiB", "GiB", "TiB"]
    suffixIndex = 0
    while size > 1024 and suffixIndex < 4:
        suffixIndex += 1  # increment the index of the suffix
        size = size / 1024.0  # apply the division
    return "%.*f %s" % (precision, size, suffixes[suffixIndex])
