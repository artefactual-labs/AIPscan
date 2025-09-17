import pytest

from AIPscan.Aggregator import types


def test_storage_service_package_init():
    """Test that the type constructor works as expected."""
    package_1 = types.StorageServicePackage()
    package_2 = types.StorageServicePackage()
    assert package_1 == package_2
    assert package_1.aip is False
    assert package_1.dip is False
    assert package_1.sip is False
    assert package_1.replica is False
    assert package_1.deleted is False


def test_storage_service_package_eq():
    """Provide some other equality tests for the type."""
    package_1 = types.StorageServicePackage(
        deleted=True, replica=False, uuid="1", current_path="2"
    )
    package_2 = types.StorageServicePackage(
        deleted=True, replica=False, uuid="1", current_path="2"
    )
    assert package_1 == package_2
    assert package_1.replica is False
    assert package_1.deleted is True
    package_3 = types.StorageServicePackage(
        deleted=1, replica=2, aip=3, dip=4, sip=5, uuid="6", current_path="7"
    )
    package_4 = types.StorageServicePackage(
        deleted=1, replica=2, aip=3, dip=4, sip=5, uuid="6", current_path="7"
    )
    assert package_3 == package_4
    assert package_3 != package_1


def test_package_ness():
    """Given specific package types check that they evaluate to true
    when queried.
    """
    package = types.StorageServicePackage(aip=True)
    assert package.is_aip()
    assert package.is_undeleted_aip()
    assert not package.is_dip()
    assert not package.is_sip()
    assert not package.is_deleted()
    assert not package.is_replica()

    package = types.StorageServicePackage(dip=True)
    assert package.is_dip()
    assert not package.is_aip()
    assert not package.is_undeleted_aip()
    assert not package.is_sip()
    assert not package.is_deleted()
    assert not package.is_replica()

    package = types.StorageServicePackage(sip=True)
    assert package.is_sip()
    assert not package.is_dip()
    assert not package.is_aip()
    assert not package.is_undeleted_aip()
    assert not package.is_deleted()
    assert not package.is_replica()

    package = types.StorageServicePackage(deleted=True)
    assert package.is_deleted()
    assert not package.is_replica()
    assert not package.is_aip()
    assert not package.is_undeleted_aip()
    assert not package.is_dip()
    assert not package.is_aip()

    package = types.StorageServicePackage(aip=True, deleted=True)
    assert package.is_deleted()
    assert not package.is_replica()
    assert not package.is_aip()
    assert not package.is_undeleted_aip()
    assert not package.is_dip()
    assert not package.is_aip()

    package = types.StorageServicePackage(aip=True, replica=True)
    assert package.is_replica()
    assert not package.is_deleted()
    assert not package.is_aip()
    assert not package.is_undeleted_aip()
    assert not package.is_dip()
    assert not package.is_aip()


@pytest.mark.parametrize(
    "package, result",
    [
        (
            types.StorageServicePackage(
                uuid="91940daf-5c33-4670-bfc8-9108f32bca7b",
                current_path="9194/0daf/5c33/4670/bfc8/9108/f32b/ca7b/repl-91940daf-5c33-4670-bfc8-9108f32bca7b.7z",
            ),
            "repl-91940daf-5c33-4670-bfc8-9108f32bca7b/data/METS.91940daf-5c33-4670-bfc8-9108f32bca7b.xml",
        ),
        (
            types.StorageServicePackage(
                uuid="902192d9-6232-4d5f-b6c4-dfa7b8733960",
                current_path="9021/92d9/6232/4d5f/b6c4/dfa7/b873/3960/repl-902192d9-6232-4d5f-b6c4-dfa7b8733960.7z",
            ),
            "repl-902192d9-6232-4d5f-b6c4-dfa7b8733960/data/METS.902192d9-6232-4d5f-b6c4-dfa7b8733960.xml",
        ),
        (
            types.StorageServicePackage(
                deleted=True,
                uuid="594a03f3-d8eb-4c83-affd-aefaf75d53cc",
                current_path="594a/03f3/d8eb/4c83/affd/aefa/f75d/53cc/delete_me-594a03f3-d8eb-4c83-affd-aefaf75d53cc.7z",
            ),
            None,
        ),
        (
            types.StorageServicePackage(
                uuid="e422c724-834c-4164-a7be-4c881043a531",
                current_path="e422/c724/834c/4164/a7be/4c88/1043/a531/normalize-e422c724-834c-4164-a7be-4c881043a531.7z",
            ),
            "normalize-e422c724-834c-4164-a7be-4c881043a531/data/METS.e422c724-834c-4164-a7be-4c881043a531.xml",
        ),
        (
            types.StorageServicePackage(
                uuid="583c009c-4255-44b9-8868-f57e4bade93c",
                current_path="583c/009c/4255/44b9/8868/f57e/4bad/e93c/normal_aip-583c009c-4255-44b9-8868-f57e4bade93c.7z",
            ),
            "normal_aip-583c009c-4255-44b9-8868-f57e4bade93c/data/METS.583c009c-4255-44b9-8868-f57e4bade93c.xml",
        ),
        (
            types.StorageServicePackage(
                uuid="846fca2b-0919-4673-804c-0f626a30cabd",
                current_path="846f/ca2b/0919/4673/804c/0f62/6a30/cabd/uncomp-846fca2b-0919-4673-804c-0f626a30cabd",
            ),
            "uncomp-846fca2b-0919-4673-804c-0f626a30cabd/data/METS.846fca2b-0919-4673-804c-0f626a30cabd.xml",
        ),
        (
            types.StorageServicePackage(
                dip=True,
                uuid="59f70134-eeca-4886-888e-b2013a08571e",
                current_path="1555/04f5/98dd/48d1/9e97/83bc/f0a5/efa2/normcore-59f70134-eeca-4886-888e-b2013a08571e",
            ),
            None,
        ),
        (
            types.StorageServicePackage(
                uuid="59f70134-eeca-4886-888e-b2013a08571e",
                current_path="59f7/0134/eeca/4886/888e/b201/3a08/571e/normcore-59f70134-eeca-4886-888e-b2013a08571e",
            ),
            "normcore-59f70134-eeca-4886-888e-b2013a08571e/data/METS.59f70134-eeca-4886-888e-b2013a08571e.xml",
        ),
        (
            types.StorageServicePackage(
                sip=True,
                uuid="fbdcd607-270e-4dff-9a01-d11b7c2a0200",
                current_path="originals/backlog-fbdcd607-270e-4dff-9a01-d11b7c2a0200",
            ),
            None,
        ),
    ],
)
def test_get_relative_path(package, result):
    """Given the current_path check our ability to construct a relative
    path within a METS file.
    """
    if package.replica or package.sip or package.deleted or package.dip:
        with pytest.raises(types.PackageError):
            _ = package.get_relative_path()
    else:
        assert package.get_relative_path() == result
