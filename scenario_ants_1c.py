import simpy
from pandas import isnull
from components_ant import Consumer, Producer, Node, Interface, NodeMonitor
import pandas as pd
import matplotlib.pyplot as plt

"""
    This scenario is a developed version of scenario 1 where the topology is 
                          (3-5) Node 2 (6-9) -  Node 4  (10-11)
    Consumer (1-2) Node 1 -                                     - Node 5 (13-14) Producer
                                    (4-7) Node 3 (8-12)
    
    Still only ants are used to check routing is working
    
    SCENARIO 1 for thesis
"""
if __name__ == '__main__':
    env = simpy.Environment()  # Create the SimPy environment
    # Create Consumer
    consumer = Consumer(env, "C1")
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
    iface1 = Interface(env, "CIF1", consumer.store)
    iface2 = Interface(env, "N1IF1", node1.store, iface1)
    iface1.add_interface(iface2)
    iface3 = Interface(env, "N1IF2", node1.store)
    iface4 = Interface(env, "N1IF3", node1.store)
    iface5 = Interface(env, "N2IF1", node2.store, iface3)
    iface3.add_interface(iface5)
    iface6 = Interface(env, "N2IF2", node2.store)
    iface7 = Interface(env, "N3IF1", node3.store, iface4)
    iface4.add_interface(iface7)
    iface8 = Interface(env, "N3IF2", node3.store)
    iface9 = Interface(env, "N4IF1", node4.store, iface6)
    iface6.add_interface(iface9)
    iface10 = Interface(env, "N4IF2", node4.store)
    iface11 = Interface(env, "N5IF1", node5.store, iface10)
    iface10.add_interface(iface11)
    iface12 = Interface(env, "N5IF2", node5.store, iface8)
    iface8.add_interface(iface12)
    iface13 = Interface(env, "N5IF3", node5.store)
    iface14 = Interface(env, "PIF1", producer.store, iface13)
    iface13.add_interface(iface14)
    # Add interfaces
    consumer.add_interface(iface1)
    node1.add_interface([iface2, iface3, iface4])
    node2.add_interface([iface5, iface6])
    node3.add_interface([iface7, iface8])
    node4.add_interface([iface9, iface10])
    node5.add_interface([iface11, iface12, iface13])
    producer.add_interface(iface14)
    # Create node monitor
    monitor = NodeMonitor(env, [node1, node2, node3, node4, node5])
    # Add request for content
    consumer.request("video")
    consumer.request("audio")
    # Run it
    env.run(60)
    print(str(node1.PAT.table))
    print(str(node2.PAT.table))
    print(str(node3.PAT.table))
    print(str(node4.PAT.table))
    print(str(node5.PAT.table))
    print(str(node1.FIB.table))
    print(str(node2.FIB.table))
    print(str(node3.FIB.table))
    print(str(node4.FIB.table))
    print(str(node5.FIB.table))

    # Visualization
    out_pat = pd.DataFrame(monitor.pat, index=monitor.times)
    out_fib = pd.DataFrame(monitor.fib, index=monitor.times)

    fig_pat = plt.figure()
    plot = out_pat.plot.line(title="PAT utilization", ax=fig_pat.add_subplot(111))

    i = 510
    fig_v = plt.figure(figsize=[8, 12])
    fig_a = plt.figure(figsize=[8, 12])
    fig_v.suptitle("Video")
    fig_a.suptitle("Audio")
    for name, entry in monitor.fib.items():
        i += 1
        data = pd.DataFrame(entry, index=monitor.times)
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
    fig_v.savefig('data/scenario1_video.png')
    fig_a.savefig('data/scenario1_audio.png')
    fig_pat.savefig('data/scenario1_pat.png')
