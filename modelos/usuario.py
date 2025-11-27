
class Usuario:
    def __init__(self, cpf, nome, email, senha, data_nasc, status='ativo'):
        self.cpf = cpf
        self.nome = nome
        self.email = email
        self.senha = senha
        self.data_nasc = data_nasc
        self.status = status


class Aluno(Usuario):
    def __init__(self, cpf, nome, email, senha, data_nasc, matricula, curso, ano_inicio,
                status='ativo', categoria=None, valor_remuneracao=None, carga_horaria=None,
                horario_inicio=None, horario_fim=None, id_supervisor_servidor=None):
        super().__init__(cpf, nome, email, senha, data_nasc, status)
        self.matricula = matricula
        self.curso = curso
        self.ano_inicio = ano_inicio
        self.categoria = categoria
        self.valor_remuneracao = valor_remuneracao
        self.carga_horaria = carga_horaria
        self.horario_inicio = horario_inicio
        self.horario_fim = horario_fim
        self.id_supervisor_servidor = id_supervisor_servidor
        self.tipo = "aluno"


class Servidor(Usuario):
    def __init__(self, cpf, nome, email, senha, data_nasc, id_servidor, data_admissao, status='ativo'):
        super().__init__(cpf, nome, email, senha, data_nasc, status)
        self.id_servidor = id_servidor
        self.data_admissao = data_admissao
        self.tipo = "servidor"


class Funcionario(Servidor):
    def __init__(self, cpf, nome, email, senha, data_nasc, id_servidor, data_admissao, departamento, cargo, status='ativo'):
        super().__init__(cpf, nome, email, senha, data_nasc, id_servidor, data_admissao, status)
        self.departamento = departamento
        self.cargo = cargo
        self.tipo = "funcionario"


class Admin(Servidor):
    def __init__(self, cpf, nome, email, senha, data_nasc, id_servidor, data_admissao,
                status= 'ativo', nivel_acesso=1, area_responsabilidade=None, data_ultimo_login=None):
        super().__init__(cpf, nome, email, senha, data_nasc, id_servidor, data_admissao, status)
        self.nivel_acesso = nivel_acesso
        self.area_responsabilidade = area_responsabilidade
        self.data_ultimo_login = data_ultimo_login
        self.tipo = "admin"
