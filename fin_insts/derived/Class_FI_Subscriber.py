
from abc import ABC, abstractmethod

 
class Subscriber(ABC):

    def __init__(self):       
        self.subscribers = []
        
    @abstractmethod
    def update_subscriber_data(self, obj):
        # work
        # for subscriber in self.subscribers:
        #    subscriber.update_subscriber_data()
        pass

