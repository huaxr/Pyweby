from master.pubsub import broker

class Message:
    def __init__(self, topic, payload, publisher):
        self.topic = topic
        self.payload = payload
        self.publisher = publisher

class subscriber:
    def __init__(self, callback):
        self.__callback = callback

    def callback(self, message):
        self.__callback(message)

    def add_subscribe(self, broker, topic):
        broker.subscribe(self, topic)

class publisher:
    def __init__(self):
        self.__targets = []

    def add_target(self, broker, topic):
        if (broker, topic) not in self.__targets:
            self.__targets.append((broker, topic))

    def publish(self, payload):
        for target in self.__targets:
            message = Message(target[1], payload, self)
            target[0].publish(message)

# for callback.
def print_message(message):
    print("publisher : %s \ntopic : %s \npayload : %s \n"%(message.publisher, message.topic, message.payload))

def print_payload(message):
    print("payload : %s \n"%(message.payload))

brokyer = broker.broker()  # this has subscribe and publish method!
message_subscriber = subscriber(print_message)
payload_subscriber = subscriber(print_payload)
message_subscriber.add_subscribe(brokyer, "xxx") # 往 broker中添加这个订阅者
payload_subscriber.add_subscribe(brokyer, "xxx")


test_publisher = publisher()
test_publisher.add_target(brokyer, "xxx")
test_publisher.publish("ni hao")
# test_publisher.publish("hello world")
