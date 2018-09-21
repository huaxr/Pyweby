import copy


class broker:
    def __init__(self):
        self.__topics = {}

    def subscribe(self, subscriber, topic):
        if topic not in self.__topics.keys():
            self.__topics[topic] = []
        if subscriber not in self.__topics[topic]:
            self.__topics[topic].append(subscriber)

    def publish(self, message):
        if message.topic not in self.__topics.keys():
            return
        for subscribe in self.__topics[message.topic]:
            message = copy.deepcopy(message)
            subscribe.callback(message)