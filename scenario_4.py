import simpy
from components1 import Consumer, Producer, Node, Interface
"""
    This scenario is a developed version of scenario 1 where the topology is 
                            (4-6) Node 2 (7-11) -  Node 4  (12-13)
    Consumer1 (1-3) Node 1                                          - Node 5 (15-16) Producer
    Consumer2 (2-9)                     (5-8) Node 3 (10-14)
                                        (2-9) Node 3
    
    Still only ants are used to check routing is working
    
    SCENARIO 2 for thesis
"""
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
    # Add request for content
    consumer1.request("video")
    consumer1.request("audio")
    consumer2.request("video")
    consumer2.request("audio")
    # Run it
    env.run(20000)
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
    for pkt in consumer1.receivedPackets:
        print(pkt)
    print("\n")
    for pkt in consumer2.receivedPackets:
        print(pkt)

