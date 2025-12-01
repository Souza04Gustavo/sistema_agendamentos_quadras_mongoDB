# camada_negocio/servicos.py

from camada_dados.usuario_dao import UsuarioDAO
from camada_dados.quadra_dao import QuadraDAO
from modelos.usuario import Usuario, Aluno, Servidor, Funcionario, Admin
from camada_dados.material_dao import MaterialDAO
from camada_dados.ginasio_dao import GinasioDAO
from camada_dados.agendamento_dao import AgendamentoDAO
from camada_dados.chamado_dao import ChamadoDAO
from camada_dados.esporte_dao import EsporteDAO
from camada_dados.evento_dao import EventoDAO
from datetime import datetime, timedelta, time, date
from camada_dados.mongo_config import conectar_mongo
from bson import ObjectId
import re

class ServicoLogin:
    def __init__(self, nome_banco="udesc_quadras"):
        self.nome_banco = nome_banco
        self.usuario_dao = UsuarioDAO()

    def _get_client_db(self):
        # Recupera o objeto Database e extrai o client dele para poder fechar depois
        db = conectar_mongo()
        if db is None:
            return None, None
        return db.client, db

    def verificar_credenciais(self, email, senha):
        """
        Verifica se o email e a senha correspondem a um usuário no banco.
        """
        print(f"--- DENTRO DO SERVIÇO DE LOGIN ---")
        print(f"DEBUG[Serviço]: Buscando usuário com email: {email}")
        usuario = self.usuario_dao.buscar_por_email(email)

        # DEBUG: Vamos inspecionar o que o DAO retornou
        if usuario:
            print(f"DEBUG[Serviço]: Usuário encontrado no banco de dados! Nome: {usuario.nome}")
            
            # Comparação de senhas
            if usuario.senha == senha:
                print("DEBUG[Serviço]: As senhas COINCIDEM. Login validado com sucesso.")
                
                # Adiciona informação se é bolsista no objeto usuário
                # Garante que funcione mesmo se o atributo não existir
                if hasattr(usuario, 'categoria'):
                    cat = str(usuario.categoria).lower()
                    usuario.is_bolsista = (cat == "bolsista")
                else:
                    usuario.is_bolsista = False
                    
                return usuario 
            else:
                print("DEBUG[Serviço]: As senhas NÃO COINCIDEM. Login negado.")
                return None 
        else:
            print("DEBUG[Serviço]: Nenhum usuário foi encontrado com este email. Login negado.")
            return None 

class ServicoAdmin:
    def __init__(self, nome_banco="udesc_quadras"):
        self.nome_banco = nome_banco
        self.usuario_dao = UsuarioDAO()
        self.quadra_dao = QuadraDAO()
        self.material_dao = MaterialDAO()
        self.ginasio_dao = GinasioDAO()
        self.agendamento_dao = AgendamentoDAO()
        self.chamado_dao = ChamadoDAO()
        self.esporte_dao = EsporteDAO()
        self.evento_dao = EventoDAO()

    def _get_client_db(self):
        db = conectar_mongo()
        if db is None:
            return None, None
        return db.client, db

    def listar_usuarios(self):
        print("DEBUG[Serviço]: Solicitando a lista de todos os usuários ao DAO.")
        return self.usuario_dao.buscar_todos_os_usuarios()
    
    def alterar_status_usuario(self, cpf, status_atual):
        novo_status = 'inativo' if status_atual == 'ativo' else 'ativo'
        print(f"DEBUG[Serviço]: Alterando status do usuário CPF {cpf} para '{novo_status}'.")
        # Chama o DAO para efetivar a alteração no banco de dados
        return self.usuario_dao.atualizar_status_usuario(cpf, novo_status)

    def listar_quadras_para_gerenciar(self):
        """
        Busca e retorna a lista de todas as quadras para o painel de gerenciamento.
        """
        print("DEBUG[Serviço]: Solicitando a lista de todas as quadras ao DAO.")
        return self.ginasio_dao.buscar_todas_as_quadras()

    def alterar_status_quadra(self, id_ginasio, num_quadra, novo_status):
        """
        Repassa a solicitação de alteração de status da quadra para o DAO.
        """
        print(f"DEBUG[Serviço]: Alterando status da quadra {num_quadra} (Gin. {id_ginasio}) para '{novo_status}'.")
        return self.quadra_dao.atualizar_status_quadra(id_ginasio, num_quadra, novo_status)

    def remover_quadra(self, id_ginasio, num_quadra):
        """
        Repassa a solicitação de exclusão de uma quadra para o DAO.
        """
        print(f"DEBUG[Serviço]: Removendo quadra {num_quadra} do Ginásio {id_ginasio}.")
        return self.quadra_dao.excluir_quadra(id_ginasio, num_quadra)
    
    def adicionar_nova_quadra(self, id_ginasio, num_quadra, capacidade, tipo_piso, cobertura):
        """
        Verifica se a quadra já existe antes de repassar a solicitação
        de criação para o DAO.
        """
        print(f"DEBUG[Serviço]: Tentando adicionar nova quadra {num_quadra} ao Ginásio {id_ginasio}.")

        if self.ginasio_dao.quadra_existe(id_ginasio, num_quadra):
            print(f"ERRO[Serviço]: Tentativa de criar quadra duplicada (Nº {num_quadra}) no Ginásio {id_ginasio}.")
            return False # Retorna falha se a quadra já existir

        # Se a verificação passar, prossegue com a criação
        return self.ginasio_dao.criar_quadra(id_ginasio, num_quadra, capacidade, tipo_piso, cobertura)
    
    def remover_usuario(self, cpf):
        """
        Repassa a solicitação de exclusão de um usuário para o DAO.
        """
        print(f"DEBUG[Serviço]: Removendo usuário CPF {cpf}.")
        return self.usuario_dao.excluir_usuario(cpf)
    
    def criar_novo_usuario(self, dados_formulario):
        """
        Cria o objeto de usuário correto com base nos dados do formulário
        e o envia para o DAO para ser salvo.
        Retorna True em caso de sucesso, False em caso de falha.
        """
        tipo_usuario = dados_formulario.get('tipo_usuario')
        print(f"DEBUG[Serviço]: Tentando criar um novo usuário do tipo '{tipo_usuario}'.")

        novo_usuario = None
        try:
            # Dados comuns a todos os usuários
            dados_comuns = {
                'cpf': dados_formulario.get('cpf'),
                'nome': dados_formulario.get('nome'),
                'email': dados_formulario.get('email'),
                'senha': dados_formulario.get('senha'),
                'data_nasc': dados_formulario.get('data_nasc'),
                'status': 'ativo' # Novos usuários sempre começam como ativos
            }

            # Unifica a lógica de Aluno e Bolsista
            if tipo_usuario in ['aluno', 'Bolsista', 'bolsista']:
                # Argumentos base para qualquer aluno
                args_aluno = {
                    **dados_comuns,
                    'matricula': dados_formulario.get('matricula'),
                    'curso': dados_formulario.get('curso'),
                    'ano_inicio': dados_formulario.get('ano_inicio')
                }
                
                # Se for um bolsista, adiciona os campos extras
                if str(tipo_usuario).lower() == 'bolsista':
                    args_aluno['is_bolsista'] = True
                    args_aluno['categoria'] = 'bolsista'
                    args_aluno['valor_remuneracao'] = dados_formulario.get('valor_remuneracao')
                    args_aluno['carga_horaria'] = dados_formulario.get('carga_horaria')
                    args_aluno['horario_inicio'] = dados_formulario.get('horario_inicio')
                    args_aluno['horario_fim'] = dados_formulario.get('horario_fim')
                    args_aluno['id_supervisor_servidor'] = dados_formulario.get('id_supervisor_servidor')
                
                # Cria o objeto Aluno com os argumentos corretos
                novo_usuario = Aluno(**args_aluno)
            
            elif tipo_usuario == 'funcionario':
                novo_usuario = Funcionario(
                    **dados_comuns,
                    id_servidor=dados_formulario.get('id_servidor'),
                    data_admissao=dados_formulario.get('data_admissao'),
                    departamento=dados_formulario.get('departamento'),
                    cargo=dados_formulario.get('cargo')
                )

            elif tipo_usuario == 'admin':
                novo_usuario = Admin(
                    **dados_comuns,
                    id_servidor=dados_formulario.get('id_servidor'),
                    data_admissao=dados_formulario.get('data_admissao'),
                    nivel_acesso=dados_formulario.get('nivel_acesso', 1), # Usa 1 como padrão
                    area_responsabilidade=dados_formulario.get('area_responsabilidade')
                )

            else:
                print(f"Erro[Serviço]: Tipo de usuário '{tipo_usuario}' desconhecido.")
                return False

            # Se um objeto foi criado com sucesso, chama o DAO para salvá-lo
            if novo_usuario:
                return self.usuario_dao.salvar(novo_usuario)

        except Exception as e:
            print(f"Erro[Serviço]: Falha ao instanciar o objeto de usuário. Detalhes: {e}")
            return False
            
        return False
    
    def listar_materiais(self):
        """
        Busca e retorna a lista de todos os materiais esportivos.
        """
        print("DEBUG[Serviço]: Solicitando a lista de todos os materiais ao DAO.")
        return self.material_dao.buscar_todos()

    def adicionar_material(self, id_ginasio, nome, descricao, marca, status, qnt_total):
        """
        Repassa a solicitação de criação de um novo material para o DAO.
        """
        print(f"DEBUG[Serviço]: Adicionando novo material '{nome}'.")
        return self.material_dao.criar(id_ginasio, nome, descricao, marca, status, qnt_total)

    def atualizar_material(self, id_material, nome, descricao, marca, status, qnt_total, qnt_disponivel):
        """
        Repassa a solicitação de atualização de um material para o DAO.
        """
        print(f"DEBUG[Serviço]: Atualizando dados do material ID {id_material}.")
        # Aqui poderiam entrar regras de negócio, como:
        # if int(qnt_disponivel) > int(qnt_total):
        #     return False  # Não permitir que a quantidade disponível seja maior que a total
        return self.material_dao.atualizar(id_material, nome, descricao, marca, status, qnt_total, qnt_disponivel)

    def remover_material(self, id_material):
        """
        Repassa a solicitação de exclusão de um material para o DAO.
        """
        print(f"DEBUG[Serviço]: Removendo material ID {id_material}.")
        return self.material_dao.excluir(id_material)
    
    def listar_ginasios(self):
        """Busca e retorna a lista de todos os ginásios."""
        print("DEBUG[Serviço]: Solicitando a lista de todos os ginásios ao DAO.")
        return self.ginasio_dao.buscar_todos()

    def buscar_ginasio_por_id(self, id_ginasio):
        """Busca um ginásio específico por seu ID."""
        print(f"DEBUG[Serviço]: Buscando ginásio com ID {id_ginasio}.")
        return self.ginasio_dao.buscar_por_id(id_ginasio)

    def adicionar_ginasio(self, nome, endereco, capacidade):
        """Repassa a solicitação de criação de um novo ginásio para o DAO."""
        print(f"DEBUG[Serviço]: Adicionando novo ginásio '{nome}'.")
        return self.ginasio_dao.criar(nome, endereco, capacidade)

    def atualizar_ginasio(self, id_ginasio, nome, endereco, capacidade):
        """Repassa a solicitação de atualização de um ginásio para o DAO."""
        print(f"DEBUG[Serviço]: Atualizando dados do ginásio ID {id_ginasio}.")
        return self.ginasio_dao.atualizar(id_ginasio, nome, endereco, capacidade)

    def remover_ginasio(self, id_ginasio):
        """Repassa a solicitação de exclusão de um ginásio para o DAO."""
        print(f"DEBUG[Serviço]: Removendo ginásio ID {id_ginasio}.")
        return self.ginasio_dao.excluir(id_ginasio)
    
    def listar_todos_agendamentos(self):
        """
        Busca e retorna a lista de todos os agendamentos do sistema.
        """
        print("DEBUG[Serviço]: Solicitando a lista de todos os agendamentos ao DAO.")
        return self.agendamento_dao.buscar_todos_os_agendamentos()

    def cancelar_agendamento_admin(self, id_agendamento):
        """
        Cancela um agendamento específico em nome de um administrador.
        """
        print(f"DEBUG[Serviço]: Admin cancelando o agendamento ID {id_agendamento}.")
        # A regra de negócio aqui é que o admin sempre muda o status para 'cancelado'.
        novo_status = 'cancelado'
        return self.agendamento_dao.admin_atualizar_status(id_agendamento, novo_status)
    
    def listar_chamados_manutencao(self):
        """
        Busca e retorna a lista de todos os chamados de manutenção abertos.
        """
        print("DEBUG[Serviço]: Solicitando a lista de todos os chamados ao DAO.")
        return self.chamado_dao.buscar_todos()

    def resolver_chamado_manutencao(self, id_chamado):
        """
        Resolve um chamado de manutenção, excluindo-o da lista de pendências.
        """
        print(f"DEBUG[Serviço]: Resolvendo (excluindo) o chamado ID {id_chamado}.")
        return self.chamado_dao.excluir(id_chamado)
    
    def listar_esportes(self):
        """Busca e retorna a lista de todos os esportes."""
        print("DEBUG[Serviço]: Solicitando a lista de todos os esportes ao DAO.")
        return self.esporte_dao.buscar_todos()

    def buscar_esporte_por_id(self, id_esporte):
        """Busca um esporte específico por seu ID."""
        print(f"DEBUG[Serviço]: Buscando esporte com ID {id_esporte}.")
        return self.esporte_dao.buscar_por_id(id_esporte)

    def adicionar_esporte(self, nome, max_jogadores):
        """Repassa a solicitação de criação de um novo esporte para o DAO."""
        print(f"DEBUG[Serviço]: Adicionando novo esporte '{nome}'.")
        return self.esporte_dao.criar(nome, max_jogadores)

    def atualizar_esporte(self, id_esporte, nome, max_jogadores):
        """Repassa a solicitação de atualização de um esporte para o DAO."""
        print(f"DEBUG[Serviço]: Atualizando dados do esporte ID {id_esporte}.")
        return self.esporte_dao.atualizar(id_esporte, nome, max_jogadores)

    def remover_esporte(self, id_esporte):
        """Repassa a solicitação de exclusão de um esporte para o DAO."""
        print(f"DEBUG[Serviço]: Removendo esporte ID {id_esporte}.")
        return self.esporte_dao.excluir(id_esporte)
    
    def buscar_dados_para_associacao(self, id_ginasio, num_quadra):
        """
        Busca todos os dados necessários para a página de associação:
        - A lista de TODOS os esportes disponíveis no sistema.
        - A lista dos IDs de esportes que JÁ ESTÃO associados a esta quadra.
        Retorna um dicionário contendo ambas as listas.
        """
        print(f"DEBUG[Serviço]: Buscando dados para associar esportes à quadra {num_quadra} (Gin. {id_ginasio}).")
        
        # Busca todos os esportes que existem (usando o EsporteDAO)
        todos_os_esportes = self.esporte_dao.buscar_todos()
        
        # Busca os IDs dos esportes que já estão marcados para esta quadra (usando o QuadraDAO)
        esportes_ja_associados = self.quadra_dao.buscar_esportes_da_quadra(id_ginasio, num_quadra)
        
        return {
            'todos_esportes': todos_os_esportes,
            'esportes_associados_ids': esportes_ja_associados
        }

    def salvar_associacao_esportes_quadra(self, id_ginasio, num_quadra, lista_ids_esportes):
        """
        Repassa a lista de IDs de esportes selecionados para o QuadraDAO atualizar
        as associações no banco de dados.
        """
        print(f"DEBUG[Serviço]: Salvando associações de esportes para a quadra {num_quadra} (Gin. {id_ginasio}).")
        return self.quadra_dao.atualizar_esportes_da_quadra(id_ginasio, num_quadra, lista_ids_esportes)
    
    def listar_eventos(self):
        """Busca e retorna a lista de todos os eventos."""
        print("DEBUG[Serviço]: Solicitando a lista de todos os eventos ao DAO.")
        return self.evento_dao.buscar_todos()
    
    def adicionar_evento(self, cpf_admin_organizador, nome_evento, desc_evento, tipo_evento, dados_tempo, lista_quadras_str):
        """
        Verifica conflitos para todos os cenários antes de criar um novo evento.
        """
        print(f"\n--- INICIANDO PROCESSO DE CRIAÇÃO DE EVENTO ---")
        print(f"DEBUG[Serviço]: Tentando adicionar novo evento do tipo '{tipo_evento}'.")
        
        # --- ETAPA 1: Processar a lista de quadras ---
        lista_quadras_ids = []
        if lista_quadras_str:
            for quadra_str in lista_quadras_str:
                partes = quadra_str.split('-')
                if len(partes) == 2:
                    lista_quadras_ids.append((int(partes[0]), int(partes[1])))
        
        # --- ETAPA 2: Lógica de Validação de Conflitos ---
        
        # CENÁRIO A: Adicionando um Evento Extraordinário
        if tipo_evento == 'extraordinario':
            inicio_str = dados_tempo.get('inicio')
            fim_str = dados_tempo.get('fim')
            if not inicio_str or not fim_str:
                print("ERRO[Serviço]: Data de início ou fim do evento extraordinário não fornecida.")
                return False

            inicio_novo_evento = datetime.fromisoformat(inicio_str)
            fim_novo_evento = datetime.fromisoformat(fim_str)
            
            print(f"\n[CENÁRIO: EXTRAORDINÁRIO] Verificando conflitos de {inicio_novo_evento} a {fim_novo_evento}")

            for id_ginasio, num_quadra in lista_quadras_ids:
                print(f"\n  Verificando Quadra: {num_quadra} (Ginásio: {id_ginasio})")
                
                # 2.1 - Verifica contra agendamentos e outros eventos extraordinários
                if self.agendamento_dao.verificar_conflito_de_horario(id_ginasio, num_quadra, inicio_novo_evento, fim_novo_evento):
                    print(f"    [X] CONFLITO ENCONTRADO (Agendamento ou Evento Extraordinário).")
                    return False
                print(f"    [✓] Sem conflitos com agendamentos ou eventos extraordinários.")

                # 2.2 - Verifica contra eventos recorrentes
                eventos_recorrentes_existentes = self.evento_dao.buscar_recorrentes_por_quadra(id_ginasio, num_quadra)
                if not eventos_recorrentes_existentes:
                    print("    [✓] Sem eventos recorrentes para esta quadra. Verificação concluída para esta quadra.")
                    continue

                dia_da_semana_novo_evento_num = inicio_novo_evento.weekday() # Python: segunda=0, ..., domingo=6
                
                for ev_rec in eventos_recorrentes_existentes:
                    regra = ev_rec['regra_recorrencia']
                    print(f"    - Comparando com a regra existente: '{regra}'")
                    
                    match = re.search(r"Toda ([\w\s-]+), das (\d{2}:\d{2}) às (\d{2}:\d{2})", regra)
                    if not match:
                        print("      -> Aviso: Regra existente não correspondeu ao padrão, pulando.")
                        continue

                    dia_pt_existente, hora_ini_str_existente, hora_fim_str_existente = match.groups()
                    
                    dias_map_pt_para_num = { 'Segunda-feira': 0, 'Terça-feira': 1, 'Quarta-feira': 2, 'Quinta-feira': 3, 'Sexta-feira': 4, 'Sábado': 5, 'Domingo': 6 }
                    dia_existente_num = dias_map_pt_para_num.get(dia_pt_existente.strip())
                    
                    print(f"      -> Dia da regra: {dia_existente_num} vs Dia do novo evento: {dia_da_semana_novo_evento_num}")
                    
                    if dia_existente_num == dia_da_semana_novo_evento_num:
                        print("      -> DIAS DA SEMANA COINCIDEM! Verificando horários...")
                        hora_ini_existente = time.fromisoformat(hora_ini_str_existente)
                        hora_fim_existente = time.fromisoformat(hora_fim_str_existente)
                        hora_ini_novo = inicio_novo_evento.time()
                        hora_fim_novo = fim_novo_evento.time()
                        
                        print(f"        - Novo Evento: {hora_ini_novo} -> {hora_fim_novo}")
                        print(f"        - Regra Existente: {hora_ini_existente} -> {hora_fim_existente}")

                        if max(hora_ini_novo, hora_ini_existente) < min(hora_fim_novo, hora_fim_existente):
                            print(f"        [X] CONFLITO DE HORÁRIO COM EVENTO RECORRENTE ENCONTRADO!")
                            return False
                        
                        print("        [✓] Sem conflito de horário.")
                    else:
                        print("      -> Dias da semana não coincidem. Sem conflito.")

        # CENÁRIO B: Adicionando um Evento Recorrente
        elif tipo_evento == 'recorrente':
            print(f"\n[CENÁRIO: RECORRENTE] Verificando conflitos...")
            
            # --- Dados do NOVO evento recorrente ---
            dia_novo_evento_en = dados_tempo.get('dia_semana') # Ex: 'Monday'
            hora_ini_novo_evento = time.fromisoformat(dados_tempo.get('hora_inicio_recorrente'))
            hora_fim_novo_evento = time.fromisoformat(dados_tempo.get('hora_fim_recorrente'))
            data_fim_recorrencia = datetime.fromisoformat(dados_tempo.get('data_fim')).date()
            
            # Dicionários de mapeamento
            dias_en_para_num = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6}
            dia_novo_evento_num = dias_en_para_num.get(dia_novo_evento_en)

            if dia_novo_evento_num is None:
                print("ERRO[Serviço]: Dia da semana inválido para novo evento recorrente.")
                return False

            # --- Início da verificação para cada quadra ---
            for id_ginasio, num_quadra in lista_quadras_ids:
                print(f"\n  Verificando Quadra: {num_quadra} (Ginásio: {id_ginasio})")
                
                # 2.1 - VERIFICAÇÃO contra outros eventos recorrentes (lógica existente)
                eventos_recorrentes_existentes = self.evento_dao.buscar_recorrentes_por_quadra(id_ginasio, num_quadra)
                for ev_rec in eventos_recorrentes_existentes:
                    regra_existente = ev_rec['regra_recorrencia']
                    match = re.search(r"Toda ([\w\s-]+), das (\d{2}:\d{2}) às (\d{2}:\d{2})", regra_existente)
                    if match:
                        dia_pt_existente, hora_ini_str_existente, hora_fim_str_existente = match.groups()
                        dias_pt_map = { 'Toda Segunda-feira': 'Monday', 'Toda Terça-feira': 'Tuesday', 'Toda Quarta-feira': 'Wednesday', 'Toda Quinta-feira': 'Thursday', 'Toda Sexta-feira': 'Friday', 'Todo Sábado': 'Saturday', 'Todo Domingo': 'Sunday' }
                        dia_en_existente = dias_pt_map.get(f"Toda {dia_pt_existente.strip()}")
                        if dia_en_existente == dia_novo_evento_en:
                            hora_ini_existente = time.fromisoformat(hora_ini_str_existente)
                            hora_fim_existente = time.fromisoformat(hora_fim_str_existente)
                            if max(hora_ini_novo_evento, hora_ini_existente) < min(hora_fim_novo_evento, hora_fim_existente):
                                print(f"    [X] CONFLITO ENCONTRADO com outro evento recorrente.")
                                return False
                print(f"    [✓] Sem conflitos com outros eventos recorrentes.")

                # ======================= INÍCIO DA NOVA LÓGICA =======================
                # 2.2 - VERIFICAÇÃO contra agendamentos e eventos extraordinários
                
                # Simula o futuro: calcula todas as datas em que o evento vai ocorrer
                datas_da_recorrencia = []
                hoje = date.today()
                data_inicial_busca = hoje - timedelta(days=hoje.weekday())
                
                data_atual = data_inicial_busca
                print(f"    - Simulando ocorrências a partir de {data_atual} até {data_fim_recorrencia}...")
                while data_atual <= data_fim_recorrencia:
                    if data_atual.weekday() == dia_novo_evento_num:
                        datas_da_recorrencia.append(data_atual)
                    data_atual += timedelta(days=1)
                
                print(f"    - Simulando {len(datas_da_recorrencia)} ocorrências futuras para o evento recorrente...")

                for data_ocorrencia in datas_da_recorrencia:
                    # Monta o intervalo de tempo completo para cada ocorrência
                    inicio_ocorrencia = datetime.combine(data_ocorrencia, hora_ini_novo_evento)
                    fim_ocorrencia = datetime.combine(data_ocorrencia, hora_fim_novo_evento)
                    
                    print(f"      -> Verificando data {data_ocorrencia} das {hora_ini_novo_evento} às {hora_fim_novo_evento}...")

                    # Reutiliza o método do AgendamentoDAO para verificar conflitos nesta data/hora específica
                    if self.agendamento_dao.verificar_conflito_de_horario(id_ginasio, num_quadra, inicio_ocorrencia, fim_ocorrencia):
                        print(f"      [X] CONFLITO ENCONTRADO com agendamento/evento extraordinário na data {data_ocorrencia}!")
                        return False # Conflito encontrado, aborta a criação
                
                print(f"    [✓] Sem conflitos com agendamentos ou eventos extraordinários para esta quadra.")
                # ======================== FIM DA NOVA LÓGICA =========================

        # --- ETAPA 3: Se não houve conflitos, prossegue para a criação ---
        print("\n[✓] Todas as verificações de conflito passaram. Prosseguindo para a criação do evento.")
        if tipo_evento == 'recorrente':
            dia_semana = dados_tempo.get('dia_semana')
            hora_inicio = dados_tempo.get('hora_inicio_recorrente')
            hora_fim = dados_tempo.get('hora_fim_recorrente')
            dias_pt = { 'Monday': 'Toda Segunda-feira', 'Tuesday': 'Toda Terça-feira', 'Wednesday': 'Toda Quarta-feira', 'Thursday': 'Toda Quinta-feira', 'Friday': 'Toda Sexta-feira', 'Saturday': 'Todo Sábado', 'Sunday': 'Todo Domingo' }
            dia_formatado = dias_pt.get(dia_semana, dia_semana)
            dados_tempo['regra'] = f"{dia_formatado}, das {hora_inicio} às {hora_fim}"
            
        return self.evento_dao.criar(
            cpf_admin_organizador, nome_evento, desc_evento, tipo_evento,
            dados_tempo, lista_quadras_ids
        )
        
    def _criar_agendamento_para_evento(self, cpf_admin, id_ginasio, num_quadra, data_ini, data_fim, nome_evento):
        """
        Método auxiliar para criar um agendamento específico para um evento
        """
        try:
            from camada_dados.agendamento_dao import verificar_disponibilidade, criar_agendamento
            
            # Verificar disponibilidade antes de criar
            data_str = data_ini.strftime('%Y-%m-%d')
            hora_ini_str = data_ini.strftime('%H:%M')
            hora_fim_str = data_fim.strftime('%H:%M')
            
            disponivel = verificar_disponibilidade(id_ginasio, num_quadra, data_str, hora_ini_str, hora_fim_str)
            
            if disponivel:
                # Criar agendamento com status 'confirmado' para eventos
                sucesso = criar_agendamento(cpf_admin, id_ginasio, num_quadra, data_str, hora_ini_str, hora_fim_str, nome_evento)
                if sucesso:
                    print(f"DEBUG: Agendamento criado para evento '{nome_evento}' na quadra {num_quadra} em {data_ini}")
                else:
                    print(f"DEBUG: Erro ao criar agendamento para evento '{nome_evento}'")
            else:
                print(f"DEBUG: Conflito de horário para evento '{nome_evento}' na quadra {num_quadra} em {data_ini}")
                
        except Exception as e:
            print(f"Erro ao criar agendamento para evento: {e}")

    def remover_evento(self, id_evento):
        """Repassa a solicitação de exclusão de um evento para o DAO."""
        print(f"DEBUG[Serviço]: Removendo evento ID {id_evento}.")
        return self.evento_dao.excluir(id_evento)


class ServicoBolsista:
    def __init__(self, nome_banco="udesc_quadras"):
        # Reutiliza os DAOs existentes
        from camada_dados.usuario_dao import UsuarioDAO
        from camada_dados.agendamento_dao import AgendamentoDAO
        self.nome_banco = nome_banco
        self.usuario_dao = UsuarioDAO()
        self.agendamento_dao = AgendamentoDAO()

    def _get_client_db(self):
        """Helper para obter cliente e banco e fechar corretamente depois"""
        db = conectar_mongo()
        if db is None:
            return None, None
        return db.client, db

    def _buscar_agendamento_por_id_hibrido(self, db, id_agendamento):
        """
        Método auxiliar INTELIGENTE para achar o agendamento.
        Tenta buscar pelo _id (ObjectId) OU pelo campo string id_agendamento.
        """
        # Lista de filtros possíveis
        filtros = []
        
        # 1. Tenta buscar como string exata no campo personalizado
        filtros.append({"id_agendamento": str(id_agendamento)})
        
        # 2. Se parecer um ObjectId válido, tenta buscar no _id
        if ObjectId.is_valid(id_agendamento):
            filtros.append({"_id": ObjectId(id_agendamento)})
            
        # Busca com OR (ou um ou outro)
        query = {"$or": filtros}
        
        print(f"DEBUG[BUSCA]: Tentando encontrar agendamento com query: {query}")
        return db.agendamentos.find_one(query)

    def buscar_usuarios_para_agendamento(self, termo_busca):
        client, db = self._get_client_db()
        if client is None: 
            return []

        usuarios = []
        try:
            filtro = {
                "$and": [
                    {
                        "$or": [
                            {"nome": {"$regex": termo_busca, "$options": "i"}},
                            {"_id": {"$regex": f"^{termo_busca}"}}
                        ]
                    },
                    {"status": "ativo"}
                ]
            }
            # Mongo Collection: usuarios
            resultado = db.usuarios.find(filtro, {"_id": 1, "nome": 1, "email": 1}).sort("nome", 1).limit(20)

            for doc in resultado:
                cpf_val = doc.get("_id")
                usuarios.append({"cpf": cpf_val, "nome": doc.get("nome"), "email": doc.get("email")})

        except Exception as e:
            print(f"Erro ao buscar usuários: {e}")
        finally:
            client.close()
        return usuarios

    def fazer_agendamento_em_nome_de(self, cpf_bolsista, cpf_beneficiario, id_ginasio,
                                    num_quadra, hora_ini, hora_fim, motivo=None):
        client, db = self._get_client_db()
        if client is None: return False

        try:
            if isinstance(hora_ini, str): hora_ini = datetime.fromisoformat(hora_ini)
            if isinstance(hora_fim, str): hora_fim = datetime.fromisoformat(hora_fim)

            # Gera um ID string para garantir compatibilidade futura
            custom_id = str(ObjectId())

            novo_agendamento = {
                "id_agendamento": custom_id, 
                "cpf_usuario": cpf_beneficiario,
                "id_ginasio": int(id_ginasio),
                "num_quadra": int(num_quadra),
                "hora_ini": hora_ini,
                "hora_fim": hora_fim,
                "motivo": motivo,
                "status_agendamento": "confirmado",
                "id_bolsista_operador": cpf_bolsista,
                "data_operacao_bolsista": datetime.now()
            }

            db.agendamentos.insert_one(novo_agendamento)
            return True
        except Exception as e:
            print(f"Erro ao fazer agendamento: {e}")
            return False
        finally:
            client.close()

    def buscar_agendamentos_para_confirmacao(self, cpf_bolsista):
        client, db = self._get_client_db()
        if client is None: return []

        try:
            hoje = datetime.now().date()
            hoje_str = hoje.strftime("%Y-%m-%d")
            
            pipeline = [
                {"$match": {
                    "id_bolsista_operador": cpf_bolsista,
                    "status_agendamento": "confirmado",
                    "$expr": {"$eq": [{"$dateToString": {"format": "%Y-%m-%d", "date": "$hora_ini"}}, hoje_str]}
                }},
                {"$lookup": {"from": "ginasios", "localField": "id_ginasio", "foreignField": "_id", "as": "ginasio"}},
                {"$unwind": "$ginasio"},
                {"$lookup": {"from": "usuarios", "localField": "cpf_usuario", "foreignField": "_id", "as": "usuario"}},
                {"$unwind": "$usuario"},
                {"$project": {
                    "_id": 0,
                    # Garante que sempre tenhamos um ID string para o HTML
                    "id_agendamento": {"$ifNull": ["$id_agendamento", {"$toString": "$_id"}]},
                    "hora_ini": 1,
                    "hora_fim": 1,
                    "status_agendamento": 1,
                    "nome_ginasio": "$ginasio.nome",
                    "num_quadra": 1,
                    "nome_beneficiario": "$usuario.nome",
                    "cpf_beneficiario": "$usuario._id"
                }},
                {"$sort": {"hora_ini": 1}}
            ]
            return list(db.agendamentos.aggregate(pipeline))
        except Exception as e:
            print(f"Erro buscar confirmação: {e}")
            return []
        finally:
            client.close()

    def confirmar_comparecimento(self, id_agendamento, cpf_bolsista):
        """Confirma o comparecimento (usado no painel principal do bolsista)"""
        client, db = self._get_client_db()
        if client is None: return False

        try:
            # 1. Busca o documento
            agendamento = self._buscar_agendamento_por_id_hibrido(db, id_agendamento)

            if agendamento:
                # Verifica propriedade
                if agendamento.get("id_bolsista_operador") != cpf_bolsista:
                    print("DEBUG: Bolsista tentou confirmar agendamento de outro operador.")
                    # return False # Descomente se quiser restringir estritamente

                # 2. Atualiza usando o _id único encontrado
                result = db.agendamentos.update_one(
                    {"_id": agendamento["_id"]},
                    {"$set": {"status_agendamento": "realizado"}}
                )
                return result.modified_count > 0
            
            print(f"DEBUG: Agendamento {id_agendamento} não encontrado.")
            return False
        except Exception as e:
            print(f"Erro confirmar: {e}")
            return False
        finally:
            client.close()

    def cancelar_agendamento_bolsista(self, id_agendamento, cpf_bolsista):
        """Cancela um agendamento"""
        print(f"DEBUG[CANCELAR]: Iniciando para ID: {id_agendamento}")
        client, db = self._get_client_db()
        if client is None: return False

        try:
            # 1. Busca Híbrida
            agendamento = self._buscar_agendamento_por_id_hibrido(db, id_agendamento)

            if agendamento:
                # 2. Atualiza status
                result = db.agendamentos.update_one(
                    {"_id": agendamento["_id"]},
                    {"$set": {"status_agendamento": "cancelado"}}
                )
                
                if result.modified_count > 0:
                    print("DEBUG[CANCELAR]: Sucesso!")
                    return True
            
            print("DEBUG[CANCELAR]: Falha - agendamento não encontrado ou já cancelado.")
            return False
        except Exception as e:
            print(f"ERRO ao cancelar: {e}")
            import traceback; traceback.print_exc()
            return False
        finally:
            client.close()

    def buscar_todos_agendamentos_bolsista(self, cpf_bolsista):
        client, db = self._get_client_db()
        if client is None: return []

        try:
            pipeline = [
                {"$sort": {"hora_ini": -1}},
                {"$lookup": {"from": "usuarios", "localField": "cpf_usuario", "foreignField": "_id", "as": "usuario"}},
                {"$unwind": "$usuario"},
                {"$lookup": {"from": "ginasios", "localField": "id_ginasio", "foreignField": "_id", "as": "ginasio"}},
                {"$unwind": "$ginasio"},
                {"$project": {
                    "_id": 0,
                    "id_agendamento": {"$ifNull": ["$id_agendamento", {"$toString": "$_id"}]},
                    "hora_ini": 1,
                    "hora_fim": 1,
                    "status_agendamento": 1,
                    "num_quadra": 1,
                    "motivo": 1,
                    "data_solicitacao": 1,
                    "nome_ginasio": "$ginasio.nome",
                    "nome_beneficiario": "$usuario.nome",
                    "cpf_beneficiario": "$usuario._id"
                }}
            ]
            return list(db.agendamentos.aggregate(pipeline))
        except Exception as e:
            print(f"Erro buscar todos: {e}")
            return []
        finally:
            client.close()

    def marcar_como_concluido(self, id_agendamento, cpf_bolsista=None):
        """Marca como concluído (usado na lista geral de agendamentos)"""
        client, db = self._get_client_db()
        if client is None: return False

        try:
            # 1. Busca Híbrida
            ag = self._buscar_agendamento_por_id_hibrido(db, id_agendamento)
            
            if not ag:
                print(f"DEBUG: Agendamento {id_agendamento} não encontrado")
                return False

            # 2. Atualiza
            res = db.agendamentos.update_one(
                {"_id": ag["_id"]}, 
                {"$set": {"status_agendamento": "realizado"}}
            )
            return res.modified_count > 0
        except Exception as e:
            print(f"ERRO ao concluir: {e}")
            return False
        finally:
            client.close()

    def gerar_relatorio_uso(self, data_inicio, data_fim, id_ginasio=None):
        client, db = self._get_client_db()
        if client is None: return []

        try:
            def to_dt(v): return v if isinstance(v, datetime) else datetime.fromisoformat(v)
            dt_inicio = to_dt(data_inicio)
            dt_fim = to_dt(data_fim)

            match_stage = {"$match": {"hora_ini": {"$gte": dt_inicio, "$lte": dt_fim}}}
            if id_ginasio is not None:
                try: match_stage["$match"]["id_ginasio"] = int(id_ginasio)
                except: match_stage["$match"]["id_ginasio"] = id_ginasio

            pipeline = [
                match_stage,
                {
                    "$group": {
                        "_id": {"ginasio": "$local_info.nome_ginasio", "num_quadra": "$num_quadra", "id_ginasio": "$id_ginasio"},
                        "total_agendamentos": {"$sum": 1},
                        "confirmados": {"$sum": {"$cond": [{"$eq": ["$status_agendamento", "realizado"]}, 1, 0]}},
                        "cancelados": {"$sum": {"$cond": [{"$eq": ["$status_agendamento", "cancelado"]}, 1, 0]}}
                    }
                },
                {"$lookup": {"from": "ginasios", "localField": "_id.id_ginasio", "foreignField": "_id", "as": "info_ginasio"}},
                {"$unwind": {"path": "$info_ginasio", "preserveNullAndEmptyArrays": True}},
                {"$sort": {"_id.ginasio": 1, "_id.num_quadra": 1}}
            ]

            resultados = list(db.agendamentos.aggregate(pipeline))
            relatorio = []
            for item in resultados:
                nome_gin = item["_id"].get("ginasio")
                if not nome_gin and item.get("info_ginasio"):
                    nome_gin = item["info_ginasio"].get("nome")

                relatorio.append({
                    "ginasio": nome_gin or f"Ginásio {item['_id']['id_ginasio']}",
                    "num_quadra": item["_id"]["num_quadra"],
                    "total_agendamentos": item.get("total_agendamentos", 0),
                    "confirmados": item.get("confirmados", 0),
                    "cancelados": item.get("cancelados", 0)
                })
            return relatorio
        except Exception as e:
            print(f"Erro relatorio: {e}")
            return []
        finally:
            client.close()