class PackageError(Exception):
    """There are things we cannot do with the package type unless it
    is completed properly. Let the user know.
    """


class StorageServicePackage:
    """Type that can record information about a storage service package
    and provide helpers as to whether or not we should process it.
    """

    default_pair_tree = "0000-0000-0000-0000-0000-0000-0000-0000-"
    compressed_ext = ".7z"

    def __init__(self, **kwargs):
        """Package constructor"""

        DELETED = "deleted"
        REPLICA = "replica"
        AIP = "aip"
        DIP = "dip"
        SIP = "sip"

        UUID = "uuid"
        CURRENT_LOCATION = "current_location"
        CURRENT_PATH = "current_path"
        ORIGIN_PIPELINE = "origin_pipeline"

        self.deleted = False
        self.replica = False
        self.aip = False
        self.dip = False
        self.sip = False
        self.uuid = None
        self.current_location = None
        self.current_path = None
        self.origin_pipeline = None

        if kwargs:
            self.deleted = kwargs.get(DELETED, self.deleted)
            self.replica = kwargs.get(REPLICA, self.replica)
            self.aip = kwargs.get(AIP, self.aip)
            self.dip = kwargs.get(DIP, self.dip)
            self.sip = kwargs.get(SIP, self.sip)
            self.uuid = kwargs.get(UUID, self.uuid)
            self.current_location = kwargs.get(CURRENT_LOCATION, self.current_location)
            self.current_path = kwargs.get(CURRENT_PATH, self.uuid)
            self.origin_pipeline = kwargs.get(ORIGIN_PIPELINE, self.origin_pipeline)

    def __repr__(self):
        ret = f"aip: '{self.aip}'; dip: '{self.dip}'; sip: '{self.sip}'; deleted: '{self.deleted}'; replica: '{self.replica}';"
        return ret

    def __eq__(self, other):
        """Comparison operator"""
        ret = True
        if self.aip != other.aip:
            ret = False
        if self.dip != other.dip:
            ret = False
        if self.sip != other.sip:
            ret = False
        if self.deleted != other.deleted:
            ret = False
        if self.replica != other.replica:
            ret = False
        if self.uuid != other.uuid:
            ret = False
        if self.current_location != other.current_location:
            ret = False
        if self.current_path != other.current_path:
            ret = False
        if self.origin_pipeline != other.origin_pipeline:
            ret = False
        return ret

    def is_aip(self):
        """Determine whether the package is a AIP"""
        if (
            self.aip
            and not self.deleted
            and not self.replica
            and not self.dip
            and not self.sip
        ):
            return True
        return False

    def is_undeleted_aip(self):
        if self.is_deleted():
            return False

        return self.is_aip()

    def is_dip(self):
        """Determine whether the package is a DIP"""
        if (
            self.dip
            and not self.deleted
            and not self.replica
            and not self.aip
            and not self.sip
        ):
            return True
        return False

    def is_sip(self):
        """Determine whether the package is a SIP"""
        if (
            self.sip
            and not self.deleted
            and not self.replica
            and not self.dip
            and not self.aip
        ):
            return True
        return False

    def is_replica(self):
        """Determine whether the package is a replica package"""
        if (
            self.replica
            and self.aip
            and not self.deleted
            and not self.sip
            and not self.dip
        ):
            return True
        return False

    def is_deleted(self):
        """Determine whether the package is a deleted package"""
        if self.deleted:
            return True
        return False

    def get_relative_path(self):
        """Return relative path from current_path."""
        if self.dip or self.sip or self.replica:
            raise PackageError(
                "Get relative path for sip or replica packages not yet implemented"
            )
        if self.deleted:
            raise PackageError("There are no relative paths for deleted packages")
        if self.uuid is None:
            raise PackageError("Cannot generate a relative path without a package UUID")
        rel = ""
        left_offset = len(self.default_pair_tree)
        right_offset = -len(self.compressed_ext)
        try:
            if self.current_path.endswith(self.compressed_ext):
                rel = self.current_path[left_offset:right_offset]
            else:
                rel = self.current_path[left_offset:]
        except AttributeError as err:
            raise PackageError("Current path doesn't exist for the package") from err
        return f"{rel}/data/METS.{self.uuid}.xml"
