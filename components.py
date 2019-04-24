import simpy
import random
import copy
from simpy.core import BoundClass
from simpy.resources import base
from heapq import heappush, heappop


class Packet(object):
    """ A very simple class that represents a packet.
        This packet will run through a queue at a switch output port.
        We use a float to represent the size of the packet in bytes so that
        we can compare to ideal M/M/1 queues.

        Parameters
        ----------
        time : float
            the time the packet arrives at the output queue.
        size : float
            the size of the packet in bytes
        id : int
            an identifier for the packet
        src, dst : int
            identifiers for source and destination
        flow_id : int
            small integer that can be used to identify a flow
    """
    def __init__(self, time, size, name, lifetime, antid=None):
        self.time = time
        self.size = size
        self.name = name #The name will contain "/ant/" in case of being a routing packet before the content name
        self.mode = 0 # 0 means Interest packet, 1 means Data packet
        self.data = None
        self.antId = antid
        self.lifetime = lifetime

    def __repr__(self):
        return "name: {}, time: {}, size: {}".\
            format(self.name, self.time, self.size)

class Consumer(object):
    def __init__(self):
        self.antId = random.randrange(9999999)
        self.interface
        self.store

    def request_content(self, name):
        #TODO It will generate packets in a specified interval
        # It will send 10 ants to form a path and once the first one arrived back in a form of Data packet it will send the Data request

    def listen(self):
        # TODO It will listen for packets in the store to process
        # TODO Might use the packet for stadistics and then erase it from memory


class Producer(object):
    def __init__(self, data):
        self.interface
        self.store
        self.data = data #List with the data names of the producer

    def createData(self):
        # TODO Create some random data

    def listen(self):
        # TODO It will listen for packets in the store to process
        # TODO It receive an Interest packet and creates the Data packet for it


class Node(object):
    def __init__(self, env, name, interfaces):
        self.store = simpy.Store(env) #The queue of pkts in the node
        self.name = name
        self.interfaces = interfaces
        self.timeout = 50 #TODO Assign it properly #It is the time to live in the table
        self.PAT = PAT()
        self.PIT = PIT()

    def run(self):
        while True:
            item = (yield self.store.get())
            iface = item[0]
            pkt = item[1]

            if "/ant/Interest/" in pkt.name and pkt.antId is not None:
                #Here ant packets process
                self.antId+=1
                entry = PATobject(pkt.antId, pkt.name, iface, self.timeout)
                self.PAT.table[self.antId] = entry #Add the Interest packet
                out_iface = self.forward_engine(pkt.mode) #The ForwardEngine decides outgoing interface
                out_iface.out_iface.put(pkt) #The packet is sent to the out iface
            elif "/Interest/" in pkt.name and pkt.antId is None:
                #Here content packets are processed
                if pkt.name in self.PIT.table:
                    self.PIT.table[pkt.name].incoming[iface] = self.timeout
                else:
                    self.PIT.table[pkt.name] = PITobject(pkt.name,iface,self.timeout) #Create entry in the PIT table for the Interest packet
                    out_iface = self.forward_engine(pkt.mode) #The ForwardEngine decides outgoing interface
                    out_iface.out_iface.put(pkt) #The packet is sent to the out iface
            elif "/ant/Data/" in pkt.name and pkt.antId is not None:
                if pkt.antId in self.PAT.table:
                    # TODO Create entry in FIB OR UPDATE IT
                    # TODO Update pheromone in the FIB

                    #Remove entry in PAT
                    entry = self.PAT.table.pop(pkt.antId)
                    #Take incoming iface from PAT
                    in_iface = entry.interface
                    #Send Data packet back to the incoming interface
                    in_iface.put(pkt)

            elif "/Data/" in pkt.name and pkt.antId is None:
                    # TODO Create entry in FIB OR UPDATE IT
                    # TODO Update pheromone in the FIB
                    # TODO Cache Data if strategy says so

                    # Remove entry in PIT
                    # Take incoming iface from PIT
                    # Send Data packet back to the incoming interface
                    entry = self.PIT.table.pop(pkt.name) #Retrieve and remove the Interest entry for pkt.name
                    for in_iface,y in entry.incoming.items(): #Loops the interfaces assigned to that name
                        in_iface.put(pkt) #sends the pkt further to that interfaces
            else:
                #Drop packet
                print("Wrong packet\n")

    def forward_engine(self,mode):
        #TODO The holistic function deciding which outgoing interface is going to be chosen
        #TODO Different function for ants and for content
        iface = random.choices(self.interfaces) #Just for not getting an error in the meantime
        return iface


class Interface(object):
    def __init__(self, name, iface, store):
        self.name = name
        self.out_iface = iface
        self.out = store #Gonna point to the Node, consumer or producer with iface store

    def put(self, pkt):
        self.out.put([self,pkt])

class FIB(object):
    def __init__(self):
        self.table = list() #list of FIB objects

class PIT(object):
    def __init__(self, ):
        self.table = list() #Dict with name as a key, values incoming interface

class PAT(object):
    def __init__(self, ):
        self.table = dict() #Dict with id as a key, values incoming interface and content name

class CS(object):
    def __init__(self, ):
        self.table = list()  # list of CS objects

class FIBobject(object):
    def __init__(self, name, interface, pheromone):
        self.name = name
        self.outgoings = dict() #Dictionary with (interface, pheromone)

class PITobject(object):
    def __init__(self, name, interface, lifetime):
        self.name = name
        self.incoming = {interface: lifetime} #dictionary with (interface,lifetime)

class PATobject(object):
    def __init__(self, id, name, interface, lifetime):
        self.id = id #Serial number of the ant
        self.name = name
        self.interface = interface
        self.lifetime = lifetime

class CSobject(object):
    def __init__(self, name, data):
        self.name = name
        self.data = data