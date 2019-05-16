import simpy
import random
import string
import functools

"""
    In this library the data is transmitted. That means using Content Store to use in-network storage.
    Now the ants need to check whether the data is in the CS, and if so, they need to create a Data packet as a response.
"""

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
    def __init__(self, creator, time, size, name, lifetime, p_id, ant=False, data=None):
        self.creator = creator
        self.time = time
        self.size = size
        self.name = name  # The name of the content
        self.mode = 0  # 0 means Interest packet, 1 means Data packet
        self.data = data
        self.id = p_id
        self.ant = ant
        self.lifetime = lifetime
        self.default_time = lifetime

    def __repr__(self):
        return "name: {}, id: {}, ant: {} time: {}, life: {}, size: {}, mode:{}, creator: {}, data: {}".\
            format(self.name, self.id, self.ant, self.time, self.lifetime, self.size, self.mode, self.creator,  self.data)

    def add_data(self, data):
        self.data = data


class Consumer(object):
    def __init__(self, env, name):
        self.name = name
        self.env = env
        self.id = random.randrange(9999999)
        self.interface = None
        self.store = simpy.Store(env)  # The queue of pkts in the internal process
        self.action = env.process(self.run())  # starts the run() method as a SimPy process
        self.receivedPackets = list()
        self.waitingPackets = list()

    def request(self, name):
        # TODO It will generate packets in a specified interval
        # It will send 10 ants to form a path and
        # once the first one arrived back in a form of Data packet it will send the Data request
        yield self.env.timeout(random.uniform(0.0, 20.0))
        for i in range(10):
            yield self.env.timeout(functools.partial(random.expovariate, 0.5)())  # generate packets at random speed
            pkt = Packet(self.name, self.env.now, random.randint(50, 100), name, 20, self.id, True)
            self.id += 1
            self.interface.packets.put(pkt)
        # yield self.env.timeout(functools.partial(random.expovariate, 0.9)())
        data = Packet(self.name, self.env.now, random.randint(1500, 2000), name, 20, self.id)
        self.id += 1
        print("Generated: " + str(data))
        self.interface.packets.put(data)

    def run(self):
        # It will listen for packets in the store to process
        while True:
            item = (yield self.store.get())
            iface = item[0]
            pkt = item[1][1]
            # Might be Interest packets going backwards than need to be moved forward again
            if pkt.mode == 0:
                # print("...Back to Consumer...")
                # print(pkt)
                iface.packets.put(pkt)
            else:
                pkt.time = self.env.now - pkt.time
                if pkt.data is not None:
                    if isinstance(pkt.data, list):
                        self.env.process(self.request_chunks(pkt.data))
                    self.receivedPackets.append(pkt)
            # TODO Might use the packet for stadistics and then erase it from memory

    def add_interface(self, iface):
        self.interface = iface

    def request_chunks(self, data):
        # It will listen for packets in the store to process
        for name, i in zip(data, range(len(data))):
            for j in range(5):
                yield self.env.timeout(0.2)
                pkt = Packet(self.name, self.env.now, random.randint(50, 100), name, 20, self.id, True)
                self.id += 1
                self.interface.packets.put(pkt)
            if i > 2:
                yield self.env.timeout(3)
            pkt = Packet(self.name, self.env.now, random.randint(1500, 2000), name, 20, self.id)
            self.id += 1
            self.interface.packets.put(pkt)


class Producer(object):
    def __init__(self, env, names, name):
        self.name = name
        self.interface = None
        self.store = simpy.Store(env)  # The queue of pkts in the internal process
        self.data = dict()  # List with the data names of the producer
        for _name in names:
            self.create_data(self, _name)
        self.action = env.process(self.listen())

    @staticmethod
    def create_data(self, name):
        chunks = dict()
        # Create 10 chunks of data from a specific content name
        for i in range(10):
            chunk_name = str(name) + "/" + str(i+1)
            # Create some random data of size 10 bits
            chunks[chunk_name] = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        self.data[name] = chunks

    def listen(self):
        # It will listen for packets in the store to process
        while True:
            item = (yield self.store.get())
            iface = item[0]
            pkt = item[1][1]
            # It receive an Interest packet and creates the Data packet for it
            if pkt.mode == 0:
                gen_name = ''  # Initialize a general name from the content
                if '/' in pkt.name:
                    # To avoid a possible error we first treat the string to be used in the if statement
                    gen_name = pkt.name.rsplit('/', 1)[0]
                # The content name is the general one
                if pkt.name in self.data:
                    if not pkt.ant:
                        pkt.creator = self.name
                        pkt.add_data(list(self.data[pkt.name].keys()))
                    pkt.lifetime = pkt.default_time
                    pkt.mode = 1  # Convert the Interest packet in Data packet
                # The content name is a specific chunk name from one of the contents stored in the Producer
                elif self.data[gen_name]:
                    if not pkt.ant:
                        pkt.creator = self.name
                        pkt.add_data(self.data[gen_name][pkt.name])
                    pkt.lifetime = pkt.default_time
                    pkt.mode = 1  # Convert the Interest packet in Data packet
                # If the content is there the packet is modified to Data, else it is returned as it is
                iface.packets.put(pkt)
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
        self.timeout = 20  # TODO Assign it properly  # It is the time to live in the table
        self.PAT = PAT()
        self.PIT = PIT()
        self.FIB = FIB()
        self.CS = CS()
        self.action = env.process(self.run())  # starts the run() method as a SimPy process
        self.action2 = env.process(self.evaporate())  # starts the run() method as a SimPy process
        self.dist = functools.partial(random.expovariate, 1.0)

    def run(self):
        while True:
            item = (yield self.store.get())
            iface = item[0]
            pkt = item[1][1]

            if pkt.mode == 0 and pkt.ant:
                # Here ant packets process
                # Check CS for data objects
                # If the data is in the CS create Data packet and return it
                if pkt.name in self.CS.table:
                    pkt.lifetime = pkt.default_time
                    pkt.mode = 1  # Convert the Interest packet in Data packet
                    self.CS.table[pkt.name].lifetime = self.timeout
                    iface.packets.put(pkt)
                else:
                    # Just save the first interface the packet come from, avoiding further loops
                    if pkt.id not in self.PAT.table:
                        entry = PATobject(pkt.id, pkt.name, iface, self.timeout)
                        self.PAT.table[pkt.id] = entry  # Add the Interest packet
                    out_iface = self.forward_engine(pkt)  # The ForwardEngine decides outgoing interface
                    out_iface.packets.put(pkt)  # The packet is sent to the out iface
            elif pkt.mode == 0 and not pkt.ant:
                # Here content packets are processed
                # Check CS for data objects
                if pkt.name in self.CS.table:
                    pkt.add_data(self.CS.table[pkt.name].data)  # Add data to the packet
                    pkt.lifetime = pkt.default_time
                    pkt.mode = 1  # Convert the Interest packet in Data packet
                    self.CS.table[pkt.name].lifetime = self.timeout
                    iface.packets.put(pkt)
                else:
                    if pkt.name in self.PIT.table:
                        if pkt.id in self.PIT.table[pkt.name].ids:
                            out_iface = iface
                            while out_iface is iface:
                                out_iface = self.forward_engine(pkt)  # The ForwardEngine decides outgoing interface
                            out_iface.packets.put(pkt)  # The packet is sent to the out iface
                        else:
                            self.PIT.table[pkt.name].incoming[iface] = self.timeout
                    else:
                        # Create entry in the PIT table for the Interest packet
                        self.PIT.table[pkt.name] = PITobject(pkt.name, pkt.id, iface, self.timeout)
                        out_iface = iface
                        while out_iface is iface:
                            out_iface = self.forward_engine(pkt)  # The ForwardEngine decides outgoing interface
                        out_iface.packets.put(pkt)  # The packet is sent to the out iface
            elif pkt.mode == 1 and pkt.ant:
                if pkt.id in self.PAT.table:
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
                    entry2 = self.PAT.table.pop(pkt.id)
                    # Take incoming iface from PAT
                    in_iface = entry2.interface
                    # Send Data packet back to the incoming interface
                    in_iface.packets.put(pkt)

            elif pkt.mode == 1 and not pkt.ant:
                # Create entry in FIB OR UPDATE IT
                pheromone = 1  # TODO Specify pheromone value
                # The node has already received a Data packet (ant or content) with that name
                if pkt.name in self.FIB.table:
                    self.FIB.table[pkt.name].outgoings[iface] += pheromone
                # The node never received a Data packet with that name before
                else:
                    entry = FIBobject(pkt.name, iface, self.interfaces, pheromone)
                    self.FIB.table[pkt.name] = entry

                # TODO Cache Data if strategy says so
                if pkt.name in self.CS.table:
                    self.CS.table[pkt.name].lifetime = self.timeout
                else:
                    cache = CSobject(pkt.name, pkt.data, self.timeout)
                    self.CS.table[pkt.name] = cache

                # Remove entry in PIT
                # Take incoming iface from PIT
                # Send Data packet back to the incoming interface
                entry = self.PIT.table.pop(pkt.name)  # Retrieve and remove the Interest entry for pkt.name
                for in_iface, y in entry.incoming.items():  # Loops the interfaces assigned to that name
                    in_iface.packets.put(pkt)  # sends the pkt further to that interfaces
            else:
                # Drop packet
                print("Wrong packet\n")

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

    # Returns the list of entries in FIB which match the general name of the content requested
    # If returns empty list, there is no record on that name nor its domains.
    # It checks the different domain levels of the content name, differentiated by '/'
    def domain_matching(self, name):
        dest = []
        for i in range(len(name.split('/'))):
            gen_name = name.rsplit('/', i)[0]
            for key in self.FIB.table:
                if gen_name in key:
                    dest.append(self.FIB.table[key])
            if dest:
                break
        return dest

    # Returns a dict with the interfaces of the node and the sum of pheromone for each entry in the FIB partially
    # matching @name.
    def domain_iface(self, name):
        fib_ob = dict()
        # Initialize list with node's interfaces
        for iface in self.interfaces:
            fib_ob[iface] = 0.0
        # Update list with pheromone amounts
        for entry in self.domain_matching(name):
            for iface, pher in entry.outgoings.items():
                fib_ob[iface] += pher
        return fib_ob

    def forward_engine(self, pkt):
        # The heuristic function deciding which outgoing interface is going to be chosen
        # Different function for ants and for content, the power strength the decision when content is routed

        if self.domain_matching(pkt.name):
            # If there is an exact match of the content name in the FIB
            if pkt.name in self.FIB.table:
                if pkt.ant:
                    pwr = 1
                else:
                    pwr = 2
                entry = self.FIB.table[pkt.name].outgoings
            # There is at least one partial match of the content name in the FIB
            else:
                entry = self.domain_iface(pkt.name)
                pwr = 0.5
            total = 0.0
            for i in entry.values():
                total += i ** pwr
            rand = random.uniform(0.0, total)
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
            for ant_id in ids:
                self.PAT.table.pop(ant_id)
            # Emptying PIT
            llista = []
            for name, pit_object in self.PIT.table.items():
                pits = []
                for iface, time in pit_object.incoming.items():
                    if time < 2:
                        pits.append(iface)
                        print(str(self.env.now) + str(iface.name) + "was deleted from " + str(name) + " from " + str(self.name))
                    else:
                        pit_object.incoming[iface] -= 1
                for iface in pits:
                    pit_object.incoming.pop(iface)
                    if not pit_object.incoming:
                        llista.append(name)
            for name in llista:
                self.PIT.table.pop(name)
                print(str(self.env.now) + str(name) + "was deleted from " + str(self.name))


class NodeMonitor(object):
    def __init__(self, env, nodes):
        self.env = env
        self.nodes = nodes
        self.pat = []
        self.pit = []
        self.pit_size = []
        self.cs = []
        self.fib = dict()
        for node in self.nodes:
            self.fib[node.name] = {interface.name: [] for interface in node.interfaces}
        self.times = []
        self.dist = functools.partial(random.expovariate, 1)
        self.action = env.process(self.run())

    def run(self):
        while True:
            yield self.env.timeout(self.dist())
            # Save time
            self.times.append(self.env.now)
            # fibs = {}
            pats = {}
            pits = {}
            css = {}
            for node in self.nodes:
                # Save PAT info
                pats[node.name] = len(node.PAT.table)
                # Save PIT info
                tot_pit = 0
                for entry in node.PIT.table.values():
                    tot_pit += len(entry.incoming)
                pits[node.name] = tot_pit
                # Save CS info
                css[node.name] = list(node.CS.table.keys())
                # Save FIB info

                for iface in node.interfaces:
                    dict_cont = {entry.name: pheromone
                                 for entry in node.FIB.table.values()
                                 for iface2, pheromone in entry.outgoings.items()
                                 if iface2 is iface}

                    # for entry in node.FIB.table.values():
                    #     for iface2, pher in entry.outgoings.items():
                    #         dict_cont[iface2.name] = pher
                    #     llista[entry.name] = dict_cont

                    self.fib[node.name][iface.name].append(dict_cont)
            self.pat.append(pats)
            self.pit_size.append(pits)
            self.cs.append(css)


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
                time = (pkt.size * 8.0) / (self.rate * 1000)
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
        self.table = dict()  # Dict with name as a key, values incoming interface


class PAT(object):
    def __init__(self, ):
        self.table = dict()  # Dict with id as a key, values incoming interface and content name


class CS(object):
    def __init__(self, ):
        self.table = dict()  # list of CS objects


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
    def __init__(self, name, p_id, interface, lifetime):
        self.name = name
        self.ids = [p_id]
        self.incoming = {interface: lifetime}  # dictionary with (interface,lifetime)


class PATobject(object):
    def __init__(self, serial, name, interface, lifetime):
        self.serial = serial  # Serial number of the ant
        self.name = name
        self.interface = interface
        self.lifetime = lifetime


class CSobject(object):
    def __init__(self, name, data, lifetime):
        self.name = name
        self.data = data
        self.lifetime = lifetime
