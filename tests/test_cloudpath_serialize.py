import pickle

from cloudpathlib import CloudPath


def test_pickle(rig, tmpdir):
    p = rig.create_cloud_path("dir_0/file0_0.txt")

    with (tmpdir / "test.pkl").open("wb") as f:
        pickle.dump(p, f)

    with (tmpdir / "test.pkl").open("rb") as f:
        pickled = pickle.load(f)

    # test a call to the network
    assert pickled.exists()

    # check we unpickled, and that client is the default client
    assert str(pickled) == str(p)
    assert pickled.client == p.client
    assert rig.client_class._default_client == pickled.client


def test_pickle_roundtrip():
    path1 = CloudPath("s3://bucket/key")
    pkl1 = pickle.dumps(path1)

    path2 = pickle.loads(pkl1)
    pkl2 = pickle.dumps(path2)

    assert path1 == path2
    assert path1._url == path2._url
    assert pkl1 == pkl2


def test_pickle_preserves_explicit_local_cache_dir(rig, tmpdir):
    """A path bound to a client with an explicitly configured persistent
    ``local_cache_dir`` keeps that cache directory across a pickle round-trip.

    The client itself is not pickled (sessions are not pickleable), but the
    cache directory is explicit configuration the user chose on purpose, so the
    restored path must reuse the same directory instead of silently falling back
    to a fresh temporary one. Regression test for
    https://github.com/drivendataorg/cloudpathlib/issues/504 -- without this the
    unpickled path pointed at a different cache dir and re-downloaded already
    cached files (notably under multiprocessing, where pickling is required).
    """
    cache_dir = str(tmpdir / "explicit_cache")

    client = rig.client_class(local_cache_dir=cache_dir, **rig.required_client_kwargs)
    p = rig.create_cloud_path("dir_0/file0_0.txt", client=client)

    assert str(p.client._local_cache_dir) == cache_dir

    pickled = pickle.loads(pickle.dumps(p))

    # the restored path resolves to the same explicitly-configured cache dir
    assert str(pickled.client._local_cache_dir) == cache_dir
    # ... which means its _local maps under that directory, not a fresh temp dir
    assert str(pickled._local).startswith(cache_dir)
