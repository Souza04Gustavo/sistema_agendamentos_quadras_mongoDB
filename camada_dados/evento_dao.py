# camada_dados/evento_dao.py

import psycopg2.extras
from .db_config import conectar_banco

class EventoDAO:
    def buscar_todos(self):
        """
        Busca todos os eventos (Extraordinários e Recorrentes) e suas informações.
        """
        conexao = conectar_banco()
        if not conexao: return []
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.DictCursor)
        eventos = []
        try:
            # Query corrigida com LEFT JOIN e COALESCE
            query = """
                SELECT 
                    e.id_evento, 
                    e.nome, 
                    e.descricao,
                    u.nome as nome_admin,
                    -- Determina o tipo do evento para exibição
                    CASE 
                        WHEN ex.id_evento IS NOT NULL THEN 'Extraordinário'
                        WHEN r.id_evento IS NOT NULL THEN 'Recorrente'
                        ELSE 'Desconhecido'
                    END as tipo_evento,
                    -- Usa COALESCE para unificar as informações de tempo
                    COALESCE(ex.data_hora_inicio, r.data_fim_recorrencia) as data_principal,
                    COALESCE(ex.data_hora_fim::text, r.regra_recorrencia) as detalhe_tempo
                FROM 
                    evento e
                LEFT JOIN 
                    extraordinario ex ON e.id_evento = ex.id_evento
                LEFT JOIN 
                    recorrente r ON e.id_evento = r.id_evento
                JOIN 
                    usuario u ON e.cpf_admin_organizador = u.cpf
                ORDER BY 
                    data_principal DESC;
            """
            cursor.execute(query)
            for linha in cursor.fetchall():
                eventos.append(dict(linha))
        except Exception as e:
            print(f"Erro ao buscar todos os eventos: {e}")
        finally:
            cursor.close()
            conexao.close()
        return eventos

    def criar(self, cpf_admin_organizador, nome_evento, desc_evento, tipo_evento, dados_tempo, lista_quadras_ids):
        """
        Cria um evento completo (Extraordinário ou Recorrente) usando uma transação.
        'dados_tempo' é um dicionário contendo os campos de tempo específicos.
        """
        conexao = conectar_banco()
        if not conexao: return False
        cursor = conexao.cursor()
        try:
            # 1. Inserir no evento principal
            query_evento = "INSERT INTO evento (cpf_admin_organizador, nome, descricao) VALUES (%s, %s, %s) RETURNING id_evento"
            cursor.execute(query_evento, (cpf_admin_organizador, nome_evento, desc_evento))
            id_novo_evento = cursor.fetchone()[0]

            # 2. Inserir na tabela de especialização correta
            if tipo_evento == 'extraordinario':
                query_especializacao = "INSERT INTO extraordinario (id_evento, data_hora_inicio, data_hora_fim) VALUES (%s, %s, %s)"
                cursor.execute(query_especializacao, (id_novo_evento, dados_tempo['inicio'], dados_tempo['fim']))
            elif tipo_evento == 'recorrente':
                query_especializacao = "INSERT INTO recorrente (id_evento, regra_recorrencia, data_fim_recorrencia) VALUES (%s, %s, %s)"
                cursor.execute(query_especializacao, (id_novo_evento, dados_tempo['regra'], dados_tempo['data_fim']))
            else:
                raise ValueError("Tipo de evento inválido")

            # 3. Inserir na tabela de junção 'evento_quadra'
            if lista_quadras_ids:
                dados_para_inserir = [(id_novo_evento, id_gin, num_q) for id_gin, num_q in lista_quadras_ids]
                query_evento_quadra = "INSERT INTO evento_quadra (id_evento, id_ginasio, num_quadra) VALUES (%s, %s, %s)"
                cursor.executemany(query_evento_quadra, dados_para_inserir)

            conexao.commit()
            print(f"DEBUG[DAO]: Evento '{nome_evento}' (tipo: {tipo_evento}) criado com ID {id_novo_evento}.")
            return True
        except Exception as e:
            conexao.rollback()
            print(f"Erro ao criar evento (transação falhou): {e}")
            return False
        finally:
            cursor.close()
            conexao.close()

    def excluir(self, id_evento):
        """
        Exclui um evento. Graças ao ON DELETE CASCADE, os registros em
        'extraordinario' and 'evento_quadra' serão apagados automaticamente.
        """
        conexao = conectar_banco()
        if not conexao: return False
        cursor = conexao.cursor()
        sucesso = False
        try:
            query = "DELETE FROM evento WHERE id_evento = %s"
            cursor.execute(query, (id_evento,))
            conexao.commit()
            if cursor.rowcount > 0:
                sucesso = True
        except Exception as e:
            conexao.rollback()
            print(f"Erro ao excluir evento: {e}")
        finally:
            cursor.close()
            conexao.close()
        return sucesso
    
    
    def quadra_pertence_a_evento(self, id_evento, id_ginasio, num_quadra):
        """
        Verifica se uma quadra específica está associada a um evento.
        Retorna True se a associação existir, False caso contrário.
        """
        conexao = conectar_banco()
        if not conexao:
            return False # Por segurança, se não conectar, não podemos confirmar
            
        cursor = conexao.cursor()
        try:
            query = """
                SELECT 1 FROM evento_quadra 
                WHERE id_evento = %s AND id_ginasio = %s AND num_quadra = %s
                LIMIT 1;
            """
            cursor.execute(query, (id_evento, id_ginasio, num_quadra))
            
            # Se fetchone() retornar algo, a linha existe.
            return cursor.fetchone() is not None
            
        except Exception as e:
            print(f"Erro ao verificar se quadra pertence a evento: {e}")
            return False
        finally:
            cursor.close()
            conexao.close()
            
    def buscar_recorrentes_por_quadra(self, id_ginasio, num_quadra):
        """
        Busca todos os eventos recorrentes associados a uma quadra específica.
        """
        conexao = conectar_banco()
        if not conexao: return []
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.DictCursor)
        recorrentes = []
        try:
            query = """
                SELECT r.regra_recorrencia
                FROM evento_quadra eq
                JOIN recorrente r ON eq.id_evento = r.id_evento
                WHERE eq.id_ginasio = %s AND eq.num_quadra = %s;
            """
            cursor.execute(query, (id_ginasio, num_quadra))
            for linha in cursor.fetchall():
                recorrentes.append(dict(linha))
        except Exception as e:
            print(f"Erro ao buscar eventos recorrentes por quadra: {e}")
        finally:
            cursor.close()
            conexao.close()
        return recorrentes