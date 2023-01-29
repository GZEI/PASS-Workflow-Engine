import itertools

from thespian.actors import *


class ListRequest:
    def __init__(self, content):
        self.content = content


class ResponseIOMessage:
    def __init__(self, payload):
        self.payload = payload


@requireCapability("Server")
class MyIOActor(ActorTypeDispatcher):
    pending_requests = dict()
    pending_requests_addr = dict()
    id_iter = itertools.count()

    def __init__(self):
        logging.warning("IOActor: Started")

    def receiveMsg_int(self, msg, sender):
        self.pending_requests_addr.pop(msg, None)
        self.pending_requests.pop(msg, None)

    def receiveMsg_dict(self, msg, sender):
        logging.warning("IOActor: Received IO Request")
        idx = next(self.id_iter)
        self.pending_requests[idx] = msg
        self.pending_requests_addr[idx] = sender
        self.send(sender, {"type": "ioack", "id": idx})

    def receiveMsg_ListRequest(self, msg, sender):
        self.send(sender, self.pending_requests)

    def receiveMsg_ResponseIOMessage(self, msg, sender):
        for idx, value in msg.payload.items():
            value["type"] = "ioresponse"
            self.send(self.pending_requests_addr[idx], value)
            del self.pending_requests_addr[idx]
            del self.pending_requests[idx]

    def receiveMsg_ActorExitRequest(self, msg, sender):
        logging.warning("IOActor: EXITING")

    def receiveUnrecognizedMessage(self, message, sender):
        logging.warning("IOActor: Did not recognize the message type: %s" % type(message))
