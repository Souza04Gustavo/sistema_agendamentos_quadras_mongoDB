class Quadra:
    def __init__(self, num_quadra, capacidade):
        self.num_quadra = num_quadra
        self.capacidade = capacidade

    @property
    def id(self):
        return self.num_quadra

    def __repr__(self):
        return f"<Quadra {self.capacidade}>"
