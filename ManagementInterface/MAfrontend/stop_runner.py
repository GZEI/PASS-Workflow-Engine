from thespian.actors import *

if __name__ == "__main__":
     capabilities = dict([('Admin Port', 1901),
                             ('Convention Address.IPv4', ('127.0.0.1', 1900)),
                             ])
     asys = ActorSystem('multiprocTCPBase', capabilities)
     asys.shutdown()
