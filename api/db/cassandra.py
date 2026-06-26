import os

from cassandra.cluster import Cluster

_cluster = None
_session = None


def get_session():

    global _cluster
    global _session

    if _session is None:

        host = os.getenv(
            "CASSANDRA_HOST",
            "timeseries-db"
        )

        _cluster = Cluster([host])

        _session = _cluster.connect()

    return _session


def close_session():

    global _cluster
    global _session

    if _session:
        _session.shutdown()

    if _cluster:
        _cluster.shutdown()

    _session = None
    _cluster = None