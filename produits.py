class produit():

    def __init__(self, id, famille, simulation) -> None:
        if simulation is not None:
            simulation.produits[id] = self
        self.id = id
        self.famille = famille
        self.arrival_time = None
        self.completion_time = None
        self.sequences = []
        self.times = []
    
    def arrival(self, system, time) :
        self.arrival_time = time
        system.prod_arrival(self)

    def completion(self, time):
        self.completion_time = time

    def flowtime(self):
        return self.completion_time-self.arrival_time

    def __str__(self) -> str:
        return f"(produit id {self.id}, famille {self.famille}, arrival_time {self.arrival_time}, completion_time {self.completion_time})"
    