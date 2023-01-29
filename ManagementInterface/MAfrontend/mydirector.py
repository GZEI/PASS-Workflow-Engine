from thespian.actors import *


class RegisteringSource:
    SourceName = ""
    Hash = ""

    def __init__(self, source_hash):
        self.Hash = source_hash

    def __str__(self):
        return self.Hash


class UnRegisteringSource:
    Hash = ""

    def __init__(self, source_hash):
        self.Hash = source_hash

    def __str__(self):
        return self.Hash


class StartSource(RegisteringSource):
    payload = ""

    def __init__(self, source_hash, start_actor, payload):
        self.Hash = source_hash
        self.StartActor = start_actor
        self.payload = payload

    def __str__(self):
        return self.Hash


class StopActor:
    instance_id = ""

    def __init__(self, instance_id):
        self.instance_id = instance_id

    def __str__(self):
        return self.instance_id


@requireCapability("Server")
class MyDirector(ActorTypeDispatcher):
    """Empty class to allow the management interface to interact with the global class"""
    pass