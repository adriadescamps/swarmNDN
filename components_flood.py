import copy

import simpy
import random
import string
import functools

"""
    In this library the data is transmitted. That means using Content Store to use in-network storage.
    Now the ants need to check whether the data is in the CS, and if so, they need to create a Data packet as a response.
"""


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
        self.trail = []

    def __repr__(self):
        return "name: {}, id: {}, ant: {} time: {}, life: {}, size: {}, mode:{}, creator: {}, data: {}".\
            format(self.name, self.id, self.ant, self.time, self.lifetime, self.size, self.mode, self.creator,  self.data)

    def __lt__(self, other):
        return self.mode > other.mode or (self.mode == other.mode and self.id < other.id)

    def add_data(self, data):
        self.data = data


class Consumer(object):
    def __init__(self, env, name, delay=0, mode=0):
        self.name = name
        self.mode = mode # 0 = Ant routing, 1 = flooding
        self.env = env
        self.delay = delay
        self.id = random.randrange(9999999)
        self.interface = None
        self.store = simpy.Store(env)  # The queue of pkts in the internal process
        self.action = env.process(self.run())  # starts the run() method as a SimPy process
        self.receivedPackets = dict()
        self.wastedPackets = list()
        self.sentPackets = list()
        self.lifetime = 100
        self.received = []

    def request(self, name, delay=0):
        # TODO It will generate packets in a specified interval
        # It will send 10 ants to form a path and
        # once the first one arrived back in a form of Data packet it will send the Data request
        yield self.env.timeout(self.delay+delay)  # Wait to start requesting packets
        if self.mode == 0:  # If using ant routing we send ants to explore
            for i in range(20):
                yield self.env.timeout(0.1)  # generate packets at fix speed
                pkt = Packet(self.name, self.env.now, random.randint(50, 100), name, self.lifetime, self.id, True)
                self.id += 1
                self.interface.packets.put(pkt)
        data = Packet(self.name, self.env.now, random.randint(1500, 2000), name, self.lifetime, self.id)
        self.id += 1
        pkt_c = copy.deepcopy(data)
        self.sentPackets.append(pkt_c)
        self.interface.packets.put(data)

    def run(self):
        # It will listen for packets in the store to process
        while True:
            item = (yield self.store.get())
            iface = item[1][0]
            pkt = item[0]
            # Might be Interest packets going backwards than need to be moved forward again
            if pkt.mode == 0:
                # print("...Back to Consumer...")
                # print(pkt)
                iface.packets.put(pkt)
            else:
                pkt.time = self.env.now - pkt.time
                if pkt.data is not None:
                    pkt.trail.append((self.name, self.env.now))
                    pkt_c = copy.deepcopy(pkt)
                    self.received.append(pkt_c)
                    if pkt.name in self.receivedPackets:
                        self.wastedPackets.append(pkt_c)
                    elif isinstance(pkt.data, list):
                        self.receivedPackets[pkt.name] = pkt_c
                        self.env.process(self.request_chunks(pkt.data))
                    else:
                        self.receivedPackets[pkt.name] = pkt_c

            # TODO Might use the packet for stadistics and then erase it from memory

    def add_interface(self, iface):
        self.interface = iface

    def request_chunks(self, data):
        # It will listen for packets in the store to process
        for name, i in zip(data, range(len(data))):
            if self.mode == 0:  # If using ant routing we send ants to explore
                for j in range(10):
                    yield self.env.timeout(0.1)
                    pkt = Packet(self.name, self.env.now, random.randint(50, 100), name, self.lifetime, self.id, True)
                    self.id += 1
                    self.interface.packets.put(pkt)
            if i > 2:
                yield self.env.timeout(3)
            pkt = Packet(self.name, self.env.now, random.randint(1500, 2000), name, self.lifetime, self.id)
            self.sentPackets.append(pkt)
            self.id += 1
            self.interface.packets.put(pkt)


class Producer(object):
    def __init__(self, env, names, name, area):
        self.name = name
        self.env = env
        self.area = area
        self.interface = None
        self.store = simpy.Store(env)  # The queue of pkts in the internal process
        self.data = dict()  # List with the data names of the producer
        for _name in names:
            self.create_data(_name)
        self.action = env.process(self.listen())
        self.received = set()
        self.wasted = []

    def create_data(self, name):
        chunks = dict()
        # Create 10 chunks of data from a specific content name
        chunks_names = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10']
        for i in chunks_names:
            chunk_name = str(self.area) + "/" + str(name) + "/" + i
            # Create some random data of size 10 bits
            chunks[chunk_name] = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        self.data[str(self.area) + "/" + str(name)] = chunks

    def listen(self):
        # It will listen for packets in the store to process
        while True:
            item = (yield self.store.get())
            iface = item[1][0]
            pkt = item[0]
            # It receive an Interest packet and creates the Data packet for it
            if pkt.mode == 0:
                gen_name = ''  # Initialize a general name from the content
                if pkt.name.count('/') > 1:
                    # To avoid a possible error we first treat the string to be used in the if statement
                    gen_name = pkt.name.rsplit('/', 1)[0]
                # The content name is the general one
                if pkt.name in self.data:
                    if not pkt.ant:
                        self.received.add(pkt.name)
                        pkt.add_data(list(self.data[pkt.name].keys()))
                        pkt.trail.append((self.name, self.env.now))
                        pkt.creator = self.name
                    pkt.lifetime = pkt.default_time
                    pkt.mode = 1  # Convert the Interest packet in Data packet
                # The content name is a specific chunk name from one of the contents stored in the Producer
                elif gen_name in self.data:
                    if not pkt.ant:
                        self.received.add(pkt.name)
                        pkt.add_data(self.data[gen_name][pkt.name])
                        pkt.trail.append((self.name, self.env.now))
                        pkt.creator = self.name
                    pkt.lifetime = pkt.default_time
                    pkt.mode = 1  # Convert the Interest packet in Data packet
                # If the content is there the packet is modified to Data, else it is returned as it is
                iface.packets.put(pkt)
            else:
                self.wasted.append(pkt)
                print("Error - Producer received Data packet")

    def add_interface(self, iface):
        self.interface = iface


class Node(object):
    def __init__(self, env, nid, name, area, mode=0):
        # It is the constant for which the pheromones will be reduced each time
        self.env = env
        self.mode = mode  # 0 is Ant routing, 1 is flood routing
        self.id = nid
        self.name = name
        self.area = area
        self.areas = ['Stavanger', 'Hammerfest', 'Lillehammer-Gjovik', 'Kirkenes', 'Kautokeino', 'Kristiansund',
                      'Haugesund', 'Svalbard', 'Kristiansand', 'Stord-Haugesund', 'Teknobyen', 'Alta', 'Oslo',
                      'Osterdalen', 'Sandnessjoen', 'Forde-Volda', 'Bergen', 'Trondheim', 'Bodo',
                      'Buskerud og Vestfold', 'Volda', 'Telemark', 'Alesund', 'Ostfold', 'Mo', 'Nesna', 'Narvik',
                      'Tromso', 'Harstad', 'Karasjok', 'Kjeller', 'Molde', 'NLH As', 'kristiansand']
        self.pkt_id = random.randrange(9999999)
        self.reduce_const = 0.05  # TODO Assign it properly
        self.pheromone = 1.5
        self.store = simpy.PriorityStore(env)  # The queue of pkts in the node
        self.interfaces = list()
        self.timeout = 1500  # TODO Assign it properly  # It is the time to live in the table
        self.PAT = PAT()
        self.PIT = PIT()
        self.FIB = FIB()
        self.CS = CS()
        self.CS.table[area] = CSobject(area, None, 0, self.name)
        self.action = env.process(self.run())  # starts the run() method as a SimPy process
        self.action2 = env.process(self.evaporate())  # starts the run() method as a SimPy process
        self.dist = functools.partial(random.expovariate, 1.0)
        self.wastedPackets = []
        self.timeouts = dict()
        self.timeoutPackets = []
        self.interestDrop = []
        self.servedData = []

    def run(self):
        if self.mode == 0:
            self.env.process(self.prepare())
        while True:
            item = (yield self.store.get())
            iface = item[1][0]
            pkt = item[0]

            if pkt.creator is not self.name:
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
                        pkt.trail.append((self.name, self.env.now))
                        pkt.creator = self.CS.table[pkt.name].producer
                        pkt.lifetime = pkt.default_time
                        pkt.mode = 1  # Convert the Interest packet in Data packet
                        self.CS.table[pkt.name].lifetime = self.timeout
                        iface.packets.put(pkt)
                    elif self.mode == 0:  # Ant routing
                        if pkt.name in self.PIT.table:
                            if pkt.id in self.PIT.table[pkt.name].ids:
                                if iface not in self.PIT.table[pkt.name].incoming:
                                    self.PIT.table[pkt.name].incoming[iface] = self.timeout
                                out_iface = list(self.PIT.table[pkt.name].incoming.keys())
                                if iface not in out_iface:
                                    out_iface.append(iface)
                                if len(out_iface) < len(self.interfaces):
                                    while iface in out_iface:
                                        iface = self.forward_engine(pkt)  # The ForwardEngine decides outgoing interface
                                    iface.packets.put(pkt)  # The packet is sent to the out iface
                                else:
                                    self.interestDrop.append(pkt)
                            else:
                                self.PIT.table[pkt.name].incoming[iface] = self.timeout
                                self.PIT.table[pkt.name].ids.append(pkt.id)
                        else:
                            # Create entry in the PIT table for the Interest packet
                            self.PIT.table[pkt.name] = PITobject(pkt.name, pkt.id, iface, self.timeout)
                            out_iface = iface
                            while out_iface is iface:
                                out_iface = self.forward_engine(pkt)  # The ForwardEngine decides outgoing interface
                            out_iface.packets.put(pkt)  # The packet is sent to the out iface
                    elif self.mode == 1:  # Flood routing
                        if pkt.name in self.PIT.table:
                            if pkt.id not in self.PIT.table[pkt.name].ids:
                                self.PIT.table[pkt.name].ids.append(pkt.id)
                            self.PIT.table[pkt.name].incoming[iface] = self.timeout
                        elif pkt.name not in self.PIT.table:
                            self.PIT.table[pkt.name] = PITobject(pkt.name, pkt.id, iface, self.timeout)
                            for out_iface in self.interfaces:
                                if out_iface is not iface:
                                    pkt_c = copy.deepcopy(pkt)
                                    out_iface.packets.put(pkt_c)
                        else:
                            self.interestDrop.append(pkt)
                elif pkt.mode == 1 and pkt.ant:
                    if pkt.id in self.PAT.table:
                        # Create entry in FIB OR UPDATE IT
                        pheromone = self.pheromone  # TODO Specify pheromone value
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
                    if self.mode == 0:  # Ant routing
                        # Create entry in FIB OR UPDATE IT
                        pheromone = self.pheromone
                        # The node has already received a Data packet (ant or content) with that name
                        if pkt.name in self.FIB.table:
                            self.FIB.table[pkt.name].outgoings[iface] += pheromone
                        # The node never received a Data packet with that name before
                        else:
                            entry = FIBobject(pkt.name, iface, self.interfaces, pheromone)
                            self.FIB.table[pkt.name] = entry

                    # Cache Data if strategy says so
                    if pkt.name in self.CS.table:
                        self.CS.table[pkt.name].lifetime = self.timeout
                    else:
                        cache = CSobject(pkt.name, pkt.data, self.timeout, pkt.creator)
                        self.CS.table[pkt.name] = cache

                    # Remove entry in PIT
                    # Take incoming iface from PIT
                    # Send Data packet back to the incoming interface
                    if pkt.name in self.PIT.table:
                        pkt.trail.append((self.name, self.env.now))
                        entry = self.PIT.table.pop(pkt.name)  # Retrieve and remove the Interest entry for pkt.name
                        self.servedData.append(entry)
                        for in_iface, y in entry.incoming.items():  # Loops the interfaces assigned to that name
                            pkt_c = copy.deepcopy(pkt)
                            in_iface.packets.put(pkt_c)  # sends the pkt further to that interfaces
                    else:
                        if not pkt.ant:
                            if pkt.name in self.timeouts:
                                self.timeoutPackets.append(pkt)
                            else:
                                self.wastedPackets.append(pkt)
                else:
                    if not pkt.ant:
                        if pkt.mode == 0:
                            self.interestDrop.append(pkt)
                        else:
                            if pkt.name in self.timeouts:
                                self.timeoutPackets.append(pkt)
                            else:
                                self.wastedPackets.append(pkt)

    def prepare(self):
        # Prepares the network with area requests so the users will fetch the data much faster
        for area in self.areas:
            if area != self.area:  # Do not send interest for your own area
                yield self.env.timeout(0.01)  # generate packets at fix speed
                for iface in self.interfaces:
                    pkt = Packet(self.name, self.env.now, 10, area, 50, self.pkt_id, True)
                    self.pkt_id += 1
                    iface.packets.put(pkt)

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
        # List of entries in the FIB matching the different domain levels of the content name
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
                    pwr = 1.5
                else:
                    pwr = 2
                entry = self.FIB.table[pkt.name].outgoings
            # There is at least one partial match of the content name in the FIB
            else:
                entry = self.domain_iface(pkt.name)
                pwr = 1
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
            fibs = []
            for fib_object in self.FIB.table.values():
                delete = True
                for iface, pheromone in fib_object.outgoings.items():
                    if pheromone > 1 + self.reduce_const:
                        self.FIB.table[fib_object.name].outgoings[iface] -= self.reduce_const
                        delete = False
                if delete:
                    fibs.append(fib_object.name)
            for fib_ob in fibs:
                self.FIB.table.pop(fib_ob)
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
                        # print(str(self.env.now) + str(iface.name) + "was deleted from " + str(name) + " from " + str(self.name))
                    else:
                        pit_object.incoming[iface] -= 1
                for iface in pits:
                    pit_object.incoming.pop(iface)
                    if not pit_object.incoming:
                        llista.append(name)
            for name in llista:
                self.timeouts[name] = self.PIT.table[name]
                self.PIT.table.pop(name)
                # print(str(self.env.now) + str(name) + "was deleted from " + str(self.name))


class NodeMonitor(object):
    def __init__(self, env, nodes):
        self.env = env
        self.nodes = nodes
        self.pat = []
        self.pit = []
        # self.cs = []
        # self.fib = dict()
        # self.store = dict()
        self.packets = []
        # for node in self.nodes.values():
        #     self.store[node.name] = []
        self.times = []
        self.action = env.process(self.run())

    def run(self):
        while True:
            yield self.env.timeout(0.2)
            # Save time
            self.times.append(self.env.now)
            # fibs = {}
            pats = {}
            pits = {}
            css = {}
            for node in self.nodes.values():
                # Save PAT info
                pats[node.name] = len(node.PAT.table)
                # Save PIT info
                tot_pit = 0
                for entry in node.PIT.table.values():
                    tot_pit += len(entry.incoming)
                pits[node.name] = tot_pit

                # if len(node.store.items) > 0:
                #     self.store[node.name].append((len(node.store.items), self.env.now))

                # Save CS info
                # css[node.name] = list(node.CS.table.keys())
                # Save FIB info

                # for iface in node.interfaces:
                #     dict_cont = {entry.name: pheromone
                #                  for entry in node.FIB.table.values()
                #                  for iface2, pheromone in entry.outgoings.items()
                #                  if iface2 is iface}

                    # for entry in node.FIB.table.values():
                    #     for iface2, pher in entry.outgoings.items():
                    #         dict_cont[iface2.name] = pher
                    #     llista[entry.name] = dict_cont

                    # self.fib[node.name][iface.name].append(dict_cont)
            self.pat.append(pats)
            self.pit.append(pits)
            # self.cs.append(css)


class Interface(object):
    def __init__(self, env, name, store, iface=None, rate=100000000.0):
        self.antWaste = []
        self.contentWaste = []
        self.env = env
        self.name = name
        self.out_iface = iface
        self.store = store  # Gonna point to the Node, consumer or producer with iface store
        self.rate = rate
        self.packets = simpy.PriorityStore(env)
        self.action = env.process(self.send())

    def add_interface(self, iface):
        self.out_iface = iface

    def put(self, pkt):
        self.store.put(simpy.PriorityItem(pkt, [self, pkt]))

    def send(self):
        while True:
            pkt = yield self.packets.get()
            if pkt.lifetime > 1:
                time = (pkt.size * 8.0) / self.rate
                yield self.env.timeout(time)  # Packet transmission time
                pkt.lifetime -= 1
                self.out_iface.put(pkt)
            else:
                if pkt.ant is not None:
                    self.antWaste.append(pkt)
                else:
                    self.contentWaste.append(pkt)

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
    def __init__(self, name, data, lifetime, producer):
        self.name = name
        self.data = data
        self.lifetime = lifetime
        self.producer = producer
