from camada_dados.mongo_config import conectar_mongo
import psycopg2.extras
from bson import ObjectId
from modelos.ginasio import Ginasio
from modelos.quadra import Quadra

class AgendamentoDAO:
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



# ==========================================================
#  BUSCAR AGENDAMENTOS POR USUÁRIO
# ==========================================================
def buscar_agendamentos_por_usuario(cpf_aluno):
    """
    Retorna todos os agendamentos realizados por um determinado aluno.
    """
    conexao = conectar_mongo()
    cursor = conexao.cursor()

    query = """
        SELECT a.id_agendamento, a.data_solicitacao, a.hora_ini, a.hora_fim, a.status_agendamento,
               a.num_quadra, g.nome AS nome_ginasio
        FROM agendamento a
        JOIN ginasio g ON a.id_ginasio = g.id_ginasio
        WHERE a.cpf_usuario = %s
        ORDER BY a.data_solicitacao DESC, a.hora_ini;
    """

    cursor.execute(query, (cpf_aluno,))
    resultados = cursor.fetchall()
    cursor.close()
    conexao.close()

    agendamentos = []
    for row in resultados:
        agendamentos.append({
            'id': row[0],
            'data': row[1],
            'hora_inicio': row[2],
            'hora_fim': row[3],
            'status_agendamento': row[4],
            'quadra': row[5],
            'ginasio': row[6]
        })

    return agendamentos

# ------------------- BUSCAR UM GINÁSIO POR ID -------------------
def get_ginasio_por_id(id_ginasio):
    conexao = conectar_mongo()
    if conexao is None:
        return None
    cursor = conexao.cursor()
    query = "SELECT id_ginasio, nome, endereco, capacidade FROM ginasio WHERE id_ginasio = %s"
    cursor.execute(query, (id_ginasio,))
    row = cursor.fetchone()
    cursor.close()
    conexao.close()
    if row:
        # Retorna um objeto Ginasio, não um dicionário
        return Ginasio(id_ginasio=row[0], nome=row[1], endereco=row[2], capacidade=row[3])
    return None

# ==========================================================
#  BUSCAR GINÁSIOS
# ==========================================================
def buscar_ginasios():
    conexao = conectar_mongo()
    if conexao is None:
        return []
    cursor = conexao.cursor()
    query = "SELECT id_ginasio, nome, endereco, capacidade FROM ginasio ORDER BY nome"
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    conexao.close()
    # Retorna lista de objetos Ginasio
    ginasios = [Ginasio(id_ginasio=row[0], nome=row[1], endereco=row[2], capacidade=row[3]) for row in rows]
    return ginasios


# ==========================================================
#  BUSCAR QUADRAS DE UM GINÁSIO
# ==========================================================

def buscar_quadras_por_ginasio(id_ginasio):
    conexao = conectar_mongo()
    if conexao is None:
        return []
    cursor = conexao.cursor()
    query = "SELECT num_quadra, capacidade FROM quadra WHERE id_ginasio = %s ORDER BY num_quadra"
    cursor.execute(query, (id_ginasio,))
    rows = cursor.fetchall()
    cursor.close()
    conexao.close()

    # Transformar cada linha em objeto Quadra
    quadras = [Quadra(num_quadra=row[0], capacidade=row[1]) for row in rows]
    return quadras

# ==========================================================
#  BUSCAR AGENDAMENTOS DE UMA QUADRA
# ==========================================================
def buscar_agendamentos_por_quadra(id_ginasio, num_quadra, data):
    """
    Busca agendamentos para uma quadra específica em uma data.
    """
    conexao = conectar_mongo()
    if not conexao:
        return []
        
    cursor = conexao.cursor(cursor_factory=psycopg2.extras.DictCursor)
    agendamentos = []
    try:
        query = """
            SELECT * 
            FROM agendamento
            WHERE id_ginasio = %s AND num_quadra = %s 
            AND DATE(hora_ini) = %s
            AND status_agendamento != 'cancelado'
            ORDER BY hora_ini
        """
        cursor.execute(query, (id_ginasio, num_quadra, data))
        resultados = cursor.fetchall()
        for row in resultados:
            agendamentos.append(dict(row))
    except Exception as e:
        print(f"Erro ao buscar agendamentos por quadra: {e}")
    finally:
        cursor.close()
        conexao.close()
    return agendamentos

# ==========================================================
#  INSERIR NOVO AGENDAMENTO
# ==========================================================
def inserir_agendamento(usuario_id, quadra_id, data, hora_inicio, hora_fim):
    """
    Insere um novo agendamento no banco de dados.
    O status inicial será 'pendente'.
    """
    conexao = conectar_mongo()
    cursor = conexao.cursor()

    query = """
        INSERT INTO agendamento (usuario_id, quadra_id, data, hora_inicio, hora_fim, status)
        VALUES (%s, %s, %s, %s, %s, 'pendente');
    """
    cursor.execute(query, (usuario_id, quadra_id, data, hora_inicio, hora_fim))
    conexao.commit()

    cursor.close()
    conexao.close()
    return True


# ==========================================================
#  ATUALIZAR STATUS DE AGENDAMENTO
# ==========================================================

def atualizar_status_agendamento(agendamento_id, novo_status):
    """
    Atualiza o status de um agendamento (por exemplo, confirmado, cancelado, rejeitado).
    CORREÇÃO: usando id_agendamento em vez de id
    """
    conexao = conectar_mongo()
    if not conexao:
        print("DEBUG: Falha na conexão com o banco")
        return False
        
    cursor = conexao.cursor()
    try:
        # CORREÇÃO: usar id_agendamento em vez de id
        query = "UPDATE agendamento SET status_agendamento = %s WHERE id_agendamento = %s;"
        cursor.execute(query, (novo_status, agendamento_id))
        conexao.commit()
        
        print(f"DEBUG: Status do agendamento {agendamento_id} atualizado para '{novo_status}'")
        print(f"DEBUG: Linhas afetadas: {cursor.rowcount}")
        
        return cursor.rowcount > 0
        
    except Exception as e:
        print(f"ERRO ao atualizar status do agendamento: {e}")
        conexao.rollback()
        return False
    finally:
        cursor.close()
        conexao.close()


# ==========================================================
#  EXCLUIR AGENDAMENTO
# ==========================================================
def excluir_agendamento(agendamento_id):
    """
    Exclui um agendamento do banco.
    """
    conexao = conectar_mongo()
    cursor = conexao.cursor()

    query = "DELETE FROM agendamento WHERE id = %s;"
    cursor.execute(query, (agendamento_id,))
    conexao.commit()

    cursor.close()
    conexao.close()
    return True

# ==========================================================
#  BUSCAR AGENDAMENTO POR ID
# ==========================================================
# No agendamento_dao.py - verificar se já está correto

def buscar_agendamento_por_id(id_agendamento):
    """
    Busca um agendamento específico pelo ID.
    Retorna um dicionário com os dados do agendamento ou None se não encontrado.
    """
    conexao = conectar_mongo()
    if not conexao:
        return None
        
    cursor = conexao.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        query = """
            SELECT 
                a.id_agendamento,  # ← Já está correto aqui
                a.cpf_usuario,
                a.id_ginasio,
                a.num_quadra,
                a.data_solicitacao,
                a.hora_ini,
                a.hora_fim,
                a.status_agendamento,
                u.nome AS nome_usuario,
                g.nome AS nome_ginasio
            FROM 
                agendamento a
            JOIN 
                usuario u ON a.cpf_usuario = u.cpf
            JOIN 
                ginasio g ON a.id_ginasio = g.id_ginasio
            WHERE 
                a.id_agendamento = %s  # ← Já está correto aqui
        """
        cursor.execute(query, (id_agendamento,))
        resultado = cursor.fetchone()
        
        if resultado:
            agendamento = dict(resultado)
            print(f"DEBUG: Agendamento ID {id_agendamento} encontrado")
            return agendamento
        else:
            print(f"DEBUG: Agendamento ID {id_agendamento} não encontrado")
            return None
            
    except Exception as e:
        print(f"Erro ao buscar agendamento por ID: {e}")
        return None
    finally:
        cursor.close()
        conexao.close()

# Adicione estas funções ao agendamento_dao.py

def verificar_disponibilidade(id_ginasio, num_quadra, data, hora_ini, hora_fim):
    """
    Verifica se a quadra está disponível no horário solicitado.
    """
    conexao = conectar_mongo()
    if not conexao:
        return False
        
    cursor = conexao.cursor()
    try:
        # Converter para timestamp completo
        timestamp_ini = f"{data} {hora_ini}:00"
        timestamp_fim = f"{data} {hora_fim}:00"
        
        query = """
            SELECT COUNT(*) FROM agendamento 
            WHERE id_ginasio = %s 
            AND num_quadra = %s 
            AND status_agendamento != 'cancelado'
            AND (
                (hora_ini < %s AND hora_fim > %s) OR
                (hora_ini < %s AND hora_fim > %s) OR
                (hora_ini >= %s AND hora_fim <= %s)
            )
        """
        cursor.execute(query, (
            id_ginasio, num_quadra,
            timestamp_fim, timestamp_ini,
            timestamp_ini, timestamp_fim,
            timestamp_ini, timestamp_fim
        ))
        conflitos = cursor.fetchone()[0]
        print(f"DEBUG: Conflitos de horário encontrados: {conflitos}")
        
        return conflitos == 0
        
    except Exception as e:
        print(f"Erro ao verificar disponibilidade: {e}")
        return False
    finally:
        cursor.close()
        conexao.close()

def verificar_disponibilidade(id_ginasio, num_quadra, data, hora_ini, hora_fim):
    """
    Verifica se a quadra está disponível no horário solicitado.
    """
    conexao = conectar_mongo()
    if not conexao:
        return False
        
    cursor = conexao.cursor()
    try:
        # Converter para timestamp completo
        timestamp_ini = f"{data} {hora_ini}:00"
        timestamp_fim = f"{data} {hora_fim}:00"
        
        query = """
            SELECT COUNT(*) FROM agendamento 
            WHERE id_ginasio = %s 
            AND num_quadra = %s 
            AND status_agendamento != 'cancelado'
            AND (
                (hora_ini < %s AND hora_fim > %s) OR
                (hora_ini < %s AND hora_fim > %s)
            )
        """
        cursor.execute(query, (
            id_ginasio, num_quadra,
            timestamp_fim, timestamp_ini,  # hora_ini < timestamp_fim AND hora_fim > timestamp_ini
            timestamp_ini, timestamp_fim   # hora_ini < timestamp_ini AND hora_fim > timestamp_fim
        ))
        conflitos = cursor.fetchone()[0]
        
        print(f"DEBUG: Conflitos encontrados: {conflitos}")
        return conflitos == 0
        
    except Exception as e:
        print(f"Erro ao verificar disponibilidade: {e}")
        return False
    finally:
        cursor.close()
        conexao.close()

def verificar_usuario_existe(cpf):
    """
    Verifica se um usuário existe no sistema.
    """
    conexao = conectar_mongo()
    if not conexao:
        return False
        
    cursor = conexao.cursor()
    try:
        query = "SELECT COUNT(*) FROM usuario WHERE cpf = %s"
        cursor.execute(query, (cpf,))
        count = cursor.fetchone()[0]
        return count > 0
    except Exception as e:
        print(f"Erro ao verificar usuário: {e}")
        return False
    finally:
        cursor.close()
        conexao.close()

def verificar_estrutura_tabela():
    """
    Verifica a estrutura da tabela agendamento
    """
    conexao = conectar_mongo()
    if not conexao:
        return
        
    cursor = conexao.cursor()
    try:
        query = """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'agendamento'
            ORDER BY ordinal_position;
        """
        cursor.execute(query)
        colunas = cursor.fetchall()
        print("=== ESTRUTURA DA TABELA AGENDAMENTO ===")
        for coluna in colunas:
            print(f"Coluna: {coluna[0]}, Tipo: {coluna[1]}, Nulo: {coluna[2]}")
    except Exception as e:
        print(f"Erro ao verificar estrutura: {e}")
    finally:
        cursor.close()
        conexao.close()
# Adicionar esta função no agendamento_dao.py para verificar a estrutura

def verificar_estrutura_agendamento():
    """
    Verifica a estrutura completa da tabela agendamento
    """
    conexao = conectar_mongo()
    if not conexao:
        return
        
    cursor = conexao.cursor()
    try:
        query = """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'agendamento'
            ORDER BY ordinal_position;
        """
        cursor.execute(query)
        colunas = cursor.fetchall()
        print("=== ESTRUTURA COMPLETA DA TABELA AGENDAMENTO ===")
        for coluna in colunas:
            print(f"Coluna: {coluna[0]}, Tipo: {coluna[1]}, Nulo: {coluna[2]}, Default: {coluna[3]}")
    except Exception as e:
        print(f"Erro ao verificar estrutura: {e}")
    finally:
        cursor.close()
        conexao.close()

def criar_agendamento(cpf_usuario, id_ginasio, num_quadra, data, hora_ini, hora_fim, motivo_evento=None):
    """
    Cria um novo agendamento no banco de dados.
    Se motivo_evento for fornecido, é um agendamento de evento.
    """
    conexao = conectar_mongo()
    if not conexao:
        print("DEBUG: Falha na conexão com o banco")
        return False
        
    cursor = conexao.cursor()
    try:
        # Converter para timestamp completo
        timestamp_ini = f"{data} {hora_ini}:00"
        timestamp_fim = f"{data} {hora_fim}:00"
        
        print(f"DEBUG - Timestamps: INI={timestamp_ini}, FIM={timestamp_fim}")
        
        if motivo_evento:
            # Agendamento de evento - usar status confirmado e incluir motivo
            query = """
                INSERT INTO agendamento 
                (cpf_usuario, id_ginasio, num_quadra, data_solicitacao, hora_ini, hora_fim, status_agendamento, motivo)
                VALUES (%s, %s, %s, CURRENT_DATE, %s, %s, 'confirmado', %s)
            """
            cursor.execute(query, (cpf_usuario, id_ginasio, num_quadra, timestamp_ini, timestamp_fim, f"Evento: {motivo_evento}"))
        else:
            # Agendamento normal
            query = """
                INSERT INTO agendamento 
                (cpf_usuario, id_ginasio, num_quadra, data_solicitacao, hora_ini, hora_fim, status_agendamento)
                VALUES (%s, %s, %s, CURRENT_DATE, %s, %s, 'confirmado')
            """
            cursor.execute(query, (cpf_usuario, id_ginasio, num_quadra, timestamp_ini, timestamp_fim))
        
        conexao.commit()
        
        print(f"DEBUG: Agendamento inserido - Linhas afetadas: {cursor.rowcount}")
        
        if cursor.rowcount > 0:
            print("DEBUG: Agendamento criado com SUCESSO no banco")
            return True
        else:
            print("DEBUG: Nenhuma linha afetada - agendamento NÃO criado")
            return False
            
    except Exception as e:
        print(f"DEBUG: Erro ao criar agendamento: {e}")
        conexao.rollback()
        return False
    finally:
        cursor.close()
        conexao.close()
        
