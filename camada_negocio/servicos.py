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
import re

class ServicoLogin:
    def __init__(self):
        self.usuario_dao = UsuarioDAO()

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
            print(f"DEBUG[Serviço]: Agora, vamos comparar as senhas.")
            print(f"   -> Senha que veio do formulário: '{senha}'")
            print(f"   -> Senha que está no banco:    '{usuario.senha}'")

            # Comparação de senhas
            if usuario.senha == senha:
                print("DEBUG[Serviço]: As senhas COINCIDEM. Login validado com sucesso.")
                
                # Adiciona informação se é bolsista no objeto usuário
                if hasattr(usuario, 'categoria'):
                    usuario.is_bolsista = (usuario.categoria == "Bolsista")
                else:
                    usuario.is_bolsista = False
                    
                return usuario # Retorna o objeto do usuário, indicando sucesso
            else:
                print("DEBUG[Serviço]: As senhas NÃO COINCIDEM. Login negado.")
                return None # Retorna None, indicando falha
        else:
            print("DEBUG[Serviço]: Nenhum usuário foi encontrado com este email. Login negado.")
            return None # Retorna None, indicando falha

class ServicoAdmin:
    def __init__(self):
        self.usuario_dao = UsuarioDAO()
        self.quadra_dao = QuadraDAO()
        self.material_dao = MaterialDAO()
        self.ginasio_dao = GinasioDAO()
        self.agendamento_dao = AgendamentoDAO()
        self.chamado_dao = ChamadoDAO()
        self.esporte_dao = EsporteDAO()
        self.evento_dao = EventoDAO()

    def listar_usuarios(self):
        print("DEBUG[Serviço]: Solicitando a lista de todos os usuários ao DAO.")
        usuarios = self.usuario_dao.buscar_todos_os_usuarios()
        
        return usuarios
    
    def alterar_status_usuario(self, cpf, status_atual):
        novo_status = 'inativo' if status_atual == 'ativo' else 'ativo'
        
        print(f"DEBUG[Serviço]: Alterando status do usuário CPF {cpf} para '{novo_status}'.")

        # Chama o DAO para efetivar a alteração no banco de dados
        sucesso = self.usuario_dao.atualizar_status_usuario(cpf, novo_status)

        return sucesso

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
            if tipo_usuario in ['aluno', 'bolsista']:
                # Argumentos base para qualquer aluno
                args_aluno = {
                    **dados_comuns,
                    'matricula': dados_formulario.get('matricula'),
                    'curso': dados_formulario.get('curso'),
                    'ano_inicio': dados_formulario.get('ano_inicio')
                }
                
                # Se for um bolsista, adiciona os campos extras
                if tipo_usuario == 'bolsista':
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
    def __init__(self):
        # Reutiliza os DAOs existentes
        from camada_dados.usuario_dao import UsuarioDAO
        from camada_dados.agendamento_dao import AgendamentoDAO
        self.usuario_dao = UsuarioDAO()
        self.agendamento_dao = AgendamentoDAO()

    def buscar_usuarios_para_agendamento(self, termo_busca):
        """Busca usuários ativos por nome ou CPF para agendamento em nome de terceiros"""
        conexao = self._conectar_banco()
        if not conexao:
            return []
            
        cursor = conexao.cursor()
        usuarios = []
        
        try:
            query = """
                SELECT cpf, nome, email 
                FROM usuario 
                WHERE (nome ILIKE %s OR cpf LIKE %s) 
                AND status = 'ativo'
                ORDER BY nome
                LIMIT 20
            """
            termo_like = f"%{termo_busca}%"
            termo_cpf = f"{termo_busca}%"
            
            cursor.execute(query, (termo_like, termo_cpf))
            resultados = cursor.fetchall()
            
            for cpf, nome, email in resultados:
                usuarios.append({'cpf': cpf, 'nome': nome, 'email': email})
                
        except Exception as e:
            print(f"Erro ao buscar usuários: {e}")
        finally:
            cursor.close()
            conexao.close()
            
        return usuarios

    def fazer_agendamento_em_nome_de(self, cpf_bolsista, cpf_beneficiario, id_ginasio, 
                                   num_quadra, hora_ini, hora_fim, motivo=None):
        """Faz agendamento em nome de outro usuário"""
        conexao = self._conectar_banco()
        if not conexao:
            return False
            
        cursor = conexao.cursor()
        sucesso = False
        
        try:
            query = """
                INSERT INTO agendamento 
                (cpf_usuario, id_ginasio, num_quadra, hora_ini, hora_fim, motivo, 
                 status_agendamento, id_bolsista_operador, data_operacao_bolsista)
                VALUES (%s, %s, %s, %s, %s, %s, 'confirmado', %s, CURRENT_TIMESTAMP)
            """
            
            cursor.execute(query, (cpf_beneficiario, id_ginasio, num_quadra, 
                                 hora_ini, hora_fim, motivo, cpf_bolsista))
            conexao.commit()
            sucesso = True
            
        except Exception as e:
            conexao.rollback()
            print(f"Erro ao fazer agendamento em nome de terceiro: {e}")
        finally:
            cursor.close()
            conexao.close()
            
        return sucesso

    def buscar_agendamentos_para_confirmacao(self, cpf_bolsista):
        """Busca agendamentos feitos pelo bolsista que precisam de confirmação"""
        conexao = self._conectar_banco()
        if not conexao:
            return []
            
        cursor = conexao.cursor()
        agendamentos = []
        
        try:
            query = """
                SELECT 
                    a.id_agendamento, a.hora_ini, a.hora_fim, a.status_agendamento,
                    g.nome as nome_ginasio, a.num_quadra,
                    u.nome as nome_beneficiario, u.cpf as cpf_beneficiario
                FROM agendamento a
                JOIN ginasio g ON a.id_ginasio = g.id_ginasio
                JOIN usuario u ON a.cpf_usuario = u.cpf
                WHERE a.id_bolsista_operador = %s 
                AND a.status_agendamento = 'confirmado'
                AND DATE(a.hora_ini) = CURRENT_DATE
                ORDER BY a.hora_ini
            """
            
            cursor.execute(query, (cpf_bolsista,))
            resultados = cursor.fetchall()
            
            for row in resultados:
                agendamentos.append({
                    'id_agendamento': row[0],
                    'hora_ini': row[1],
                    'hora_fim': row[2],
                    'status_agendamento': row[3],
                    'nome_ginasio': row[4],
                    'num_quadra': row[5],
                    'nome_beneficiario': row[6],
                    'cpf_beneficiario': row[7]
                })
                
        except Exception as e:
            print(f"Erro ao buscar agendamentos para confirmação: {e}")
        finally:
            cursor.close()
            conexao.close()
            
        return agendamentos

    def confirmar_comparecimento(self, id_agendamento, cpf_bolsista):
        """Confirma o comparecimento do usuário no agendamento"""
        conexao = self._conectar_banco()
        if not conexao:
            return False
            
        cursor = conexao.cursor()
        sucesso = False
        
        try:
            # Verifica se o agendamento foi feito por este bolsista
            query_verifica = """
                SELECT id_agendamento FROM agendamento 
                WHERE id_agendamento = %s AND id_bolsista_operador = %s
            """
            cursor.execute(query_verifica, (id_agendamento, cpf_bolsista))
            
            if cursor.fetchone():
                query_confirma = """
                    UPDATE agendamento 
                    SET status_agendamento = 'realizado'
                    WHERE id_agendamento = %s
                """
                cursor.execute(query_confirma, (id_agendamento,))
                conexao.commit()
                sucesso = True
                
        except Exception as e:
            conexao.rollback()
            print(f"Erro ao confirmar comparecimento: {e}")
        finally:
            cursor.close()
            conexao.close()
            
        return sucesso


    def cancelar_agendamento_bolsista(self, id_agendamento, cpf_bolsista):
        """Cancela um agendamento feito pelo bolsista"""
        print(f"DEBUG[CANCELAR]: Iniciando cancelamento - Agendamento: {id_agendamento}, Bolsista: {cpf_bolsista}")
        
        conexao = self._conectar_banco()
        if not conexao:
            print("DEBUG[CANCELAR]: Falha na conexão com o banco")
            return False
            
        cursor = conexao.cursor()
        sucesso = False
        
        try:
            # Primeiro, vamos verificar TODOS os agendamentos para debug
            query_debug = "SELECT id_agendamento, cpf_usuario, status_agendamento FROM agendamento WHERE id_agendamento = %s"
            cursor.execute(query_debug, (id_agendamento,))
            agendamento_debug = cursor.fetchone()
            
            print(f"DEBUG[CANCELAR]: Resultado da busca direta: {agendamento_debug}")
            
            if not agendamento_debug:
                print(f"DEBUG[CANCELAR]: Agendamento {id_agendamento} realmente não existe na tabela")
                return False
            
            # Agora vamos verificar com a query original
            query_verifica = """
                SELECT id_agendamento, status_agendamento 
                FROM agendamento 
                WHERE id_agendamento = %s
            """
            cursor.execute(query_verifica, (id_agendamento,))
            agendamento = cursor.fetchone()
            
            print(f"DEBUG[CANCELAR]: Resultado da verificação: {agendamento}")
            
            if agendamento:
                print(f"DEBUG[CANCELAR]: Agendamento encontrado - ID: {agendamento[0]}, Status atual: {agendamento[1]}")
                
                # Atualizar o status para 'cancelado'
                query_cancelar = """
                    UPDATE agendamento 
                    SET status_agendamento = 'cancelado'
                    WHERE id_agendamento = %s
                """
                cursor.execute(query_cancelar, (id_agendamento,))
                conexao.commit()
                
                # Verificar se realmente foi atualizado
                cursor.execute("SELECT status_agendamento FROM agendamento WHERE id_agendamento = %s", (id_agendamento,))
                novo_status = cursor.fetchone()
                print(f"DEBUG[CANCELAR]: Status após atualização: {novo_status}")
                
                sucesso = True
                print(f"DEBUG[CANCELAR]: Agendamento {id_agendamento} cancelado com sucesso")
            else:
                print(f"DEBUG[CANCELAR]: Agendamento {id_agendamento} não encontrado na verificação")
                
        except Exception as e:
            conexao.rollback()
            print(f"ERRO ao cancelar agendamento: {e}")
            import traceback
            traceback.print_exc()
        finally:
            cursor.close()
            conexao.close()
            
        return sucesso

    def buscar_todos_agendamentos_bolsista(self, cpf_bolsista):
        """Busca todos os agendamentos feitos pelo bolsista"""
        print(f"DEBUG[ServicoBolsista]: Buscando agendamentos para bolsista CPF: {cpf_bolsista}")
        
        conexao = self._conectar_banco()
        if not conexao:
            print("DEBUG[ServicoBolsista]: Falha na conexão com o banco")
            return []
            
        cursor = conexao.cursor()
        agendamentos = []
        
        try:
            query = """
                SELECT 
                    a.id_agendamento, a.hora_ini, a.hora_fim, a.status_agendamento,
                    g.nome as nome_ginasio, a.num_quadra,
                    u.nome as nome_beneficiario, u.cpf as cpf_beneficiario,
                    a.motivo, a.data_solicitacao
                FROM agendamento a
                JOIN ginasio g ON a.id_ginasio = g.id_ginasio
                JOIN usuario u ON a.cpf_usuario = u.cpf
                ORDER BY a.hora_ini DESC
            """
            
            print(f"DEBUG[ServicoBolsista]: Executando query: {query}")
            print(f"DEBUG[ServicoBolsista]: Parâmetro: {cpf_bolsista}")
            
            cursor.execute(query, (cpf_bolsista,))
            resultados = cursor.fetchall()
            
            print(f"DEBUG[ServicoBolsista]: {len(resultados)} agendamentos encontrados")
            
            for row in resultados:
                agendamento = {
                    'id_agendamento': row[0],
                    'hora_ini': row[1],
                    'hora_fim': row[2],
                    'status_agendamento': row[3],
                    'nome_ginasio': row[4],
                    'num_quadra': row[5],
                    'nome_beneficiario': row[6],
                    'cpf_beneficiario': row[7],
                    'motivo': row[8],
                    'data_solicitacao': row[9]
                }
                print(f"DEBUG[ServicoBolsista]: Agendamento encontrado: {agendamento}")
                agendamentos.append(agendamento)
                
        except Exception as e:
            print(f"ERRO ao buscar todos os agendamentos do bolsista: {e}")
            import traceback
            traceback.print_exc()
        finally:
            cursor.close()
            conexao.close()
            
        return agendamentos


    def marcar_como_concluido(self, id_agendamento, cpf_bolsista):
        """Marca um agendamento como concluído/realizado"""
        print(f"DEBUG: Tentando marcar agendamento {id_agendamento} como concluído pelo bolsista {cpf_bolsista}")
        
        conexao = self._conectar_banco()
        if not conexao:
            return False
            
        cursor = conexao.cursor()
        sucesso = False
        
        try:
            query_verifica = """
                SELECT id_agendamento, status_agendamento 
                FROM agendamento 
                WHERE id_agendamento = %s
            """
            cursor.execute(query_verifica, (id_agendamento,))
            agendamento = cursor.fetchone()
            
            if agendamento:
                print(f"DEBUG: Agendamento encontrado - ID: {agendamento[0]}, Status atual: {agendamento[1]}")
                
                # Atualizar o status para 'realizado'
                query_concluir = """
                    UPDATE agendamento 
                    SET status_agendamento = 'realizado'
                    WHERE id_agendamento = %s
                """
                cursor.execute(query_concluir, (id_agendamento,))
                conexao.commit()
                sucesso = True
                print(f"DEBUG: Agendamento {id_agendamento} marcado como realizado com sucesso")
            else:
                print(f"DEBUG: Agendamento {id_agendamento} não encontrado")
                
        except Exception as e:
            conexao.rollback()
            print(f"ERRO ao marcar agendamento como concluído: {e}")
            import traceback
            traceback.print_exc()
        finally:
            cursor.close()
            conexao.close()
            
        return sucesso

    def gerar_relatorio_uso(self, data_inicio, data_fim, id_ginasio=None):
        """Gera relatório básico de uso das quadras"""
        conexao = self._conectar_banco()
        if not conexao:
            return []
            
        cursor = conexao.cursor()
        relatorio = []
        
        try:
            query_base = """
                SELECT 
                    g.nome as ginásio,
                    a.num_quadra,
                    COUNT(*) as total_agendamentos,
                    COUNT(CASE WHEN a.status_agendamento = 'realizado' THEN 1 END) as confirmados,
                    COUNT(CASE WHEN a.status_agendamento = 'cancelado' THEN 1 END) as cancelados
                FROM agendamento a
                JOIN ginasio g ON a.id_ginasio = g.id_ginasio
                WHERE a.hora_ini BETWEEN %s AND %s
            """
            
            params = [data_inicio, data_fim]
            
            if id_ginasio:
                query_base += " AND a.id_ginasio = %s"
                params.append(id_ginasio)
                
            query_base += """
                GROUP BY g.nome, a.num_quadra
                ORDER BY g.nome, a.num_quadra
            """
            
            cursor.execute(query_base, params)
            resultados = cursor.fetchall()
            
            for row in resultados:
                relatorio.append({
                    'ginasio': row[0],
                    'num_quadra': row[1],
                    'total_agendamentos': row[2],
                    'confirmados': row[3],
                    'cancelados': row[4]
                })
                
        except Exception as e:
            print(f"Erro ao gerar relatório: {e}")
        finally:
            cursor.close()
            conexao.close()
            
        return relatorio

    def _conectar_banco(self):
        """Método auxiliar para conexão com o banco"""
        try:
            from camada_dados.mongo_config import conectar_banco
            return conectar_banco()
        except Exception as e:
            print(f"Erro ao conectar com banco: {e}")
            return None