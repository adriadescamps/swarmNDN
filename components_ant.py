import simpy
import random
import string
import functools

random.seed(2)


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
        ant_id : int
            an identifier for the packet
        name : string
            name of the content requested
    """
    def __init__(self, creator, time, size, name, lifetime, ant_id=None, data=None):
        self.creator = creator
        self.time = time
        self.size = size
        self.name = name  # The name of the content
        self.mode = 0  # 0 means Interest packet, 1 means Data packet
        self.data = data
        self.antId = ant_id
        self.lifetime = lifetime
        self.default_time = lifetime

    def __repr__(self):
        return "name: {}, antID: {}, time: {}, life: {}, size: {}, mode:{}, data: {}".\
            format(self.name, self.antId, self.time, self.lifetime, self.size, self.mode, self.data)

    def add_data(self, data):
        self.data = data


class Consumer(object):
    def __init__(self, env, name):
        self.name = name
        self.env = env
        self.antId = random.randrange(9999999)
        self.interface = None
        self.store = simpy.Store(env)  # The queue of pkts in the internal process
        self.names = simpy.Store(env)  # The queue of pkts in the internal process
        self.action = env.process(self.run())  # starts the run() method as a SimPy process
        self.action2 = env.process(self.listen())  # starts the run() method as a SimPy process
        self.receivedPackets = list()

    def run(self):
        # It will send 10 ants to form a path and
        # once the first one arrived back in a form of Data packet it will send the Data request

        while True:
            # First Scenario - We send a single request to a specific content name
            name = (yield self.names.get())
            for i in range(10):
                yield self.env.timeout(functools.partial(random.expovariate, 0.9)())  # generate packets at random speed
                pkt = Packet(self.name, self.env.now, random.randint(80, 100), name, 20, self.antId)
                # print(pkt)
                self.antId += 1
                self.interface.packets.put(pkt)

    def listen(self):
        # It will listen for packets in the store to process
        while True:
            item = (yield self.store.get())
            iface = item[0]
            pkt = item[1][1]
            # Might be Interest packets going backwards than need to be moved forward again
            if pkt.mode == 0:
                # print("...Back to Consumer...")
                iface.packets.put(pkt)
            else:
                pkt.time = self.env.now - pkt.time
                self.receivedPackets.append(pkt)
                # print("\nConsumer received back: " + str(pkt))
            # TODO Might use the packet for stadistics and then erase it from memory

    def add_interface(self, iface):
        self.interface = iface

    def request(self, name):
        self.names.put(name)


class Producer(object):
    def __init__(self, env, names):
        self.interface = None
        self.store = simpy.Store(env)  # The queue of pkts in the internal process
        self.data = dict()  # List with the data names of the producer
        for name in names:
            self.data[name] = self.create_data()
        self.action = env.process(self.listen())  # starts the run() method as a SimPy process

    @staticmethod
    def create_data():
        # Create some random data of size 10 bits
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

    def listen(self):
        # It will listen for packets in the store to process
        while True:
            item = (yield self.store.get())
            iface = item[0]
            pkt = item[1][1]
            # It receive an Interest packet and creates the Data packet for it
            if pkt.mode == 0:
                # print("Producer received: " + str(pkt))
                if pkt.name in self.data:
                    if pkt.antId is None:
                        pkt.add_data(self.data[pkt.name])
                    pkt.lifetime = pkt.default_time
                    pkt.mode = 1  # Convert the Interest packet in Data packet
                iface.packets.put(pkt)  # If the content is there the packet is modified to Data, else it is returned as it is
            else:
                print("Error - Producer received Data packet")

    def add_interface(self, iface):
        self.interface = iface


class Node(object):
    def __init__(self, env, name):
        # It is the constant for which the pheromones will be reduced each time
        self.env = env
        self.reduce_const = 0.1  # TODO Assign it properly
        self.store = simpy.Store(env)  # The queue of pkts in the node
        self.name = name
        self.interfaces = list()
        self.timeout = 30  # TODO Assign it properly  # It is the time to live in the table
        self.PAT = PAT()
        self.PIT = PIT()
        self.FIB = FIB()
        self.action = env.process(self.run())  # starts the run() method as a SimPy process
        self.action2 = env.process(self.evaporate())  # starts the run() method as a SimPy process
        self.dist = functools.partial(random.expovariate, 1.0)

    def run(self):
        while True:
            item = (yield self.store.get())
            iface = item[0]
            pkt = item[1][1]

            if pkt.mode == 0 and pkt.antId is not None:
                # Here ant packets process
                if pkt.antId not in self.PAT.table: # Just save the first interface the packet come from, avoiding further loops
                    entry = PATobject(pkt.antId, pkt.name, iface, self.timeout)
                    self.PAT.table[pkt.antId] = entry  # Add the Interest packet
                out_iface = self.forward_engine(pkt)  # The ForwardEngine decides outgoing interface
                out_iface.packets.put(pkt)  # The packet is sent to the out iface
            elif pkt.mode == 0 and pkt.antId is None:
                # Here content packets are processed
                if pkt.name in self.PIT.table:
                    self.PIT.table[pkt.name].incoming[iface] = self.timeout
                else:
                    # Create entry in the PIT table for the Interest packet
                    self.PIT.table[pkt.name] = PITobject(pkt.name, iface, self.timeout)
                    out_iface = self.forward_engine(pkt)  # The ForwardEngine decides outgoing interface
                    out_iface.packets.put(pkt)  # The packet is sent to the out iface
            elif pkt.mode == 1 and pkt.antId is not None:
                if pkt.antId in self.PAT.table:
                    # Create entry in FIB OR UPDATE IT
                    pheromone = 1  # TODO Specify pheromone value
                    # The node has already received a Data packet (ant or content) with that name
                    if pkt.name in self.FIB.table:
                        self.FIB.table[pkt.name].outgoings[iface] += pheromone
                    # The node never received a Data packet with that name before
                    else:
                        entry = FIBobject(pkt.name, iface, self.interfaces, pheromone)
                        self.FIB.table[pkt.name] = entry

                    # Remove entry in PAT
                    entry2 = self.PAT.table.pop(pkt.antId)
                    # Take incoming iface from PAT
                    in_iface = entry2.interface
                    # Send Data packet back to the incoming interface
                    in_iface.packets.put(pkt)

            elif pkt.mode == 1 and pkt.antId is None:
                # Create entry in FIB OR UPDATE IT
                pheromone = 1  # TODO Specify pheromone value
                # The node has already received a Data packet (ant or content) with that name
                if pkt.name in self.FIB.table:
                    self.FIB.table[pkt.name].outgoings[iface] += pheromone
                # The node never received a Data packet with that name before
                else:
                    entry = FIBobject(pkt.name, iface, self.interfaces, pheromone)
                    self.FIB.table[pkt.name] = entry

                # Remove entry in PIT
                # Take incoming iface from PIT
                # Send Data packet back to the incoming interface
                entry = self.PIT.table.pop(pkt.name)  # Retrieve and remove the Interest entry for pkt.name
                for in_iface, y in entry.incoming.items():  # Loops the interfaces assigned to that name
                    in_iface.packets.put(pkt)  # sends the pkt further to that interfaces
            else:
                # Drop packet
                print("Wrong packet\n")

            # print("Node " + self.name + "\n Table: " + str(self.PAT.table))

    def add_interface(self, iface):
        if isinstance(iface, list):
            for each in iface:
                if each not in self.interfaces:
                    self.interfaces.append(each)
                else:
                    print("Error - Interface already existing " + each.name)
        else:
            if iface not in self.interfaces:
                self.interfaces.append(iface)
            else:
                print("Error - Interface already existing " + iface.name)

    def forward_engine(self, pkt):
        # The heuristic function deciding which outgoing interface is going to be chosen
        # Different function for ants and for content, the power strength the decision when content is routed
        if pkt.name in self.FIB.table:
            pwr = pkt.mode + 1
            entry = self.FIB.table[pkt.name].outgoings
            total = 0
            for i in entry.values():
                total += i ** pwr
            rand = random.randint(0, int(total))
            for iface, pheromone in entry.items():
                if rand - (pheromone ** pwr) < 0:
                    return iface
                else:
                    rand -= pheromone ** pwr
        return random.choices(self.interfaces)[0]

    def evaporate(self):
        while True:
            yield self.env.timeout(self.dist())
            # Evaporate pheromones
            for fib_object in self.FIB.table.values():
                for iface, pheromone in fib_object.outgoings.items():
                    if pheromone > 1 + self.reduce_const:
                        self.FIB.table[fib_object.name].outgoings[iface] -= self.reduce_const
            # Reduce or delete PAT-PIT entries
            ids = []
            for ant_id, pat_object in self.PAT.table.items():
                if pat_object.lifetime < 2:
                    ids.append(ant_id)
                else:
                    pat_object.lifetime -= 1
            # Not applicable for data yet
            for ant_id in ids:
                self.PAT.table.pop(ant_id)
                # print("PAT " + str(self.name) + " TABLE: Emptied packet "+str(ant_id))


class NodeMonitor(object):
    def __init__(self, env, nodes):
        self.env = env
        self.nodes = nodes
        self.pat = []
        self.fib = dict()
        for node in self.nodes:
            self.fib[node.name] = []
        self.times = []
        self.dist = functools.partial(random.expovariate, 1.0)
        self.action = env.process(self.run())

    def run(self):
        while True:
            yield self.env.timeout(self.dist())
            # Save time
            self.times.append(self.env.now)
            pats = {}
            for node in self.nodes:
                # Save PAT info
                pats[node.name] = len(node.PAT.table)
                # Save FIB info
                llista = {}
                for entry in node.FIB.table.values():
                    dict_iface = dict()
                    for iface, pher in entry.outgoings.items():
                        dict_iface[iface.name] = pher
                    llista[entry.name] = dict_iface
                self.fib[node.name].append(llista)
            self.pat.append(pats)


class Interface(object):
    def __init__(self, env, name, store, iface=None, rate=1000.0):
        self.env = env
        self.name = name
        self.out_iface = iface
        self.store = store  # Gonna point to the Node, consumer or producer with iface store
        self.rate = rate
        self.packets = simpy.Store(env)
        self.action = env.process(self.send())

    def add_interface(self, iface):
        self.out_iface = iface

    def put(self, pkt):
        self.store.put([self, pkt])

    def send(self):
        while True:
            pkt = yield self.packets.get()
            if pkt.lifetime > 1:
                # print("Iface: " + str(self.env.now))
                time = pkt.size * 8.0 / self.rate
                yield self.env.timeout(time)  # Packet transmission time
                # print("Iface: " + str(time) + " - " + str(self.env.now))
                pkt.lifetime -= 1
                self.out_iface.put([self.out_iface, pkt])
            else:
                print("\n----------------------\nPacket died: {}, {}" + str(pkt))

    def __repr__(self):
        return "Interface: {}".\
            format(self.name)


class FIB(object):
    def __init__(self):
        self.table = dict()  # list of FIB objects


class PIT(object):
    def __init__(self):
        self.table = list()  # Dict with name as a key, values incoming interface


class PAT(object):
    def __init__(self, ):
        self.table = dict()  # Dict with id as a key, values incoming interface and content name


class CS(object):
    def __init__(self, ):
        self.table = list()  # list of CS objects


class FIBobject(object):
    def __init__(self, name, in_iface, interfaces, pheromone):
        self.name = name
        self.outgoings = dict()  # Dictionary with (interface, pheromone)
        for iface in interfaces:  # Creates a pair for each interface in the node with the basic amount of pheromones
            self.outgoings[iface] = 1
        self.outgoings[in_iface] += pheromone  # Increases the pheromones level for the desired iface

    def __repr__(self):
        return "\nName: {}, Pheromones: {}".\
            format(self.name, self.outgoings)


class PITobject(object):
    def __init__(self, name, interface, lifetime):
        self.name = name
        self.incoming = {interface: lifetime}  # dictionary with (interface,lifetime)


class PATobject(object):
    def __init__(self, serial, name, interface, lifetime):
        self.serial = serial  # Serial number of the ant
        self.name = name
        self.interface = interface
        self.lifetime = lifetime


class CSobject(object):
    def __init__(self, name, data):
        self.name = name
        self.data = data
