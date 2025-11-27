# camada_dados/ginasio_dao.py

import psycopg2.extras
from .mongo_config import conectar_mongo

class GinasioDAO:
    def buscar_por_id(self, id_ginasio):
        """
        Busca um único ginásio pelo seu ID.
        Retorna um dicionário se encontrado, None caso contrário.
        """
        conexao = conectar_mongo()
        if not conexao:
            return None
            
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.DictCursor)
        ginasio = None
        try:
            query = "SELECT id_ginasio, nome, endereco, capacidade FROM ginasio WHERE id_ginasio = %s"
            cursor.execute(query, (id_ginasio,))
            resultado = cursor.fetchone()
            if resultado:
                ginasio = dict(resultado)
        except Exception as e:
            print(f"Erro ao buscar ginásio por ID: {e}")
        finally:
            cursor.close()
            conexao.close()
        return ginasio

    def criar(self, nome, endereco, capacidade):
        """
        Insere um novo ginásio no banco de dados.
        Retorna o ID do novo ginásio em caso de sucesso, None caso contrário.
        """
        conexao = conectar_mongo()
        if not conexao:
            return None
            
        cursor = conexao.cursor()
        novo_id = None
        try:
            # Usamos RETURNING id_ginasio para obter o ID do registro recém-criado
            query = "INSERT INTO ginasio (nome, endereco, capacidade) VALUES (%s, %s, %s) RETURNING id_ginasio"
            cursor.execute(query, (nome, endereco, capacidade))
            novo_id = cursor.fetchone()[0]
            conexao.commit()
            print(f"DEBUG[DAO]: Novo ginásio '{nome}' criado com ID {novo_id}.")
        except Exception as e:
            conexao.rollback()
            print(f"Erro ao criar ginásio: {e}")
        finally:
            cursor.close()
            conexao.close()
        return novo_id

    def atualizar(self, id_ginasio, nome, endereco, capacidade):
        """
        Atualiza os dados de um ginásio existente.
        Retorna True em caso de sucesso, False em caso de falha.
        """
        conexao = conectar_mongo()
        if not conexao:
            return False
        
        cursor = conexao.cursor()
        sucesso = False
        try:
            query = "UPDATE ginasio SET nome = %s, endereco = %s, capacidade = %s WHERE id_ginasio = %s"
            cursor.execute(query, (nome, endereco, capacidade, id_ginasio))
            conexao.commit()
            if cursor.rowcount > 0:
                sucesso = True
                print(f"DEBUG[DAO]: Ginásio ID {id_ginasio} atualizado.")
        except Exception as e:
            conexao.rollback()
            print(f"Erro ao atualizar ginásio: {e}")
        finally:
            cursor.close()
            conexao.close()
        return sucesso

    def excluir(self, id_ginasio):
        """
        Exclui um ginásio do banco de dados.
        Atenção: A configuração ON DELETE CASCADE pode apagar dados relacionados.
        Retorna True em caso de sucesso, False em caso de falha.
        """
        conexao = conectar_mongo()
        if not conexao:
            return False
            
        cursor = conexao.cursor()
        sucesso = False
        try:
            query = "DELETE FROM ginasio WHERE id_ginasio = %s"
            cursor.execute(query, (id_ginasio,))
            conexao.commit()
            if cursor.rowcount > 0:
                sucesso = True
                print(f"DEBUG[DAO]: Ginásio ID {id_ginasio} excluído.")
        except Exception as e:
            conexao.rollback()
            print(f"Erro ao excluir ginásio: {e}")
        finally:
            cursor.close()
            conexao.close()
        return sucesso
    
    # --- Metodos migrados para o MongoDB ---
    
    def buscar_todos(self):
        """
        [MongoDB] Busca todos os ginásios na coleção 'ginasios'.
        """
        db = conectar_mongo()
        if db is None:
            return []
        
        ginasios = []
        try:
            # Busca todos os documentos na coleção e ordena por nome
            resultados = db.ginasios.find({}).sort("nome", 1)
            ginasios = list(resultados)
        except Exception as e:
            print(f"Erro ao buscar todos os ginásios no MongoDB: {e}")
            
        return ginasios
    
    