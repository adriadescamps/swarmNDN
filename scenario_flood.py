import functools
import os
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
    return nx.from_pandas_edgelist(df, 'source', 'target', create_using=nx.DiGraph())
    # nx.draw(g, with_labels=True, node_color='skyblue', node_size=35, edge_color="blue", width=2.0,
    #         edge_cmap=plt.get_cmap("winter"))


if __name__ == '__main__':
    # Mode 0 is Ant routing, mode 1 is flood routing
    consum = []
    hits = {}
    hits_a = {}
    waste = {}
    timeouts = {}
    inter = {}
    prod_rec = {}
    total_stretch = {}
    total_times = {}
    for mode in range(2):
        if mode == 0:
            output = 'ant_1000/scenario6'
        else:
            output = 'flood_1000/scenario7'
        consum = []
        prod = []
        hits[mode] = []
        hits_a[mode] = []
        waste[mode] = []
        timeouts[mode] = []
        inter[mode] = []
        prod_rec[mode] = []
        aver_stretch = []
        aver_times = []
        simulations = 1
        for simulation in range(simulations):
            random.seed(2200+simulation)
            env = simpy.Environment()  # Create the SimPy environment
            nodes = importTopology(env, 'isis-uninett.net', mode)
            graph = printTopology('isis-uninett.net', nodes)
            # Create Consumers
            consumers = {}
            for i in range(random.randint(10, 50)):
                name = 'C'+str(i)
                consumers[name] = Consumer(env, name, i*3+10, mode)
                rand = random.choice(list(nodes.keys()))
                iface_c = Interface(env, name + "-" + nodes[rand].name, consumers[name].store)
                iface_n = Interface(env, nodes[rand].name + "-" + name, nodes[rand].store, iface_c)
                iface_c.add_interface(iface_n)
                nodes[rand].add_interface(iface_n)
                consumers[name].add_interface(iface_c)
                graph.add_edge(name, nodes[rand].name, value=1000000)
                graph.add_edge(nodes[rand].name, name, value=1000000)
            # Create Producer
            names = ["video", "audio"]
            # Generate a random number of producers (1-5) in a random location
            producers = {}
            for i in range(random.randint(1, 5)):
                name = 'P'+str(i)
                rand = random.choice(list(nodes.keys()))
                while nodes[rand].area != 'Trondheim':
                    rand = random.choice(list(nodes.keys()))
                producers[name] = Producer(env, names, name, nodes[rand].area)
                iface_p = Interface(env, name + "-" + nodes[rand].name, producers[name].store)
                iface_n = Interface(env, nodes[rand].name + "-" + name, nodes[rand].store, iface_p)
                iface_p.add_interface(iface_n)
                nodes[rand].add_interface(iface_n)
                producers[name].add_interface(iface_p)
                graph.add_edge(name, nodes[rand].name, value=1000000)
                graph.add_edge(nodes[rand].name, name, value=1000000)

            # Create static Producer
            # producer = Producer(env, names, "P01", "Trondheim")
            # # 5 - hovedbygget
            # node = nodes['5']
            # iface_p = Interface(env, "P01" + "-" + node.name, producer.store)
            # iface_n = Interface(env, node.name + "-" + "P01", node.store, iface_p)
            # iface_p.add_interface(iface_n)
            # producer.add_interface(iface_p)
            # node.add_interface(iface_n)
            # info.write("P01" + " - Node:  " + nodes['5'].name + '\n')

            # Create node monitor
            monitor_n = NodeMonitor(env, nodes)
            # Add request for content
            for con in consumers.values():
                env.process(con.request("Trondheim/video"))
                env.process(con.request("Trondheim/audio", 20))

            # data = []
            # monitor = functools.partial(monitor, data)
            # trace(env, monitor)

            # Run it
            env.run(2000)

            # Save events information to a file
            # data_f = pd.DataFrame(data)
            # data_f.to_csv('data/scenario7/scenario7_data_' + str(simulation) + '.csv')

            # Visualization
            con_times = {}
            for name, consumer in consumers.items():
                con_times[name] = consumer.receivedPackets.values()
            con_times = {name: list(consumer.receivedPackets.values())
                         for name, consumer in consumers.items()
                         if consumer.receivedPackets}
            fig_con = plt.figure(figsize=(10, 7))
            if con_times:
                cons = {name: {pkt.name: pkt.time for pkt in consumer} for name, consumer in con_times.items()}
                out_consumer = pd.DataFrame(cons)
                plot3 = out_consumer.plot.bar(title="Content access response time", ax=fig_con.add_subplot(111))
                plot3.set(ylabel="Time")
                plot3.legend(loc='center left', bbox_to_anchor=(1, 0.5))

            # out_pat = pd.DataFrame(monitor_n.pat, index=monitor_n.times)
            # fig_pat = plt.figure()
            # plot = out_pat.plot.line(title="PAT", ax=fig_pat.add_subplot(111))
            # plot.set(ylabel="Max Entries")
            # plot.set(xlabel="Time")
            # plot.legend().remove()
            #
            # out_pit = pd.DataFrame(monitor_n.pit, index=monitor_n.times)
            # fig_pit = plt.figure()
            # plot2 = out_pit.plot.line(title="PIT", ax=fig_pit.add_subplot(111))
            # plot2.set(ylabel="Max Entries")
            # plot2.set(xlabel="Time")
            # plot2.legend().remove()
            #
            # out_pat.to_csv('data/' + output + '_pat_' + str(simulation) + '.csv')
            # out_pit.to_csv('data/' + output + '_pit_' + str(simulation) + '.csv')
            if con_times:
                out_consumer.to_csv('data/' + output + '_times_' + str(simulation) + '.csv')

            # fig_pat.savefig('data/' + output + '_pat_' + str(simulation) + ".png")
            # fig_pit.savefig('data/' + output + '_pit_' + str(simulation) + ".png")
            fig_con.savefig('data/' + output + '_times_' + str(simulation) + ".png")
            print(str(simulation))
            consum.append(len(consumers))
            prod.append(len(producers))
            hit = sum(len(consumer.receivedPackets) for consumer in consumers.values())
            hits[mode].append(hit)
            hits_a[mode].append(hit / len(consumers))
            waste[mode].append(sum(len(consumer.wastedPackets) for consumer in consumers.values()) +
                               sum(len(node.wastedPackets) for node in nodes.values()) +
                               sum(len(producer.wasted) for producer in producers.values()))
            timeouts[mode].append(sum(len(node.timeoutPackets) for node in nodes.values()))
            inter[mode].append(sum(len(node.interestDrop) for node in nodes.values()))
            prod_rec[mode].append(max([len(prod.received) for prod in producers.values()]))

            stretch = {}
            times = {}
            for con in consumers.values():
                for pkt in con.receivedPackets.values():
                    if pkt.name not in stretch:
                        stretch[pkt.name] = []
                    if pkt.name not in times:
                        times[pkt.name] = []
                    sp = (len(nx.shortest_path(graph, con.name, pkt.creator)) - 1)
                    times[pkt.name].append(pkt.time / (sp * 2))
                    stretch[pkt.name].append((pkt.default_time - pkt.lifetime) / sp)

            names = {}
            for con in consumers.values():
                for pkt in con.receivedPackets.values():
                    if pkt.name not in names:
                        names[pkt.name] = 1
                    else:
                        names[pkt.name] += 1
            aver_stretch.append({name: sum(stretch[name]) / len(stretch[name]) for name in stretch.keys()})
            aver_times.append({name: sum(times[name]) / len(times[name]) for name in times.keys()})

        names = [name for stretch in aver_stretch for name in stretch.keys()]

        total_stretch[mode] = {name: sum(aver_stretch[i][name]
                                         for i in range(simulations)
                                         if name in aver_stretch[i]) / simulations
                               for name in names}

        total_times[mode] = {name: sum(aver_times[i][name]
                                       for i in range(simulations)
                                       if name in aver_times[i]) / simulations
                             for name in names}

        out_hits = pd.DataFrame({'hits': hits[mode], 'waste': waste[mode], 'timeout': timeouts[mode],
                                 'prodRec': prod_rec[mode], 'interest': inter[mode]}, index=consum)
        out_hits = out_hits.sort_index()
        out_hits.to_csv('data/' + output + '_prova.csv')
        fig = plt.figure(figsize=[12, 8])
        ax = out_hits[['hits', 'waste', 'timeout', 'interest']].plot.bar(title="Content retrieved")
        fig.xticks = 'Consumers'
        fig.yticks = 'Hits'
        plt.xticks(rotation=0)
        ax2 = ax.twinx()
        plot = ax2.plot(ax.get_xticks(), out_hits[['prodRec']], marker='.', markeredgecolor='black')
        plot[0].get_figure().savefig('data/' + output + '_prova.png')
        out_hits2 = pd.DataFrame({'hits': hits[mode], 'prodRec': prod_rec[mode]}, index=consum)
        out_hits2 = out_hits2.sort_index()
        out_hits2.to_csv('data/' + output + '_prova2.csv')
        fig2 = plt.figure(figsize=[12, 8])
        ax = out_hits2[['hits']].plot.bar(title="Content retrieved")
        fig2.xticks = 'Consumers'
        fig2.yticks = 'Hits'
        plt.xticks(rotation=0)
        ax2 = ax.twinx()
        plot = ax2.plot(ax.get_xticks(), out_hits[['prodRec']], marker='.', markeredgecolor='black')
        plot[0].get_figure().savefig('data/' + output + '_prova2.png')
        # out_hits = pd.DataFrame({'hits': hits[mode], 'waste': waste[mode], 'timeout': timeouts[mode]}, index=consum)
        # out_hits_p = pd.DataFrame({'hits': hits[mode], 'waste': waste[mode], 'timeout': timeouts[mode]}, index=[consum, prod])
        # out_hits_a = pd.DataFrame({'hits': hits_a[mode], 'waste': waste[mode], 'timeout': timeouts[mode]}, index=[consum, prod])
        # out_prod = pd.DataFrame({'interests': prod_rec}, index=consum)
        # out_hits = out_hits.sort_index()
        # out_hits_p = out_hits_p.sort_index()
        # out_hits_a = out_hits_a.sort_index()
        # out_prod = out_prod.sort_index()
        # out_hits.to_csv('data/' + output + '_hits.csv')
        # out_hits_p.to_csv('data/' + output + '_hits_p.csv')
        # out_hits_a.to_csv('data/' + output + '_hits_a.csv')
        # fig_hits = plt.figure()
        # plot = out_hits.plot.bar(title="Content retrieved", ax=fig_hits.add_subplot(111))
        # plot_i = out_prod.plot.line(ax=fig_hits.add_subplot(111))
        # plot.set(ylabel="Hits")
        # plot.set(xlabel="Consumers")
        # fig_hits.savefig('data/' + output + '_hits.png')
        # fig_hits_p = plt.figure()
        # plot_p = out_hits_p.plot.bar(title="Content retrieved", ax=fig_hits_p.add_subplot(111))
        # plot_p.set(ylabel="Hits")
        # plot_p.set(xlabel="Consumers, Producers")
        # fig_hits_p.savefig('data/' + output + '_hits_p.png')
        # fig_hits_a = plt.figure()
        # plot_a = out_hits_a.plot.bar(title="Content retrieved per consumer", ax=fig_hits_a.add_subplot(111))
        # plot_a.set(ylabel="Average Hits")
        # plot_a.set(xlabel="Consumers, Producers")
        # fig_hits_a.savefig('data/' + output + '_hits_a.png')
    out_prod = pd.DataFrame(prod_rec, index=consum)
    out_hit_a = pd.DataFrame(hits_a, index=consum)
    out_waste = pd.DataFrame(waste, index=consum)
    out_prod.columns = ['Ant routing', 'Flooding']
    out_hit_a.columns = ['Ant routing', 'Flooding']
    out_waste.columns = ['Ant routing', 'Flooding']
    out_prod = out_prod.sort_index()
    out_hit_a = out_hit_a.sort_index()
    out_waste = out_waste.sort_index()
    out_hit_a.to_csv('data/hits_a' + str(time.time())[:8] + '.csv')
    out_waste.to_csv('data/waste' + str(time.time())[:8] + '.csv')
    fig_hits = plt.figure()
    fig_hits2 = plt.figure()
    fig_hits_a = plt.figure()
    plot_hit_a = out_hit_a.plot.bar(title="Content retrieved per consumer", ax=fig_hits_a.add_subplot(211))
    plt.xticks(rotation=0)
    plot_hit_a2 = plot_hit_a.twinx()
    plot_a2 = plot_hit_a2.plot(plot_hit_a.get_xticks(), out_prod, marker='o', linestyle='-.', markeredgecolor='black')
    plot_waste = out_waste.plot.bar(title="Content wasted", ax=fig_hits.add_subplot(212))
    plot_waste2 = out_waste.plot.bar(title="Content wasted", ax=fig_hits2.add_subplot(212))
    plot_waste_a = out_waste.plot.bar(title="Content wasted", ax=fig_hits_a.add_subplot(212))

    fig_hits.savefig('data/' + str(time.time())[:8] + 'hits.png')
    fig_hits2.savefig('data/' + str(time.time())[:8] + 'hits2.png')
    fig_hits_a.savefig('data/' + str(time.time())[:8] + 'hits_a.png')

    out_stretch = pd.DataFrame(total_stretch)
    out_stretch.columns = ['Ant routing', 'Flooding']
    out_stretch = out_stretch.sort_index()
    out_stretch.to_csv('data/' + str(time.time())[:8] + 'stretch_.csv')
    fig_str = plt.figure()
    plot_str = out_stretch.plot.bar(title='Stretch', ax=fig_str.add_subplot(111))
    fig_str.savefig('data/' + str(time.time())[:8] + 'stretch_.png')

    out_times = pd.DataFrame(total_times)
    out_times.columns = ['Ant routing', 'Flooding']
    out_times = out_times.sort_index()
    out_times.to_csv('data/' + str(time.time())[:8] + 'times_.csv')
    fig_tim = plt.figure()
    plot_tim = out_times.plot.bar(title='Stretch Time', ax=fig_tim.add_subplot(111))
    fig_tim.savefig('data/' + str(time.time())[:8] + 'times_.png')
