import simpy
from components_ant import Consumer, Producer, Node, Interface, NodeMonitor
import pandas as pd
import matplotlib.pyplot as plt

"""
    This scenario is a developed version of scenario 1 where the topology is 
                          (3-5) Node 2 (6-9)
    Consumer (1-2) Node 1 -                - Node 4 (11-12) Producer
                          (4-7) Node 3 (8-10)
    
    Still only ants are used to check routing is working
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
    iface10 = Interface(env, "N4IF2", node4.store, iface8)
    iface8.add_interface(iface10)
    iface11 = Interface(env, "N4IF3", node4.store)
    iface12 = Interface(env, "PIF1", producer.store, iface11)
    iface11.add_interface(iface12)
    # Add interfaces
    consumer.add_interface(iface1)
    node1.add_interface([iface2, iface3, iface4])
    node2.add_interface([iface5, iface6])
    node3.add_interface([iface7, iface8])
    node4.add_interface([iface9, iface10, iface11])
    producer.add_interface(iface12)
    # Create node monitor
    monitor = NodeMonitor(env, [node1, node2, node3, node4])
    # Add request for content
    consumer.request("video")
    consumer.request("audio")
    # Run it
    env.run(50)
    print(str(node1.PAT.table))
    print(str(node2.PAT.table))
    print(str(node3.PAT.table))
    print(str(node4.PAT.table))
    # print(str(node1.FIB.table))
    # print(str(node2.FIB.table))
    # print(str(node3.FIB.table))
    # print(str(node4.FIB.table))
    out_pat = pd.DataFrame(monitor.pat, index=monitor.times)

    plot = out_pat.plot.line(title="PAT utilization")
    out_fib = []
    for name, node in monitor.fib.items():
        out_fib.append(pd.DataFrame(node, index=monitor.times))
    i = 220
    fig = plt.figure()
    fig.suptitle("Pheromones")
    for entry, name in zip(out_fib, monitor.fib.keys()):
        i += 1
        a = entry.plot.line(title=name, ax=fig.add_subplot(i), grid=True)
        a.set(xlabel="Time", ylabel="Pheromone amount")
    plt.show()

