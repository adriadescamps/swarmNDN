import simpy
from components_ant import Consumer, Producer, Node, Interface
"""
    This scenario is a simple Consumer-Node-Producer where the consumer requests one content
    Only the ants are enabled
"""
if __name__ == '__main__':
    env = simpy.Environment()  # Create the SimPy environment
    # Create Consumer
    consumer = Consumer(env)
    # Create Producer
    names = ["video", "audio"]
    producer = Producer(env, names)
    # Create Node
    node = Node(env, "N01")
    # Create Interfaces
    iface1 = Interface(env, "CIF1", consumer.store)
    iface2 = Interface(env, "NIF1", node.store, iface1)
    iface1.add_interface(iface2)
    iface3 = Interface(env, "NIF2", node.store)
    iface4 = Interface(env, "PIF1", producer.store, iface3)
    iface3.add_interface(iface4)
    # Add interfaces
    consumer.add_interface(iface1)
    node.add_interface(iface2)
    node.add_interface(iface3)
    producer.add_interface(iface4)
    # Add request for content
    consumer.request("video")
    # Run it
    print("Running: " + str(env.now))
    env.run(20000)
    print("Running: " + str(env.now))

