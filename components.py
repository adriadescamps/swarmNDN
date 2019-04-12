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
    def __init__(self, time, size, name, flow_id=0):
        self.time = time
        self.size = size
        self.name = name
        #self.flow_id = flow_id

    def __repr__(self):
        return "name: {}, time: {}, size: {}".\
            format(self.name, self.time, self.size)

class SwitchPort(object):
    """ Models a switch output port with a given rate and buffer size limit in bytes.
        Set the "out" member variable to the entity to receive the packet.

        Parameters
        ----------
        env : simpy.Environment
            the simulation environment
        rate : float
            the bit rate of the port
        qlimit : integer (or None)
            a buffer size limit in bytes or packets for the queue (including items
            in service).
        limit_bytes : If true, the queue limit will be based on bytes if false the
            queue limit will be based on packets.

    """
    def __init__(self, env, rate, qlimit=None, limit_bytes=True, debug=False):
        self.store = simpy.Store(env)
        self.rate = rate
        self.env = env
        self.out = None
        self.packets_rec = 0
        self.packets_drop = 0
        self.qlimit = qlimit
        self.limit_bytes = limit_bytes
        self.byte_size = 0  # Current size of the queue in bytes
        self.debug = debug
        self.busy = 0  # Used to track if a packet is currently being sent
        self.action = env.process(self.run())  # starts the run() method as a SimPy process

class Node(object):
    def __init__(self, name, interfaces):
        self.name = name
        self.interfaces = interfaces

class Interface(object):
    def __init__(self, ):


class ForwardEngine(object):
    def __init__(self, ):


class FIB(object):
    def __init__(self):
        self.table = list() #list of FIB objects

class PIT(object):
    def __init__(self, ):
        self.table = list() #Dict with name as a key, values incoming interface

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
        self.incoming = dict() #dictionary with (interface,lifetime)

class PATobject(object):
    def __init__(self, id, name, interface, lifetime):
        self.id = id #Serial number of the ant
        self.name = name
        self.incoming = dict() #dictionary with (interface,lifetime)

class CSobject(object):
    # def __init__(self, name):
    #     self.name = name
    #     self.outgoings = dict() #Dictionary with (interface, pheromone)

    def __init__(self, name, interface, pheromone):
        self.name = name
        self.outgoings = dict() #Dictionary with (interface, pheromone)
        self.outgoings[interface] = pheromone