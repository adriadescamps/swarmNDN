import functools

import simpy
from components_data import Consumer, Producer, Node, Interface, NodeMonitor
import pandas as pd
import matplotlib.pyplot as plt
"""
    This scenario is a developed version of scenario 1 where the topology is 
                            (4-6) Node 2 (7-11) -  Node 4  (12-13)
    Consumer1 (1-3) Node 1                                          - Node 5 (15-16) Producer
    Consumer2 (2-9)                     (5-8) Node 3 (10-14)
                                        (2-9) Node 3
    
    Ants and data are used to check routing is working
    
    SCENARIO 3 for thesis
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
    producer = Producer(env, names)
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
    consumer1.request("video")
    consumer1.request("audio")
    consumer2.request("video")
    consumer2.request("audio")

    data = []
    monitor = functools.partial(monitor, data)
    trace(env, monitor)

    # Run it
    env.run(65)
    # print(str(node1.PAT.table))
    # print(str(node2.PAT.table))
    # print(str(node3.PAT.table))
    # print(str(node4.PAT.table))
    # print(str(node5.PAT.table))
    # print(str(node1.FIB.table))
    # print(str(node2.FIB.table))
    # print(str(node3.FIB.table))
    # print(str(node4.FIB.table))
    # print(str(node5.FIB.table))
    # for pkt in consumer1.receivedPackets:
    #     print(pkt)
    # for pkt in consumer2.receivedPackets:
    #     print(pkt)

    # Save events information to a file
    data_f = pd.DataFrame(data)
    data_f.to_csv('data/scenario3_data.csv')

    # Visualization
    con1 = []
    con2 = []
    for pkt1, pkt2 in zip(consumer1.receivedPackets, consumer2.receivedPackets):
        con1.append(pkt1.time)
        con2.append(pkt2.time)
    out_consumer = pd.DataFrame({consumer1.name: con1, consumer2.name: con2}, index=["video", "audio"])
    out_pat = pd.DataFrame(monitor_n.pat, index=monitor_n.times)
    out_pit = pd.DataFrame(monitor_n.pit, index=monitor_n.times)
    out_fib = pd.DataFrame(monitor_n.fib, index=monitor_n.times)

    fig_pat = plt.figure()
    plot = out_pat.plot.line(title="PAT", ax=fig_pat.add_subplot(111))
    plot.set(ylabel='Entries', xlabel='Time')

    fig_pit = plt.figure()
    plot2 = out_pit.plot.line(title="PIT", ax=fig_pit.add_subplot(111))
    plot2.set(ylabel='Entries', xlabel='Time')

    fig_con = plt.figure()
    plot3 = out_consumer.plot.bar(title="Content RTT", ax=fig_con.add_subplot(111))
    plot3.set(ylabel="Time", xlabel='Content name')

    i = 510
    fig_v = plt.figure(figsize=[8, 12])
    fig_a = plt.figure(figsize=[8, 12])
    fig_v.suptitle("Content name: Video", y=0.99, x=0.3)
    fig_a.suptitle("Content name: Audio", y=0.99, x=0.3)
    for name, entry in monitor_n.fib.items():
        i += 1
        data = pd.DataFrame(entry, index=monitor_n.times)
        video = data['video'].to_frame()
        video = video.dropna()
        video = video['video'].apply(pd.Series)
        video_p = video.plot.line(title=name, ax=fig_v.add_subplot(i), grid=True)
        video_p.set(xlabel="Time", ylabel="Pheromone amount")
        audio = data['audio'].to_frame()
        audio = audio.dropna()
        audio = audio['audio'].apply(pd.Series)
        audio_p = audio.plot.line(title=name, ax=fig_a.add_subplot(i), grid=True)
        audio_p.set(xlabel="Time", ylabel="Pheromone amount")
    plt.show()
    fig_v.savefig('data/scenario3_video.png')
    fig_a.savefig('data/scenario3_audio.png')
    fig_pat.savefig('data/scenario3_pat.png')
    fig_pit.savefig('data/scenario3_pit.png')
    fig_con.savefig('data/scenario3_data.png')
