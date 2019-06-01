import functools
import random
import sys
import time

import simpy
from components_flood import Consumer, Producer, Node, Interface, NodeMonitor
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
"""
    This scenario uses Uninetts topology
    SCENARIO 6 for thesis
"""


def trace(env, callback):
    """Replace the ``step()`` method of *env* with a tracing function
    that calls *callbacks* with an events time, priority, ID and its
    instance just before it is processed.
    """
    def get_wrapper(env_step, callback):
        """Generate the wrapper for env.step()."""
        @functools.wraps(env_step)
        def tracing_step():
            """Call *callback* for the next event if one exist before
            calling ``env.step()``."""
            if len(env._queue):
                t, prio, eid, event = env._queue[0]
                callback(t, prio, eid, event)
            return env_step()
        return tracing_step
    env.step = get_wrapper(env.step, callback)


def monitor(data, t, prio, eid, event):
    if not issubclass(type(event), simpy.events.Timeout):
        data.append((t, eid, type(event), event.value))


def importTopology(env, name, mode):
    nodes = {}
    interfaces = {}
    file = open(name, 'r')
    line = file.readline()
    while '*Vertices' not in line:
        line = file.readline()
    line = file.readline()
    while '*Arcs' not in line:
        words = line.split()
        # Read nodes
        nodes[words[0]] = Node(env, words[0], words[1][1:-1], words[5][1:-1], mode)
        line = file.readline()
    line = file.readline()
    while line is not '':
        words = line.split()
        # Read links
        tupl = (words[1], words[0])
        if tupl in interfaces:
            iface = Interface(env, words[4], nodes[words[0]].store, interfaces[tupl], float(words[6]))
            interfaces[tupl].add_interface(iface)
        else:
            iface = Interface(env, words[4], nodes[words[0]].store, rate=float(words[6]))

        nodes[words[0]].add_interface(iface)
        interfaces[(words[0], words[1])] = iface

        line = file.readline()
    return nodes


def printTopology(name, nodes):
    file = open(name, 'r')
    line = file.readline()
    while '*Arcs' not in line:
        #Skip nodes
        line = file.readline()
    line = file.readline()
    dicc = {}
    dicc['value'] = []
    dicc['source'] = []
    dicc['target'] = []
    while line is not '':
        words = line.split()
        # Read links
        dicc['source'].append(nodes[words[0]].name)
        dicc['target'].append(nodes[words[1]].name)
        dicc['value'].append(words[6])

        line = file.readline()

    plt.figure(figsize=(20, 15))
    df = pd.DataFrame(dicc)
    g = nx.from_pandas_edgelist(df, 'source', 'target', create_using=nx.Graph())
    nx.draw(g, with_labels=True, node_color='skyblue', node_size=35, edge_color="blue", width=2.0,
            edge_cmap=plt.get_cmap("winter"))


if __name__ == '__main__':
    # Mode 0 is Ant routing, mode 1 is flood routing
    consum = []
    hits = {}
    waste = {}
    for mode in range(2):
        if mode == 0:
            output = 'scenario6/scenario6'
        else:
            output = 'scenario7/scenario7'
        consum = []
        hits[mode] = []
        waste[mode] = []
        for simulation in range(20):
            random.seed(2200+simulation)
            env = simpy.Environment()  # Create the SimPy environment
            nodes = importTopology(env, 'isis-uninett.net', mode)
            # printTopology('isis-uninett.net', nodes)
            info = open('data/' + output + '_info' + str(simulation) + '.txt', 'w+')
            # Create Consumers
            info.write("Consumers:\n")
            consumers = {}
            for i in range(random.randint(10, 20)):
                name = 'C'+str(i)
                consumers[name] = Consumer(env, name, i*3+20, mode)
                rand = random.choice(list(nodes.keys()))
                iface_c = Interface(env, name + "-" + nodes[rand].name, consumers[name].store)
                iface_n = Interface(env, nodes[rand].name + "-" + name, nodes[rand].store, iface_c)
                iface_c.add_interface(iface_n)
                nodes[rand].add_interface(iface_n)
                consumers[name].add_interface(iface_c)
                info.write(name + " - Node:  " + nodes[rand].name + '\n')

            # Create Producer
            info.write("Producers:" + '\n')
            names = ["video", "audio"]
            # Generate a random number of producers (1-5) in a random location
            # producers = {}
            # for i in range(random.randint(1, 5)):
            #     name = 'P'+str(i)
            #     rand = random.choice(list(nodes.keys()))
            #     producers[name] = Producer(env, names, name, nodes[rand].area)
            #     iface_p = Interface(env, name + "-" + nodes[rand].name, producers[name].store)
            #     iface_n = Interface(env, nodes[rand].name + "-" + name, nodes[rand].store, iface_p)
            #     iface_p.add_interface(iface_n)
            #     nodes[rand].add_interface(iface_n)
            #     producers[name].add_interface(iface_p)
            #     info.write(name + " - Node:  " + nodes[rand].name)

            # Create static Producer
            producer = Producer(env, names, "P01", "Trondheim")
            # 5 - hovedbygget
            node = nodes['5']
            iface_p = Interface(env, "P01" + "-" + node.name, producer.store)
            iface_n = Interface(env, node.name + "-" + "P01", node.store, iface_p)
            iface_p.add_interface(iface_n)
            producer.add_interface(iface_p)
            node.add_interface(iface_n)
            info.write("P01" + " - Node:  " + nodes['5'].name + '\n')

            # Create node monitor
            monitor_n = NodeMonitor(env, nodes)
            # Add request for content
            for con in consumers.values():
                env.process(con.request("Trondheim/video"))
                # env.process(con.request("Trondheim/audio", 20))

            # data = []
            # monitor = functools.partial(monitor, data)
            # trace(env, monitor)

            # Run it
            env.run(2000)

            # Save events information to a file
            # data_f = pd.DataFrame(data)
            # data_f.to_csv('data/scenario7/scenario7_data_' + str(simulation) + '.csv')

            # # Visualization
            con_times = {}
            for name, consumer in consumers.items():
                con_times[name] = consumer.receivedPackets
            con_times = {name: consumer.receivedPackets
                         for name, consumer in consumers.items()
                         if consumer.receivedPackets}
            fig_con = plt.figure(figsize=(10, 7))
            if con_times:

                out_consumer = pd.DataFrame(con_times)
                plot3 = out_consumer.plot.bar(title="Content access response time", ax=fig_con.add_subplot(111))
                plot3.set(ylabel="Time")
                plot3.legend(loc='center left', bbox_to_anchor=(1, 0.5))

            out_pat = pd.DataFrame(monitor_n.pat, index=monitor_n.times)
            fig_pat = plt.figure()
            plot = out_pat.plot.line(title="PAT", ax=fig_pat.add_subplot(111))
            plot.set(ylabel="Max Entries")
            plot.set(xlabel="Time")
            plot.legend().remove()

            out_pit = pd.DataFrame(monitor_n.pit, index=monitor_n.times)
            fig_pit = plt.figure()
            plot2 = out_pit.plot.line(title="PIT", ax=fig_pit.add_subplot(111))
            plot2.set(ylabel="Max Entries")
            plot2.set(xlabel="Time")
            plot2.legend().remove()

            out_pat.to_csv('data/' + output + '_pat_' + str(simulation) + '.csv')
            out_pit.to_csv('data/' + output + '_pit_' + str(simulation) + '.csv')
            if con_times:
                out_consumer.to_csv('data/' + output + '_times_' + str(simulation) + '.csv')

            fig_pat.savefig('data/' + output + '_pat_' + str(simulation) + ".png")
            fig_pit.savefig('data/' + output + '_pit_' + str(simulation) + ".png")
            fig_con.savefig('data/' + output + '_times_' + str(simulation) + ".png")
            info.close()
            print(str(simulation))
            consum.append(len(consumers))
            hits[mode].append(sum(len(consumer.receivedPackets) for consumer in consumers.values()))
            waste[mode].append(sum(len(consumer.wastedPackets) for consumer in consumers.values()) + sum(len(node.wastedPackets) for node in nodes.values()))
            # plt.show()
        out_hits = pd.DataFrame({'hits': hits[mode], 'waste': waste[mode]}, index=consum)
        out_hits = out_hits.sort_index()
        out_hits.to_csv('data/' + output + '_hits.csv')
        fig_hits = plt.figure()
        plot = out_hits.plot.bar(title="Content retrieved", ax=fig_hits.add_subplot(111))
        plot.set(ylabel="Hits")
        plot.set(xlabel="Consumers")
        fig_hits.savefig('data/' + output + '_hits.png')
    out_hit = pd.DataFrame(hits, index=consum)
    out_waste = pd.DataFrame(waste, index=consum)
    out_hit.columns = ['Ant routing', 'Flooding']
    out_waste.columns = ['Ant routing', 'Flooding']
    out_hit = out_hit.sort_index()
    out_waste = out_waste.sort_index()
    out_hit.to_csv('data/hits.csv')
    out_waste.to_csv('data/waste.csv')
    fig_hits = plt.figure(figsize=[12, 16])
    plot_hit = out_hit.plot.bar(title="Content retrieved", ax=fig_hits.add_subplot(211))
    plot_waste = out_waste.plot.bar(title="Content wasted", ax=fig_hits.add_subplot(212))
    fig_hits.savefig('data/hits.png')
