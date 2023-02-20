import myIOActor
import mydirector
from thespian.actors import *


class SimpleSourceAuthority(Actor):
    """Allows every source to be loaded, taken from the samples available in the documentation"""

    def receiveMessage(self, msg, sender):
        if msg is True:
            self.registerSourceAuthority()
        if isinstance(msg, ValidateSource):
            self.send(sender,
                      ValidatedSource(msg.sourceHash,
                                      msg.sourceData,
                                      getattr(msg, 'sourceInfo', None)))


class ActorSystemManager:
    """A singleton that holds information about the management actor system"""
    __instance = None
    __asys = None
    __director = None
    __ioactor = None
    __ready = False

    @staticmethod
    def getInstance():
        """ Static access method. """
        if ActorSystemManager.__instance == None:
            ActorSystemManager()
        return ActorSystemManager.__instance

    def __init__(self):
        """ Virtually private constructor. """
        if ActorSystemManager.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            ActorSystemManager.__instance = self

    def startActorSystem(self):
        if self.__asys is None:
            capabilities = dict([('Admin Port', 1901),
                                 ('Convention Address.IPv4', ('127.0.0.1', 1900)),
                                 ])
            asys = ActorSystem('multiprocTCPBase', capabilities)
            sa = asys.createActor(SimpleSourceAuthority)
            asys.tell(sa, True)
            self.__asys = asys
            self.__ioactor = asys.createActor(myIOActor.MyIOActor, globalName="MyIOActor")
            self.__director = asys.createActor(mydirector.MyDirector, globalName="MyDirector")
            self.__ready = True
        elif not self.__ready:
            self.__asys.shutdown()
            self.__asys = None
        return self.__asys

    def stopActorSystem(self):
        self.startActorSystem()
        self.__asys.shutdown()
        self.__asys = None

    def getIOActor(self):
        return self.__ioactor

    def getDirector(self):
        return self.__director

    def __del__(self):
        self.stopActorSystem()


def loadSource(filename, start_actors):
    logging.basicConfig(level=logging.DEBUG)
    try:
        actorSystemManager = ActorSystemManager.getInstance()
        asys = actorSystemManager.startActorSystem()
        myDirector = actorSystemManager.getDirector()
        source_hash = asys.loadActorSource(filename)
        print("Hash of loaded file: " + source_hash)
        asys.tell(myDirector, mydirector.RegisteringSource(source_hash))
        for start_actor in start_actors:
            newActor = asys.createActor(start_actor, sourceHash=source_hash)
            asys.tell(newActor, ActorExitRequest())
        return source_hash
    except Exception as e:
        raise Exception(str(e))


def startSource(start_actor, hash, payload):
    logging.basicConfig(level=logging.DEBUG)
    try:
        actorSystemManager = ActorSystemManager.getInstance()
        asys = actorSystemManager.startActorSystem()
        myDirector = actorSystemManager.getDirector()
        ioActor = actorSystemManager.getIOActor()
        payload["director"] = myDirector
        payload["ioactor"] = ioActor
        payload["addressbook"] = dict()
        tmp = asys.ask(myDirector, mydirector.StartSource(hash, start_actor, payload))
        if tmp != 0:
            print(tmp)
        else:
            raise Exception("Instance not available on the server, please redeploy!")
    except Exception as e:
        raise Exception(str(e))


def ask_running_actors():
    logging.basicConfig(level=logging.DEBUG)
    try:
        actorSystemManager = ActorSystemManager.getInstance()
        asys = actorSystemManager.startActorSystem()
        myDirector = actorSystemManager.getDirector()
        running_actors = asys.ask(myDirector, "list")
        if running_actors is None:
            actorSystemManager.stopActorSystem()
            return dict()
        return running_actors
    except Exception as e:
        actorSystemManager.stopActorSystem()
        raise Exception("Server not available, please check!")


def ask_pending_requests():
    logging.basicConfig(level=logging.DEBUG)
    try:
        actorSystemManager = ActorSystemManager.getInstance()
        asys = actorSystemManager.startActorSystem()
        ioActor = actorSystemManager.getIOActor()
        pending_requests = asys.ask(ioActor, myIOActor.ListRequest("None"))
        if pending_requests is None:
            actorSystemManager.stopActorSystem()
            return dict()
        return pending_requests
    except Exception as e:
        actorSystemManager.stopActorSystem()
        raise Exception("Server not available, please check!")


def respond_pending_request(payload):
    logging.basicConfig(level=logging.DEBUG)
    try:
        actorSystemManager = ActorSystemManager.getInstance()
        asys = actorSystemManager.startActorSystem()
        ioActor = actorSystemManager.getIOActor()
        return asys.tell(ioActor, myIOActor.ResponseIOMessage(payload))
    except Exception as e:
        raise Exception(str(e))
