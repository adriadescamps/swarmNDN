import simpy
from components1 import Consumer, Producer, Node, Interface
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
    consumer = Consumer(env)
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
    # Add request for content
    consumer.request("video")
    # Run it
    env.run(20000)
    print(str(node1.PAT.table))
    print(str(node2.PAT.table))
    print(str(node3.PAT.table))
    print(str(node4.PAT.table))

