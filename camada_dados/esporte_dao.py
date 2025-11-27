# camada_dados/esporte_dao.py

import psycopg2.extras
from .db_config import conectar_banco

class EsporteDAO:
    def buscar_todos(self):
        """Busca todos os esportes, ordenados por nome."""
        conexao = conectar_banco()
        if not conexao: return []
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.DictCursor)
        esportes = []
        try:
            cursor.execute("SELECT id_esporte, nome, max_jogadores FROM esporte ORDER BY nome")
            for linha in cursor.fetchall():
                esportes.append(dict(linha))
        except Exception as e:
            print(f"Erro ao buscar esportes: {e}")
        finally:
            cursor.close()
            conexao.close()
        return esportes

    def buscar_por_id(self, id_esporte):
        """Busca um único esporte pelo seu ID."""
        conexao = conectar_banco()
        if not conexao: return None
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.DictCursor)
        esporte = None
        try:
            cursor.execute("SELECT id_esporte, nome, max_jogadores FROM esporte WHERE id_esporte = %s", (id_esporte,))
            resultado = cursor.fetchone()
            if resultado:
                esporte = dict(resultado)
        except Exception as e:
            print(f"Erro ao buscar esporte por ID: {e}")
        finally:
            cursor.close()
            conexao.close()
        return esporte

    def criar(self, nome, max_jogadores):
        """Insere um novo esporte no banco de dados."""
        conexao = conectar_banco()
        if not conexao: return None
        cursor = conexao.cursor()
        novo_id = None
        try:
            query = "INSERT INTO esporte (nome, max_jogadores) VALUES (%s, %s) RETURNING id_esporte"
            cursor.execute(query, (nome, max_jogadores))
            novo_id = cursor.fetchone()[0]
            conexao.commit()
        except Exception as e:
            conexao.rollback()
            print(f"Erro ao criar esporte: {e}")
        finally:
            cursor.close()
            conexao.close()
        return novo_id

    def atualizar(self, id_esporte, nome, max_jogadores):
        """Atualiza os dados de um esporte existente."""
        conexao = conectar_banco()
        if not conexao: return False
        cursor = conexao.cursor()
        sucesso = False
        try:
            query = "UPDATE esporte SET nome = %s, max_jogadores = %s WHERE id_esporte = %s"
            cursor.execute(query, (nome, max_jogadores, id_esporte))
            conexao.commit()
            if cursor.rowcount > 0:
                sucesso = True
        except Exception as e:
            conexao.rollback()
            print(f"Erro ao atualizar esporte: {e}")
        finally:
            cursor.close()
            conexao.close()
        return sucesso

    def excluir(self, id_esporte):
        """Exclui um esporte do banco de dados."""
        conexao = conectar_banco()
        if not conexao: return False
        cursor = conexao.cursor()
        sucesso = False
        try:
            query = "DELETE FROM esporte WHERE id_esporte = %s"
            cursor.execute(query, (id_esporte,))
            conexao.commit()
            if cursor.rowcount > 0:
                sucesso = True
        except Exception as e:
            conexao.rollback()
            print(f"Erro ao excluir esporte: {e}")
        finally:
            cursor.close()
            conexao.close()
        return sucesso