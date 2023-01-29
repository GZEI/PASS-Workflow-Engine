import logging
from re import T

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
    """Actual director source code"""
    availableSource = dict()
    runningActors = dict()

    def __init__(self):
        logging.warning("DIRECTOR: Started")

    def receiveMsg_RegisteringSource(self, message, sender):
        logging.warning("DIRECTOR: Successfully registered " + message.Hash + "with start actor " + message.SourceName)
        self.availableSource[message.Hash] = message.SourceName

    def receiveMsg_UnRegisteringSource(self, message, sender):
        if message.Hash in self.availableSource.keys():
            self.unloadActorSource(message.Hash)
            self.availableSource.pop(message.Hash)
            logging.warning("DIRECTOR: Successfully unregistered " + message.Hash)
            self.send(sender, "DIRECTOR: Successfully unregistered " + message.Hash)
        else:
            logging.warning("DIRECTOR: Tried to unload unregistered source!")
            self.unloadActorSource(message.Hash)
            self.send(sender, "DIRECTOR: Tried to unload unregistered source!")

    def receiveMsg_str(self, message, sender):
        if message == "available":
            self.send(sender, self.availableSource)
            logging.warning("DIRECTOR: Sent current sources list")
        else:
            self.send(sender, self.runningActors)
            logging.warning("DIRECTOR: Sent current running list")

    def receiveMsg_StartSource(self, message, sender):
        if message.Hash in self.availableSource.keys():
            newActor = self.createActor(message.StartActor, sourceHash=message.Hash)
            self.send(sender, newActor)
            self.send(newActor, message.payload)
        else:
            self.send(sender, 0)

    def receiveMsg_StopActor(self, message, sender):
        actor_to_stop = self.runningActors.get(message.instance_id)
        if actor_to_stop is not None:
            self.send(actor_to_stop, ActorExitRequest())
            logging.warning("DIRECTOR: Successfully send exit Request")
            self.runningActors.pop(message.instance_id)
        else:
            logging.warning("DIRECTOR: Running actor not found")

    def receiveMsg_dict(self, message, sender):
        if "unregister" in message:
            i = message.get("unregister")
            process_instance = self.runningActors.get(i)
            if process_instance is not None:
                self.runningActors[i]["cnt"] = self.runningActors[i]["cnt"] - 1
                self.runningActors[i]["addr"][message.get("subject_name")].remove(sender)
                if self.runningActors[i]["cnt"] < 1:
                    if self.runningActors.pop(i, None) is not None:
                        logging.warning("DIRECTOR: Removed instance as requested")
                    else:
                        logging.warning("DIRECTOR: Could not remove instance, not found in dict")
        if "register" in message:
            i = message.get("register")
            process_instance = self.runningActors.get(i)
            if process_instance is not None:
                self.runningActors[i]["cnt"] = self.runningActors[i]["cnt"] + 1
                if message.get("subject_name") in self.runningActors[i]["addr"]:
                    self.runningActors[i]["addr"][message.get("subject_name")].append(sender)
                else:
                    self.runningActors[i]["addr"][message.get("subject_name")] = [sender]
                tmp = self.runningActors[i]["addr"].copy()
                tmp["type"] = "addressbook"
                for actor_address_list in self.runningActors[i]["addr"].values():
                    logging.warning("DIRECTOR: Send current running: " + str(tmp))
                    for actor in actor_address_list:
                        self.send(actor, tmp)
            else:
                self.runningActors[i] = dict()
                self.runningActors[i]["cnt"] = 1
                self.runningActors[i]["addr"] = {message.get("subject_name"): [sender]}
