# modelos/usuario.py

class Usuario:
    def __init__(self, cpf, nome, email, senha, data_nasc, status='ativo', tipo='usuario'):
        self.cpf = cpf 
        self.nome = nome
        self.email = email
        self.senha = senha
        self.data_nasc = data_nasc
        self.status = status
        self.tipo = tipo

class Aluno(Usuario):
    # O segredo está aqui: **kwargs aceita qualquer campo extra do MongoDB sem dar erro
    def __init__(self, cpf, nome, email, senha, data_nasc, matricula, curso, ano_inicio, status='ativo', is_bolsista=False, **kwargs):
        super().__init__(cpf, nome, email, senha, data_nasc, status, tipo='aluno')
        
        self.matricula = matricula
        self.curso = curso
        self.ano_inicio = ano_inicio
        self.is_bolsista = is_bolsista
        
        # Se for bolsista, pega os dados extras
        if is_bolsista:
            self.categoria = "bolsista"
            self.valor_remuneracao = kwargs.get('valor_remuneracao')
            self.carga_horaria = kwargs.get('carga_horaria')
            self.horario_inicio = kwargs.get('horario_inicio')
            self.horario_fim = kwargs.get('horario_fim')
            self.id_supervisor_servidor = kwargs.get('id_supervisor_servidor')
        else:
            self.categoria = "nao_bolsista"
            self.valor_remuneracao = None

    def get_document_mongo(self):
        """Prepara o dicionário para salvar no MongoDB"""
        doc = {
            "_id": self.cpf,
            "nome": self.nome,
            "email": self.email,
            "senha": self.senha,
            "data_nasc": self.data_nasc,
            "status": self.status,
            "tipo": "aluno",
            "detalhes_aluno": {
                "matricula": self.matricula,
                "curso": self.curso,
                "ano_inicio": self.ano_inicio,
                "categoria": getattr(self, 'categoria', 'nao_bolsista')
            }
        }
        if self.is_bolsista:
            doc["detalhes_aluno"].update({
                "valor_remuneracao": self.valor_remuneracao,
                "carga_horaria": self.carga_horaria,
                "horario_inicio": self.horario_inicio,
                "horario_fim": self.horario_fim,
                "id_supervisor_servidor": self.id_supervisor_servidor
            })
        return doc

class Funcionario(Usuario):
    def __init__(self, cpf, nome, email, senha, data_nasc, id_servidor, data_admissao, departamento, cargo, status='ativo', **kwargs):
        super().__init__(cpf, nome, email, senha, data_nasc, status, tipo='funcionario')
        self.id_servidor = id_servidor
        self.data_admissao = data_admissao
        self.departamento = departamento
        self.cargo = cargo

class Admin(Usuario):
    def __init__(self, cpf, nome, email, senha, data_nasc, id_servidor, data_admissao, nivel_acesso=1, area_responsabilidade=None, status='ativo', **kwargs):
        super().__init__(cpf, nome, email, senha, data_nasc, status, tipo='admin')
        self.id_servidor = id_servidor
        self.data_admissao = data_admissao
        self.nivel_acesso = nivel_acesso
        self.area_responsabilidade = area_responsabilidade

class Servidor(Usuario):
    def __init__(self, cpf, nome, email, senha, data_nasc, id_servidor, data_admissao, status='ativo', **kwargs):
        super().__init__(cpf, nome, email, senha, data_nasc, status, tipo='servidor')
        self.id_servidor = id_servidor
        self.data_admissao = data_admissao