class Ginasio:
    def __init__(self, id_ginasio, nome, endereco, capacidade):
        self.id_ginasio = id_ginasio
        self.nome = nome
        self.endereco = endereco
        self.capacidade = capacidade

    def __repr__(self):
        return f"<Ginasio {self.nome}>"

    @property
    def id(self):
        return self.id_ginasio
