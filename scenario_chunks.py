import functools

import simpy
from components_chunks import Consumer, Producer, Node, Interface, NodeMonitor
import pandas as pd
import matplotlib.pyplot as plt
"""
    This scenario is a developed version of scenario 1 where the topology is 
                            (4-6) Node 2 (7-11) -  Node 4  (12-13)
    Consumer1 (1-3) Node 1                                          - Node 5 (15-16) Producer
    Consumer2 (2-9)                     (5-8) Node 3 (10-14)
                                        (2-9) Node 3
    
    Ants and data are used to check routing is working. For a specific content, 10 chunks of data are requested.
    
    SCENARIO 4 for thesis
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


if __name__ == '__main__':
    env = simpy.Environment()  # Create the SimPy environment
    # Create Consumer
    consumer1 = Consumer(env, "C1")
    consumer2 = Consumer(env, "C2")
    # Create Producer
    names = ["video", "audio"]
    producer = Producer(env, names, "P01")
    # Create Node
    node1 = Node(env, "N01")
    node2 = Node(env, "N02")
    node3 = Node(env, "N03")
    node4 = Node(env, "N04")
    node5 = Node(env, "N05")
    # Create Interfaces
    iface1 = Interface(env, "C1IF1", consumer1.store)
    iface2 = Interface(env, "C2IF1", consumer2.store)

    iface3 = Interface(env, "N1IF1", node1.store, iface1)
    iface1.add_interface(iface3)
    iface4 = Interface(env, "N1IF2", node1.store)
    iface5 = Interface(env, "N1IF3", node1.store)
    iface6 = Interface(env, "N2IF1", node2.store, iface4)
    iface4.add_interface(iface6)
    iface7 = Interface(env, "N2IF2", node2.store)
    iface8 = Interface(env, "N3IF1", node3.store, iface5)
    iface5.add_interface(iface8)
    iface9 = Interface(env, "N3IF2", node3.store, iface2)
    iface2.add_interface(iface9)
    iface10 = Interface(env, "N3IF3", node3.store)
    iface11 = Interface(env, "N4IF1", node4.store, iface7)
    iface7.add_interface(iface11)
    iface12 = Interface(env, "N4IF2", node4.store)
    iface13 = Interface(env, "N5IF1", node5.store, iface12)
    iface12.add_interface(iface13)
    iface14 = Interface(env, "N5IF2", node5.store, iface10)
    iface10.add_interface(iface14)
    iface15 = Interface(env, "N5IF3", node5.store)
    iface16 = Interface(env, "PIF1", producer.store, iface15)
    iface15.add_interface(iface16)
    # Add interfaces
    consumer1.add_interface(iface1)
    consumer2.add_interface(iface2)
    node1.add_interface([iface3, iface4, iface5])
    node2.add_interface([iface6, iface7])
    node3.add_interface([iface8, iface9, iface10])
    node4.add_interface([iface11, iface12])
    node5.add_interface([iface13, iface14, iface15])
    producer.add_interface(iface16)
    # Create node monitor
    monitor_n = NodeMonitor(env, [node1, node2, node3, node4, node5])
    # Add request for content
    env.process(consumer2.request("video"))
    env.process(consumer2.request("audio"))
    env.process(consumer1.request("video"))
    env.process(consumer1.request("audio"))

    data = []
    # Bind *data* as first argument to monitor()
    # see https://docs.python.org/3/library/functools.html#functools.partial
    monitor = functools.partial(monitor, data)
    trace(env, monitor)

    # Run it
    env.run(100)
    print(str(node1.PIT.table))
    print(str(node2.PIT.table))
    print(str(node3.PIT.table))
    print(str(node4.PIT.table))
    print(str(node5.PIT.table))
    print(str(node1.FIB.table))
    print(str(node2.FIB.table))
    print(str(node3.FIB.table))
    print(str(node4.FIB.table))
    print(str(node5.FIB.table))
    print("Consumer 1")
    for pkt in consumer1.receivedPackets:
        print(pkt)
    print("Consumer 2")
    for pkt in consumer2.receivedPackets:
        print(pkt)

    # Save events information to a file
    data_f = pd.DataFrame(data)
    data_f.to_csv("scenario4_data.csv")

    # Save CS information to a file
    cs_f = pd.DataFrame(monitor_n.cs, index=monitor_n.times)
    cs_f.to_csv("scenario4_cs.csv")

    # Visualization
    con1 = dict()
    con2 = dict()
    for pkt1 in consumer1.receivedPackets:
        con1[pkt1.name] = pkt1.time
    for pkt2 in consumer2.receivedPackets:
        con2[pkt2.name] = pkt2.time
    out_consumer = pd.DataFrame({consumer1.name: con1, consumer2.name: con2})
    out_pat = pd.DataFrame(monitor_n.pat, index=monitor_n.times)
    out_pit = pd.DataFrame(monitor_n.pit_size, index=monitor_n.times)
    out_fib = pd.DataFrame(monitor_n.fib, index=monitor_n.times)

    fig_pat = plt.figure()
    plot = out_pat.plot.line(title="PAT entries", ax=fig_pat.add_subplot(111))

    fig_pit = plt.figure()
    plot2 = out_pit.plot.line(title="PIT entries", ax=fig_pit.add_subplot(111))

    fig_con = plt.figure()
    plot3 = out_consumer.plot.bar(title="Data retrieving time", ax=fig_con.add_subplot(111))
    plot3.set(ylabel="Time")

    # i = 510
    # fig_v = plt.figure(figsize=[8, 12])
    # fig_a = plt.figure(figsize=[8, 12])
    # fig_v.suptitle("Video")
    # fig_a.suptitle("Audio")
    # for name, entry in monitor_n.fib.items():
    #     i += 1
    #     data = pd.DataFrame(entry, index=monitor_n.times)
    #     video = data['video'].to_frame()
    #     video = video.dropna()
    #     video = video['video'].apply(pd.Series)
    #     video_p = video.plot.line(title=name, ax=fig_v.add_subplot(i), grid=True)
    #     video_p.set(xlabel="Time", ylabel="Pheromone amount")
    #     audio = data['audio'].to_frame()
    #     audio = audio.dropna()
    #     audio = audio['audio'].apply(pd.Series)
    #     audio_p = audio.plot.line(title=name, ax=fig_a.add_subplot(i), grid=True)
    #     audio_p.set(xlabel="Time", ylabel="Pheromone amount")
    #
    i = 0
    for node, ifaces in monitor_n.fib.items():
        i += 1
        f_fib = pd.DataFrame(ifaces, index=monitor_n.times)
        f_fib.to_csv("scenario4_fib_" + str(node) + ".csv")
        j = 310
        fig_fib = plt.figure(figsize=[8, 12])
        for iface, content in ifaces.items():
            j += 1
            iface_fib = pd.DataFrame(content, index=monitor_n.times)
            plot_fib = iface_fib.plot.line(title=iface, ax=fig_fib.add_subplot(j))
            plot_fib.legend(bbox_to_anchor=(1,0), loc="lower right", bbox_transform=fig_fib.transFigure, ncol=3)
        fig_fib.savefig('scenario4_fib_' + str(node) + '.png')

    f_fib = pd.DataFrame(monitor_n.fib, index=monitor_n.times)
    f_fib.to_csv("scenario4_fib.csv")

    # reform = [{(time, node_name, content_name, iface_name): [pheromone]}
    #           for node_name, node_info in monitor_n.fib.items()
    #           for node_info_time, time in zip(node_info, monitor_n.times)
    #           for content_name, content_info in node_info_time.items()
    #           for iface_name, pheromone in content_info.items()]
    #
    # df = pd.DataFrame(reform).T
    # names = ['Time','Node',  'Content', 'Interface']
    # df.index.set_names(names, inplace=True)
    # df.to_excel("scenario4_fib.xlsx")

    plt.show()
    # fig_v.savefig('scenario4_video.png')
    # fig_a.savefig('scenario4_audio.png')
    fig_pat.savefig('scenario4_pat.png')
    fig_pit.savefig('scenario4_pit.png')
    fig_con.savefig('scenario4_data.png')