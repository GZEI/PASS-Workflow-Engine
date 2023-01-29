from thespian.actors import *
import mydirector
import myIOActor

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


if __name__ == "__main__":
    """Starts and stops the server side actor system"""
    logging.basicConfig(level=logging.DEBUG)
    asys = ActorSystem("multiprocTCPBase", {"Server": True})
    sa = asys.createActor(SimpleSourceAuthority)
    asys.tell(sa, True)
    asys.createActor(mydirector.MyDirector, globalName="MyDirector")
    asys.createActor(myIOActor.MyIOActor, globalName="MyIOActor")
    input("Enter zum beenden....")
    asys.shutdown()
