# camada_dados/chamado_dao.py

import psycopg2.extras
from .mongo_config import conectar_mongo

class ChamadoDAO:
    def buscar_todos(self):
        """
        Busca todos os chamados de manutenção abertos, juntando informações
        do usuário que abriu, do ginásio e da quadra.
        Retorna uma lista de dicionários.
        """
        conexao = conectar_mongo()
        if not conexao:
            return []
        
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.DictCursor)
        chamados = []
        try:
            query = """
                SELECT 
                    c.id_cha,
                    c.data,
                    c.descricao,
                    c.num_quadra,
                    g.nome as nome_ginasio,
                    u.nome as nome_usuario_abriu
                FROM 
                    chamado_manutencao c
                JOIN 
                    usuario u ON c.cpf_usuario_abriu = u.cpf
                JOIN 
                    ginasio g ON c.id_ginasio = g.id_ginasio
                ORDER BY
                    c.data DESC;
            """
            cursor.execute(query)
            resultados = cursor.fetchall()
            for linha in resultados:
                chamados.append(dict(linha))
            print(f"DEBUG[DAO]: {len(chamados)} chamados de manutenção encontrados.")
        except Exception as e:
            print(f"Erro ao buscar todos os chamados: {e}")
        finally:
            cursor.close()
            conexao.close()
        return chamados

    def excluir(self, id_chamado):
        """
        Exclui um chamado de manutenção do banco de dados, geralmente após
        ser resolvido.
        Retorna True em caso de sucesso, False em caso de falha.
        """
        conexao = conectar_mongo()
        if not conexao:
            return False
            
        cursor = conexao.cursor()
        sucesso = False
        try:
            query = "DELETE FROM chamado_manutencao WHERE id_cha = %s"
            cursor.execute(query, (id_chamado,))
            conexao.commit()
            if cursor.rowcount > 0:
                sucesso = True
                print(f"DEBUG[DAO]: Chamado ID {id_chamado} excluído com sucesso.")
        except Exception as e:
            conexao.rollback()
            print(f"Erro ao excluir chamado: {e}")
        finally:
            cursor.close()
            conexao.close()
        return sucesso