from camada_dados.mongo_config import conectar_mongo
import psycopg2.extras
from bson import ObjectId
from modelos.ginasio import Ginasio
from modelos.quadra import Quadra
from datetime import datetime

class AgendamentoDAO:
    
    # --- Metodos originais do PostgreSQL---
    '''
    def buscar_todos_os_agendamentos(self):
        """
        Busca todos os agendamentos do sistema, juntando informações do usuário e do ginásio.
        Retorna uma lista de dicionários.
        """
        conexao = conectar_mongo()
        if not conexao:
            return []
        
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.DictCursor)
        agendamentos = []
        try:
            query = """
                SELECT
                    a.id_agendamento,
                    a.hora_ini,
                    a.hora_fim,
                    a.status_agendamento,
                    a.num_quadra,
                    g.nome AS nome_ginasio,
                    u.nome AS nome_usuario
                FROM
                    agendamento a
                JOIN
                    usuario u ON a.cpf_usuario = u.cpf
                JOIN
                    ginasio g ON a.id_ginasio = g.id_ginasio
                ORDER BY
                    a.hora_ini DESC;
            """
            cursor.execute(query)
            resultados = cursor.fetchall()
            for linha in resultados:
                agendamentos.append(dict(linha))
            print(f"DEBUG[DAO]: {len(agendamentos)} agendamentos totais encontrados.")
        except Exception as e:
            print(f"Erro ao buscar todos os agendamentos: {e}")
        finally:
            cursor.close()
            conexao.close()
        return agendamentos

    def admin_atualizar_status(self, id_agendamento, novo_status):
        """
        Permite que um administrador altere o status de qualquer agendamento.
        Retorna True em caso de sucesso, False em caso de falha.
        """
        if novo_status not in ['confirmado', 'cancelado', 'realizado', 'nao_compareceu']:
            print(f"Erro: Status '{novo_status}' é inválido.")
            return False

        conexao = conectar_mongo()
        if not conexao:
            return False
            
        cursor = conexao.cursor()
        sucesso = False
        try:
            # Corrigido para usar a chave primária correta: id_agendamento
            query = "UPDATE agendamento SET status_agendamento = %s WHERE id_agendamento = %s"
            cursor.execute(query, (novo_status, id_agendamento))
            conexao.commit()
            if cursor.rowcount > 0:
                sucesso = True
                print(f"DEBUG[DAO]: Status do agendamento ID {id_agendamento} atualizado para '{novo_status}'.")
        except Exception as e:
            conexao.rollback()
            print(f"Erro ao atualizar status do agendamento (admin): {e}")
        finally:
            cursor.close()
            conexao.close()
        return sucesso

    def buscar_agendamentos_por_usuario(self, cpf_usuario):
        """
        Retorna todos os agendamentos realizados por um determinado usuário.
        (Refatorado para ser um método de classe)
        """
        conexao = conectar_mongo()
        if not conexao:
            return []
            
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.DictCursor)
        agendamentos = []
        try:
            query = """
                SELECT a.id_agendamento, a.data_solicitacao, a.hora_ini, a.hora_fim, a.status_agendamento,
                       a.num_quadra, g.nome AS nome_ginasio
                FROM agendamento a
                JOIN ginasio g ON a.id_ginasio = g.id_ginasio
                WHERE a.cpf_usuario = %s
                ORDER BY a.hora_ini DESC;
            """
            cursor.execute(query, (cpf_usuario,))
            resultados = cursor.fetchall()
            for row in resultados:
                agendamentos.append(dict(row))
        except Exception as e:
            print(f"Erro ao buscar agendamentos por usuário: {e}")
        finally:
            cursor.close()
            conexao.close()
        return agendamentos

    def buscar_agendamentos_por_quadra(self, id_ginasio, num_quadra, data_inicio, data_fim):
        """
        Busca AGENDAMENTOS, EVENTOS EXTRAORDINÁRIOS e EVENTOS RECORRENTES
        para uma quadra específica dentro de um intervalo de datas.
        """
        conexao = conectar_mongo()
        if not conexao:
            return []
            
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.DictCursor)
        ocupacoes = []
        try:
            # Query com UNION ALL para juntar os três tipos de ocupação
            query = """
                -- Parte 1: Busca os AGENDAMENTOS normais
                SELECT 
                    'agendamento' as tipo_ocupacao, hora_ini, hora_fim,
                    status_agendamento as status,
                    NULL as nome_evento,
                    NULL as regra_recorrencia -- Nova coluna para compatibilidade
                FROM agendamento
                WHERE 
                    id_ginasio = %s AND num_quadra = %s
                    AND status_agendamento != 'cancelado'
                    AND (hora_ini, hora_fim) OVERLAPS (TIMESTAMP %s, TIMESTAMP %s)

                UNION ALL

                -- Parte 2: Busca os EVENTOS EXTRAORDINÁRIOS
                SELECT 
                    'evento' as tipo_ocupacao, ex.data_hora_inicio as hora_ini, ex.data_hora_fim as hora_fim,
                    'bloqueado' as status,
                    e.nome as nome_evento,
                    NULL as regra_recorrencia -- Nova coluna para compatibilidade
                FROM evento_quadra eq
                JOIN evento e ON eq.id_evento = e.id_evento
                JOIN extraordinario ex ON e.id_evento = ex.id_evento
                WHERE
                    eq.id_ginasio = %s AND eq.num_quadra = %s
                    AND (ex.data_hora_inicio, ex.data_hora_fim) OVERLAPS (TIMESTAMP %s, TIMESTAMP %s)
                
                UNION ALL

                -- Parte 3: Busca os EVENTOS RECORRENTES
                SELECT
                    'evento' as tipo_ocupacao,
                    NULL as hora_ini, NULL as hora_fim,
                    'recorrente' as status,
                    e.nome as nome_evento, -- Agora pega o NOME real do evento
                    r.regra_recorrencia as regra_recorrencia -- E a regra em sua própria coluna
                FROM evento_quadra eq
                JOIN evento e ON eq.id_evento = e.id_evento
                JOIN recorrente r ON e.id_evento = r.id_evento
                WHERE
                    eq.id_ginasio = %s AND eq.num_quadra = %s
                    AND r.data_fim_recorrencia >= %s;
            """
            
            parametros = (
                id_ginasio, num_quadra, data_inicio, data_fim,  # Para agendamentos
                id_ginasio, num_quadra, data_inicio, data_fim,  # Para eventos extraordinários
                id_ginasio, num_quadra, data_inicio           # Para eventos recorrentes (só precisa da data de início do período)
            )

            cursor.execute(query, parametros)
            
            resultados = cursor.fetchall()
            for row in resultados:
                ocupacoes.append(dict(row))
                
            print(f"DEBUG[DAO]: Encontradas {len(ocupacoes)} ocupações (agendamentos + eventos).")
                
        except Exception as e:
            print(f"Erro ao buscar agendamentos e eventos por quadra: {e}")
        finally:
            cursor.close()
            conexao.close()
        return ocupacoes
    
    def verificar_conflito_de_horario(self, id_ginasio, num_quadra, inicio, fim):
        """
        Verifica se existe qualquer agendamento ou evento extraordinário que se sobrepõe
        a um dado intervalo de tempo para uma quadra específica.
        Retorna True se houver conflito, False caso contrário.
        """
        conexao = conectar_mongo()
        if not conexao:
            return True 
            
        cursor = conexao.cursor()
        try:
            query = """
                SELECT 1 FROM agendamento
                WHERE id_ginasio = %s AND num_quadra = %s
                AND status_agendamento != 'cancelado'
                AND (hora_ini, hora_fim) OVERLAPS (TIMESTAMP %s, TIMESTAMP %s)
                
                UNION ALL

                SELECT 1 FROM evento_quadra eq
                JOIN extraordinario ex ON eq.id_evento = ex.id_evento
                WHERE eq.id_ginasio = %s AND eq.num_quadra = %s
                AND (ex.data_hora_inicio, ex.data_hora_fim) OVERLAPS (TIMESTAMP %s, TIMESTAMP %s)
                
                LIMIT 1;
            """
            
            # ======================= INÍCIO DA CORREÇÃO =======================
            
            # Formata os objetos datetime para strings no formato ISO 8601
            # Ex: '2025-11-13 07:00:00'
            inicio_str = inicio.isoformat(" ")
            fim_str = fim.isoformat(" ")

            parametros = (
                id_ginasio, num_quadra, inicio_str, fim_str,
                id_ginasio, num_quadra, inicio_str, fim_str
            )
            
            # ======================== FIM DA CORREÇÃO =========================
            
            cursor.execute(query, parametros)
            
            conflito_encontrado = cursor.fetchone() is not None
            
            if conflito_encontrado:
                print(f"DEBUG[DAO]: Conflito de horário ENCONTRADO para a quadra {num_quadra} (Gin. {id_ginasio}) entre {inicio_str} e {fim_str}")
            else:
                print(f"DEBUG[DAO]: Sem conflitos encontrados para a quadra {num_quadra} (Gin. {id_ginasio}) entre {inicio_str} e {fim_str}")

            return conflito_encontrado
            
        except Exception as e:
            print(f"Erro ao verificar conflito de horário: {e}")
            return True
        finally:
            cursor.close()
            conexao.close()
    '''
    
    # --- Metodos refatorados para o MongoDB ---
    def verificar_conflito_de_horario(self, id_ginasio, num_quadra, inicio, fim):
        """
        [MongoDB] Verifica se existe qualquer agendamento ou evento extraordinário
        que se sobrepõe a um dado intervalo de tempo para uma quadra específica.
        Retorna True se houver conflito, False caso contrário.
        """
        db = conectar_mongo()
        if db is None:
            return True # Assume conflito por segurança se não puder conectar

        try:
            # Filtro para encontrar conflitos em AGENDAMENTOS
            filtro_agendamento = {
                "id_ginasio": int(id_ginasio),
                "num_quadra": int(num_quadra),
                "status_agendamento": {"$ne": "cancelado"}, # Onde o status NÃO SEJA 'cancelado'
                # Lógica de sobreposição de horários do MongoDB:
                # Início do conflito < Fim do novo E Fim do conflito > Início do novo
                "hora_ini": {"$lt": fim},
                "hora_fim": {"$gt": inicio}
            }
            
            # Busca se existe pelo menos UM agendamento que bate com o filtro
            conflito_agendamento = db.agendamentos.find_one(filtro_agendamento)
            
            if conflito_agendamento:
                print(f"DEBUG[DAO-Mongo]: Conflito ENCONTRADO com um agendamento existente.")
                return True

            # Filtro para encontrar conflitos em EVENTOS EXTRAORDINÁRIOS
            filtro_evento = {
                "tipo": "extraordinario",
                "quadras_bloqueadas": {
                    "$elemMatch": {"id_ginasio": int(id_ginasio), "num_quadra": int(num_quadra)}
                },
                "data_hora_inicio": {"$lt": fim},
                "data_hora_fim": {"$gt": inicio}
            }
            
            # Busca se existe pelo menos UM evento que bate com o filtro
            conflito_evento = db.eventos.find_one(filtro_evento)

            if conflito_evento:
                print(f"DEBUG[DAO-Mongo]: Conflito ENCONTRADO com o evento extraordinário '{conflito_evento['nome']}'.")
                return True

            # Se não encontrou conflitos em nenhuma das coleções
            print(f"DEBUG[DAO-Mongo]: Sem conflitos de horário encontrados para a quadra {num_quadra}.")
            return False
            
        except Exception as e:
            print(f"Erro ao verificar conflito de horário no MongoDB: {e}")
            return True # Em caso de erro, assume conflito por segurança

    def buscar_todos_os_agendamentos(self):
        """
        [MongoDB] Busca todos os documentos da coleção 'agendamentos'.
        """
        db = conectar_mongo()
        if db is None:
            return []
        
        agendamentos = []
        try:
            # Busca todos os documentos e ordena pela hora de início (mais novos primeiro)
            resultados = db.agendamentos.find({}).sort("hora_ini", -1)
            
            # Precisamos renomear/formatar algumas chaves para compatibilidade com o template
            for doc in resultados:
                doc['id_agendamento'] = doc.pop('_id') # Renomeia _id para id_agendamento
                doc['nome_usuario'] = doc.get('usuario_info', {}).get('nome', 'N/A')
                doc['nome_ginasio'] = doc.get('local_info', {}).get('nome_ginasio', 'N/A')
                agendamentos.append(doc)

            print(f"DEBUG[DAO-Mongo]: {len(agendamentos)} agendamentos totais encontrados.")

        except Exception as e:
            print(f"Erro ao buscar todos os agendamentos no MongoDB: {e}")
            
        return agendamentos
    
    def buscar_agendamentos_por_quadra(self, id_ginasio, num_quadra, data_inicio, data_fim):
        """
        [MongoDB] Busca tanto AGENDAMENTOS quanto EVENTOS para uma quadra específica
        dentro de um intervalo de datas.
        """
        db = conectar_mongo()
        if db is None:
            return []
            
        ocupacoes = []
        try:
            # --- Busca Agendamentos ---
            filtro_agendamento = {
                "id_ginasio": int(id_ginasio),
                "num_quadra": int(num_quadra),
                "status_agendamento": {"$ne": "cancelado"},
                "hora_ini": {"$lt": data_fim}, # Começa antes do fim do intervalo
                "hora_fim": {"$gt": data_inicio} # Termina depois do início do intervalo
            }
            agendamentos = db.agendamentos.find(filtro_agendamento)
            
            for doc in agendamentos:
                doc['tipo_ocupacao'] = 'agendamento'
                doc['status'] = doc.get('status_agendamento')
                ocupacoes.append(doc)
            
            # --- Busca Eventos Extraordinários ---
            filtro_evento_extra = {
                "tipo": "extraordinario",
                "quadras_bloqueadas": {"$elemMatch": {"id_ginasio": int(id_ginasio), "num_quadra": int(num_quadra)}},
                "data_hora_inicio": {"$lt": data_fim},
                "data_hora_fim": {"$gt": data_inicio}
            }
            eventos_extra = db.eventos.find(filtro_evento_extra)
            
            for doc in eventos_extra:
                doc['tipo_ocupacao'] = 'evento'
                doc['status'] = 'bloqueado'
                doc['hora_ini'] = doc.get('data_hora_inicio')
                doc['hora_fim'] = doc.get('data_hora_fim')
                doc['nome_evento'] = doc.get('nome')
                ocupacoes.append(doc)

            # --- Busca Eventos Recorrentes (lógica permanece em Python na rota) ---
            # Adicionamos os recorrentes aqui para que a rota possa processá-los
            filtro_evento_rec = {
                "tipo": "recorrente",
                "quadras_bloqueadas": {"$elemMatch": {"id_ginasio": int(id_ginasio), "num_quadra": int(num_quadra)}},
                "data_fim_recorrencia": {"$gte": data_inicio}
            }
            eventos_rec = db.eventos.find(filtro_evento_rec)

            for doc in eventos_rec:
                 doc['tipo_ocupacao'] = 'evento'
                 doc['status'] = 'recorrente'
                 # A chave 'nome_evento' já existe como 'nome' no documento 'doc'.
                 # Vamos apenas garantir que ela seja chamada de 'nome_evento' para o template.
                 doc['nome_evento'] = doc.get('nome')
                 ocupacoes.append(doc)
                 
            print(f"DEBUG[DAO-Mongo]: Encontradas {len(ocupacoes)} ocupações (agendamentos + eventos).")
                
        except Exception as e:
            print(f"Erro ao buscar ocupações por quadra no MongoDB: {e}")
            
        return ocupacoes

    def admin_atualizar_status(self, id_agendamento, novo_status):
            """
            [MongoDB] Permite que um administrador altere o status de qualquer agendamento.
            Retorna True em caso de sucesso, False em caso de falha.
            """
            if novo_status not in ['confirmado', 'cancelado', 'realizado', 'nao_compareceu']:
                print(f"Erro: Status '{novo_status}' é inválido.")
                return False

            db = conectar_mongo()
            if db is None:
                return False
                
            sucesso = False
            try:
                # Converte a string do ID para um objeto ObjectId do MongoDB
                obj_id = ObjectId(id_agendamento)
                
                # Comando Mongo: db.<colecao>.update_one({filtro}, {operador_de_update})
                resultado = db.agendamentos.update_one(
                    {"_id": obj_id}, # Filtro para encontrar o agendamento pelo seu _id
                    {"$set": {"status_agendamento": novo_status}} # Define o novo status
                )
                
                if resultado.modified_count > 0:
                    sucesso = True
                    print(f"DEBUG[DAO-Mongo]: Status do agendamento ID {id_agendamento} atualizado para '{novo_status}'.")
                else:
                    print(f"DEBUG[DAO-Mongo]: Nenhum agendamento com ID {id_agendamento} foi encontrado para atualizar.")

            except Exception as e:
                print(f"Erro ao atualizar status do agendamento (admin) no MongoDB: {e}")
                
            return sucesso

    def buscar_agendamentos_por_usuario(self, cpf_usuario):
        """
        [MongoDB] Retorna todos os agendamentos realizados por um determinado usuário.
        """
        db = conectar_mongo()
        if db is None:
            return []
            
        agendamentos = []
        try:
            # Filtra a coleção 'agendamentos' pelo CPF do usuário
            filtro = {"cpf_usuario": cpf_usuario}
            resultados = db.agendamentos.find(filtro).sort("hora_ini", -1)
            
            # Formata os dados para compatibilidade com o template
            for doc in resultados:
                doc['id_agendamento'] = doc.pop('_id')
                doc['ginasio'] = doc.get('local_info', {}).get('nome_ginasio')
                doc['quadra'] = doc.get('num_quadra')
                # Adicione outras chaves que o seu template meus_agendamentos.html possa precisar
                agendamentos.append(doc)

        except Exception as e:
            print(f"Erro ao buscar agendamentos por usuário no MongoDB: {e}")

        return agendamentos


# --- Funções Auxiliares criadas pelo José ---
def get_ginasio_por_id(id_ginasio):  # --- Refatorada para o MongoDB
    """
    [MongoDB] Busca um único ginásio pelo seu _id.
    Retorna um objeto Ginasio para manter a compatibilidade.
    """
    db = conectar_mongo()
    if db is None:
        return None
        
    try:
        # Busca o documento na coleção 'ginasios' pelo _id (convertido para int)
        doc = db.ginasios.find_one({"_id": int(id_ginasio)})
        
        if doc:
            # Reconstrói o objeto Ginasio a partir do dicionário
            return Ginasio(
                id_ginasio=doc.get('_id'),
                nome=doc.get('nome'),
                endereco=doc.get('endereco'),
                capacidade=doc.get('capacidade')
            )
    except Exception as e:
        print(f"Erro ao buscar ginásio por ID no MongoDB: {e}")
        
    return None

def buscar_ginasios():  # --- Refatorada para o MongoDB
    """
    [MongoDB] Busca todos os ginásios na coleção 'ginasios'.
    Retorna uma lista de objetos Ginasio para manter a compatibilidade
    com o código existente.
    """
    db = conectar_mongo()
    if db is None:
        return []
        
    ginasios_obj = []
    try:
        # Busca todos os documentos na coleção e ordena por nome
        resultados = db.ginasios.find({}).sort("nome", 1)
        
        # Converte cada dicionário do Mongo em um objeto Ginasio
        for doc in resultados:
            ginasios_obj.append(
                Ginasio(
                    id_ginasio=doc.get('_id'),
                    nome=doc.get('nome'),
                    endereco=doc.get('endereco'),
                    capacidade=doc.get('capacidade')
                )
            )
        print(f"DEBUG[DAO-Mongo]: {len(ginasios_obj)} ginásios encontrados.")
    except Exception as e:
        print(f"Erro ao buscar ginásios no MongoDB: {e}")
        
    return ginasios_obj

def buscar_quadras_por_ginasio(id_ginasio):  # --- Refatorada para o MongoDB
    """
    [MongoDB] Busca as quadras embutidas de um ginásio específico.
    Retorna uma lista de objetos Quadra para manter a compatibilidade.
    """
    db = conectar_mongo()
    if db is None:
        return []

    quadras_obj = []
    try:
        # Busca o documento do ginásio e projeta apenas o campo 'quadras'
        ginasio_doc = db.ginasios.find_one(
            {"_id": int(id_ginasio)},
            {"quadras": 1, "_id": 0} 
        )
        
        if ginasio_doc and 'quadras' in ginasio_doc:
            # Para cada dicionário de quadra no array, cria um objeto Quadra
            for quadra_dict in ginasio_doc['quadras']:
                quadras_obj.append(
                    Quadra(
                        num_quadra=quadra_dict.get('num_quadra'),
                        capacidade=quadra_dict.get('capacidade')
                    )
                )
    except Exception as e:
        print(f"Erro ao buscar quadras por ginásio no MongoDB: {e}")
        
    return quadras_obj

def inserir_agendamento(cpf_usuario, id_ginasio, num_quadra, hora_ini, hora_fim):
    """
    Insere um novo agendamento na coleção MongoDB 'agendamentos'.
    O status inicial sempre será 'pendente'.
    """
    db = conectar_mongo()
    if db is None:
        return False

    try:
        novo = {
            "cpf_usuario": cpf_usuario,
            "id_ginasio": int(id_ginasio),
            "num_quadra": int(num_quadra),
            "hora_ini": hora_ini,
            "hora_fim": hora_fim,
            "status_agendamento": "pendente",
            "data_solicitacao": datetime.now()
        }

        result = db.agendamentos.insert_one(novo)
        print(f"DEBUG[Mongo]: Agendamento criado → ID = {result.inserted_id}")
        return True

    except Exception as e:
        print(f"Erro ao inserir agendamento no MongoDB: {e}")
        return False



def atualizar_status_agendamento(id_agendamento, novo_status):
    """
    Atualiza o status de um agendamento específico.
    """
    db = conectar_mongo()
    if db is None:
        return False

    try:
        result = db.agendamentos.update_one(
            {"_id": ObjectId(id_agendamento)},
            {"$set": {"status_agendamento": novo_status}}
        )

        print(f"DEBUG[Mongo]: Status atualizado? {result.modified_count > 0}")
        return result.modified_count > 0
    
    except Exception as e:
        print(f"Erro ao atualizar status no MongoDB: {e}")
        return False



def excluir_agendamento(id_agendamento):
    """
    Remove um agendamento da coleção.
    """
    db = conectar_mongo()
    if db is None:
        return False

    try:
        result = db.agendamentos.delete_one({"_id": ObjectId(id_agendamento)})
        print(f"DEBUG[Mongo]: Registros apagados = {result.deleted_count}")
        return result.deleted_count > 0
    
    except Exception as e:
        print("Erro ao excluir agendamento no Mongo:", e)
        return False



def buscar_agendamento_por_id(id_agendamento):
    """
    Busca um agendamento específico pelo _id no MongoDB.
    Retorna o documento completo ou None.
    """
    db = conectar_mongo()
    if db is None:
        return None

    try:
        ag = db.agendamentos.find_one({"_id": ObjectId(id_agendamento)})
        if ag:
            ag["id_agendamento"] = ag.pop("_id")  # mantém compatibilidade com o restante do sistema

        return ag

    except Exception as e:
        print(f"Erro ao localizar agendamento no MongoDB: {e}")
        return None
    
def verificar_disponibilidade(id_ginasio, num_quadra, data, hora_ini, hora_fim): # --- Refatorada para o MongoDB
    """
    [MongoDB] Verifica se a quadra está disponível no horário solicitado,
    considerando agendamentos e eventos extraordinários.
    """
    db = conectar_mongo()
    if db is None:
        return False # Se não conectar, não permite agendar por segurança

    try:
        # Converte as strings de data e hora para objetos datetime
        timestamp_ini = datetime.fromisoformat(f"{data}T{hora_ini}")
        timestamp_fim = datetime.fromisoformat(f"{data}T{hora_fim}")

        # Reutiliza o método já migrado da classe AgendamentoDAO
        dao = AgendamentoDAO()
        # O método já retorna True se houver conflito, então retornamos o inverso
        tem_conflito = dao.verificar_conflito_de_horario(id_ginasio, num_quadra, timestamp_ini, timestamp_fim)
        
        return not tem_conflito # Retorna True se NÃO houver conflito (está disponível)

    except Exception as e:
        print(f"Erro ao verificar disponibilidade no MongoDB: {e}")
        return False

def verificar_usuario_existe(cpf: str) -> bool:
    """
    Verifica se um usuário existe no sistema pelo CPF (que é o _id da coleção).
    Conversão direta da versão em PostgreSQL -> MongoDB.
    """
    db = conectar_mongo()
    if not db:
        return False

    try:
        usuario = db["usuarios"].find_one({"_id": cpf})  # CPF continua sendo a chave primária
        return usuario is not None

    except Exception as e:
        print(f"Erro ao verificar usuário no MongoDB: {e}")
        return False

def verificar_estrutura_tabela(sample_size: int = 100):
    """
    [MongoDB] Inspeção rápida da coleção 'agendamentos'.
    - Mostra contagem total
    - Mostra um documento de amostra
    - Varre até `sample_size` documentos e lista campos encontrados com tipos observados
    """
    db = conectar_mongo()
    if db is None:
        print("Falha ao conectar ao MongoDB.")
        return

    try:
        coll = db.agendamentos
        total = coll.count_documents({})
        print(f"TOTAL de documentos em 'agendamentos': {total}")

        # Documento de amostra
        amostra = coll.find_one()
        if amostra:
            print("\n--- Documento de amostra (primeiro encontrado) ---")
            for k, v in amostra.items():
                print(f"{k}: ({type(v).__name__}) -> {v}")
        else:
            print("\nColeção vazia — sem documento de amostra.")

        # Analisar tipos observados por campo em até `sample_size` documentos
        print(f"\nAnalisando até {sample_size} documentos para detectar campos e tipos...")
        tipos_por_campo = {}
        cursor = coll.find({}, limit=sample_size)
        for doc in cursor:
            for k, v in doc.items():
                tipos_por_campo.setdefault(k, set()).add(type(v).__name__)

        print("\n--- Campos detectados e tipos observados ---")
        for campo, tipos in sorted(tipos_por_campo.items()):
            tipos_list = ", ".join(sorted(tipos))
            print(f"{campo}: {tipos_list}")

    except Exception as e:
        print(f"Erro ao verificar estrutura da coleção 'agendamentos': {e}")


def verificar_estrutura_agendamento():
    """
    [MongoDB] Inspeção detalhada da coleção 'agendamentos':
    - chama verificar_estrutura_tabela para visão dos campos
    - exibe estatísticas da coleção (collStats)
    - exibe índices
    - exibe regras de validação (validator) se houver
    """
    db = conectar_mongo()
    if db is None:
        print("Falha ao conectar ao MongoDB.")
        return

    try:
        coll_name = "agendamentos"
        coll = db[coll_name]

        # 1) Informações básicas e campos/tipos (usa a função acima)
        print("=== INSPEÇÃO RÁPIDA (campos e tipos) ===")
        verificar_estrutura_tabela(sample_size=200)

        # 2) Estatísticas da coleção
        try:
            stats = db.command("collStats", coll_name)
            print("\n=== collStats (estatísticas da coleção) ===")
            print(f"size (bytes): {stats.get('size')}")
            print(f"count (docs): {stats.get('count')}")
            print(f"storageSize (bytes): {stats.get('storageSize')}")
            print(f"avgObjSize (bytes): {stats.get('avgObjSize')}")
        except Exception as e:
            print(f"Não foi possível obter collStats: {e}")

        # 3) Índices
        try:
            print("\n=== Índices da coleção ===")
            indexes = coll.index_information()
            for name, info in indexes.items():
                print(f"- {name}: keys={info.get('key')}, unique={info.get('unique', False)}")
        except Exception as e:
            print(f"Erro ao listar índices: {e}")

        # 4) Validação do esquema (validator) — ver se o collection info tem validator
        try:
            coll_info = db.command("listCollections", filter={"name": coll_name})
            collections = coll_info.get("cursor", {}).get("firstBatch", [])
            if collections:
                options = collections[0].get("options", {})
                validator = options.get("validator")
                validationLevel = options.get("validationLevel")
                validationAction = options.get("validationAction")
                if validator:
                    print("\n=== Regras de validação (validator) ===")
                    print(f"validationLevel: {validationLevel}, validationAction: {validationAction}")
                    print(validator)
                else:
                    print("\nNenhuma regra de validação (validator) definida para esta coleção.")
            else:
                print("\nColeção não encontrada ao checar validação.")
        except Exception as e:
            print(f"Erro ao verificar regras de validação: {e}")

    except Exception as e:
        print(f"Erro ao verificar estrutura completa de agendamento: {e}")


def criar_agendamento(cpf_usuario, id_ginasio, num_quadra, data, hora_ini, hora_fim, motivo_evento=None): # --- Refatorada para o MongoDB
    """
    [MongoDB] Cria um novo documento de agendamento na coleção 'agendamentos'.
    """
    db = conectar_mongo()
    if db is None:
        return False

    try:
        # Busca informações para embutir no documento
        usuario_info = db.usuarios.find_one({"_id": cpf_usuario}, {"nome": 1})
        ginasio_info = db.ginasios.find_one({"_id": int(id_ginasio)}, {"nome": 1})

        if not usuario_info or not ginasio_info:
            print("ERRO[DAO-Mongo]: Usuário ou Ginásio não encontrado para criar agendamento.")
            return False

        # Monta o documento de agendamento
        novo_agendamento = {
            "cpf_usuario": cpf_usuario,
            "id_ginasio": int(id_ginasio),
            "num_quadra": int(num_quadra),
            "data_solicitacao": datetime.now(),
            "hora_ini": datetime.fromisoformat(f"{data}T{hora_ini}"),
            "hora_fim": datetime.fromisoformat(f"{data}T{hora_fim}"),
            "status_agendamento": "confirmado",
            "usuario_info": {"nome": usuario_info.get('nome')},
            "local_info": {"nome_ginasio": ginasio_info.get('nome')}
        }

        if motivo_evento:
            novo_agendamento['motivo'] = f"Evento: {motivo_evento}"

        # Insere o novo documento na coleção
        resultado = db.agendamentos.insert_one(novo_agendamento)
        
        return resultado.inserted_id is not None

    except Exception as e:
        print(f"Erro ao criar agendamento no MongoDB: {e}")
        return False