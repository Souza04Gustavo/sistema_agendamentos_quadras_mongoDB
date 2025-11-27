# camada_dados/quadra_dao.py

import psycopg2.extras
from .mongo_config import conectar_mongo

class QuadraDAO:
    def buscar_todas_as_quadras(self):
        """
        Busca todas as quadras e junta com as informações do ginásio correspondente.
        Retorna uma lista de dicionários, um para cada quadra.
        """
        conexao = conectar_mongo()
        if not conexao:
            return []
        
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.DictCursor)
        quadras = []
        try:
            query = """
                SELECT 
                    q.id_ginasio, 
                    g.nome as nome_ginasio,
                    q.num_quadra,
                    q.tipo_piso,
                    q.cobertura,
                    q.status
                FROM 
                    quadra q
                JOIN 
                    ginasio g ON q.id_ginasio = g.id_ginasio
                ORDER BY
                    g.nome, q.num_quadra;
            """
            cursor.execute(query)
            resultados = cursor.fetchall()
            for linha in resultados:
                quadras.append(dict(linha))
            print(f"DEBUG[DAO]: {len(quadras)} quadras encontradas.")
        except Exception as e:
            print(f"Erro ao buscar todas as quadras: {e}")
        finally:
            cursor.close()
            conexao.close()
        return quadras

    def atualizar_status_quadra(self, id_ginasio, num_quadra, novo_status):
        """
        Atualiza o status de uma quadra específica.
        Retorna True em caso de sucesso, False em caso de falha.
        """
        if novo_status not in ['disponivel', 'manutencao', 'interditada']:
            print(f"Erro: Status '{novo_status}' é inválido.")
            return False
            
        conexao = conectar_mongo()
        if not conexao:
            return False
            
        cursor = conexao.cursor()
        sucesso = False
        try:
            query = "UPDATE quadra SET status = %s WHERE id_ginasio = %s AND num_quadra = %s"
            cursor.execute(query, (novo_status, id_ginasio, num_quadra))
            conexao.commit()
            if cursor.rowcount > 0:
                print(f"DEBUG[DAO]: Status da quadra {num_quadra} (Ginásio {id_ginasio}) atualizado.")
                sucesso = True
        except Exception as e:
            conexao.rollback()
            print(f"Erro ao atualizar status da quadra: {e}")
        finally:
            cursor.close()
            conexao.close()
        return sucesso

    def excluir_quadra(self, id_ginasio, num_quadra):
        """
        Exclui uma quadra do banco de dados.
        Atenção: Esta ação é destrutiva e pode apagar agendamentos relacionados
        devido à configuração ON DELETE CASCADE.
        Retorna True em caso de sucesso, False em caso de falha.
        """
        conexao = conectar_mongo()
        if not conexao:
            return False
            
        cursor = conexao.cursor()
        sucesso = False
        try:
            query = "DELETE FROM quadra WHERE id_ginasio = %s AND num_quadra = %s"
            cursor.execute(query, (id_ginasio, num_quadra))
            conexao.commit()
            if cursor.rowcount > 0:
                print(f"DEBUG[DAO]: Quadra {num_quadra} (Ginásio {id_ginasio}) excluída com sucesso.")
                sucesso = True
            else:
                print(f"DEBUG[DAO]: Nenhuma quadra encontrada para exclusão com os IDs fornecidos.")
        except Exception as e:
            conexao.rollback()
            print(f"Erro ao excluir a quadra: {e}")
        finally:
            cursor.close()
            conexao.close()
        return sucesso
    
    
    def criar_quadra(self, id_ginasio, num_quadra, capacidade, tipo_piso, cobertura):
        """
        Insere uma nova quadra no banco de dados.
        Retorna True em caso de sucesso, False em caso de falha.
        """
        conexao = conectar_mongo()
        if not conexao:
            return False
            
        cursor = conexao.cursor()
        sucesso = False
        try:
            # O status padrão ao criar sempre será 'disponivel'
            query = """
                INSERT INTO quadra (id_ginasio, num_quadra, capacidade, tipo_piso, cobertura, status)
                VALUES (%s, %s, %s, %s, %s, 'disponivel')
            """
            # O valor de 'cobertura' vem como 'on' do checkbox, convertemos para booleano
            cobertura_bool = True if cobertura else False
            
            cursor.execute(query, (id_ginasio, num_quadra, capacidade, tipo_piso, cobertura_bool))
            conexao.commit()
            sucesso = True
            print(f"DEBUG[DAO]: Nova quadra {num_quadra} criada no ginásio {id_ginasio}.")
        except Exception as e:
            conexao.rollback()
            print(f"Erro ao criar a quadra: {e}")
        finally:
            cursor.close()
            conexao.close()
        return sucesso
    
    def buscar_esportes_da_quadra(self, id_ginasio, num_quadra):
        """
        Busca todos os IDs de esportes associados a uma quadra específica.
        Retorna uma lista de IDs.
        """
        conexao = conectar_mongo()
        if not conexao: return []
        cursor = conexao.cursor()
        ids_esportes = []
        try:
            query = "SELECT id_esporte FROM quadra_esporte WHERE id_ginasio = %s AND num_quadra = %s"
            cursor.execute(query, (id_ginasio, num_quadra))
            # fetchall() retorna uma lista de tuplas, ex: [(1,), (3,)]. Precisamos extrair o primeiro item de cada tupla.
            resultados = cursor.fetchall()
            ids_esportes = [item[0] for item in resultados]
        except Exception as e:
            print(f"Erro ao buscar esportes da quadra: {e}")
        finally:
            cursor.close()
            conexao.close()
        return ids_esportes

    def atualizar_esportes_da_quadra(self, id_ginasio, num_quadra, lista_ids_esportes):
        """
        Atualiza a lista de esportes de uma quadra.
        Esta operação é transacional: primeiro apaga todas as associações antigas
        e depois insere as novas.
        """
        conexao = conectar_mongo()
        if not conexao: return False
        cursor = conexao.cursor()
        try:
            # 1. Apaga todas as associações existentes para esta quadra
            cursor.execute("DELETE FROM quadra_esporte WHERE id_ginasio = %s AND num_quadra = %s", (id_ginasio, num_quadra))

            # 2. Se a nova lista não estiver vazia, insere as novas associações
            if lista_ids_esportes:
                # Prepara os dados para uma inserção em massa (mais eficiente)
                dados_para_inserir = [(id_ginasio, num_quadra, id_esporte) for id_esporte in lista_ids_esportes]
                query_insert = "INSERT INTO quadra_esporte (id_ginasio, num_quadra, id_esporte) VALUES (%s, %s, %s)"
                # psycopg2 pode executar a mesma query para uma lista de tuplas
                cursor.executemany(query_insert, dados_para_inserir)
            
            conexao.commit()
            print(f"DEBUG[DAO]: Associações de esportes para a quadra {num_quadra} (Gin. {id_ginasio}) atualizadas.")
            return True
        except Exception as e:
            conexao.rollback()
            print(f"Erro ao atualizar esportes da quadra: {e}")
            return False
        finally:
            cursor.close()
            conexao.close()
            
            
        