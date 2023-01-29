from thespian.actors import *


class ListRequest:
    def __init__(self, content):
        self.content = content


class ResponseIOMessage:
    def __init__(self, payload):
        self.payload = payload


@requireCapability("Server")
class MyIOActor(ActorTypeDispatcher):
    """Empty class to allow the management interface to interact with the global class"""
    pass
