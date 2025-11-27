# camada_dados/material_dao.py

import psycopg2.extras
from .db_config import conectar_banco

class MaterialDAO:
    def buscar_todos(self):
        """
        Busca todos os materiais esportivos, juntando com o nome do ginásio.
        Retorna uma lista de dicionários.
        """
        conexao = conectar_banco()
        if not conexao:
            return []
        
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.DictCursor)
        materiais = []
        try:
            query = """
                SELECT 
                    m.id_material, m.nome, m.descricao, m.marca, m.status,
                    m.qnt_total, m.qnt_disponivel,
                    g.id_ginasio, g.nome as nome_ginasio
                FROM 
                    material_esportivo m
                JOIN 
                    ginasio g ON m.id_ginasio = g.id_ginasio
                ORDER BY
                    g.nome, m.nome;
            """
            cursor.execute(query)
            resultados = cursor.fetchall()
            for linha in resultados:
                materiais.append(dict(linha))
            print(f"DEBUG[DAO]: {len(materiais)} materiais encontrados.")
        except Exception as e:
            print(f"Erro ao buscar todos os materiais: {e}")
        finally:
            cursor.close()
            conexao.close()
        return materiais

    def criar(self, id_ginasio, nome, descricao, marca, status, qnt_total):
        """
        Insere um novo material esportivo no banco de dados.
        A quantidade disponível será igual à total na criação.
        Retorna True em caso de sucesso, False em caso de falha.
        """
        conexao = conectar_banco()
        if not conexao:
            return False
            
        cursor = conexao.cursor()
        sucesso = False
        try:
            query = """
                INSERT INTO material_esportivo 
                    (id_ginasio, nome, descricao, marca, status, qnt_total, qnt_disponivel)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            # qnt_disponivel é igual a qnt_total ao criar
            cursor.execute(query, (id_ginasio, nome, descricao, marca, status, qnt_total, qnt_total))
            conexao.commit()
            sucesso = True
            print(f"DEBUG[DAO]: Novo material '{nome}' criado com sucesso.")
        except Exception as e:
            conexao.rollback()
            print(f"Erro ao criar material: {e}")
        finally:
            cursor.close()
            conexao.close()
        return sucesso

    def atualizar(self, id_material, nome, descricao, marca, status, qnt_total, qnt_disponivel):
        """
        Atualiza os dados de um material esportivo existente.
        Retorna True em caso de sucesso, False em caso de falha.
        """
        conexao = conectar_banco()
        if not conexao:
            return False
            
        cursor = conexao.cursor()
        sucesso = False
        try:
            query = """
                UPDATE material_esportivo SET
                    nome = %s, descricao = %s, marca = %s, status = %s, 
                    qnt_total = %s, qnt_disponivel = %s
                WHERE id_material = %s
            """
            cursor.execute(query, (nome, descricao, marca, status, qnt_total, qnt_disponivel, id_material))
            conexao.commit()
            if cursor.rowcount > 0:
                sucesso = True
                print(f"DEBUG[DAO]: Material ID {id_material} atualizado.")
        except Exception as e:
            conexao.rollback()
            print(f"Erro ao atualizar material: {e}")
        finally:
            cursor.close()
            conexao.close()
        return sucesso

    def excluir(self, id_material):
        """
        Exclui um material esportivo do banco.
        Atenção: Pode falhar se o material estiver vinculado a um agendamento
        devido à configuração ON DELETE RESTRICT.
        Retorna True em caso de sucesso, False em caso de falha.
        """
        conexao = conectar_banco()
        if not conexao:
            return False
            
        cursor = conexao.cursor()
        sucesso = False
        try:
            query = "DELETE FROM material_esportivo WHERE id_material = %s"
            cursor.execute(query, (id_material,))
            conexao.commit()
            if cursor.rowcount > 0:
                sucesso = True
                print(f"DEBUG[DAO]: Material ID {id_material} excluído.")
        except Exception as e:
            conexao.rollback()
            print(f"Erro ao excluir material: {e}")
        finally:
            cursor.close()
            conexao.close()
        return sucesso
    
    # No camada_dados/material_dao.py - adicionar este método

    def buscar_por_ginasio(self, id_ginasio):
        """
        Busca todos os materiais disponíveis em um ginásio específico.
        Retorna apenas materiais com status 'bom' e quantidade disponível > 0.
        """
        conexao = conectar_banco()
        if not conexao:
            return []
            
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.DictCursor)
        materiais = []
        
        try:
            query = """
                SELECT id_material, nome, descricao, marca, status, 
                    qnt_total, qnt_disponivel
                FROM material_esportivo 
                WHERE id_ginasio = %s 
                AND status = 'bom' 
                AND qnt_disponivel > 0
                ORDER BY nome
            """
            cursor.execute(query, (id_ginasio,))
            resultados = cursor.fetchall()
            
            for linha in resultados:
                materiais.append(dict(linha))
                
        except Exception as e:
            print(f"Erro ao buscar materiais por ginásio: {e}")
        finally:
            cursor.close()
            conexao.close()
            
        return materiais
    
    def buscar_por_ginasio(self, id_ginasio):
        """
        Busca todos os materiais esportivos de um ginásio específico.
        Retorna uma lista de dicionários.
        """
        conexao = conectar_banco()
        if not conexao:
            return []
        
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.DictCursor)
        materiais = []
        try:
            query = """
                SELECT * FROM material_esportivo 
                WHERE id_ginasio = %s 
                ORDER BY nome;
            """
            cursor.execute(query, (id_ginasio,))
            for linha in cursor.fetchall():
                materiais.append(dict(linha))
        except Exception as e:
            print(f"Erro ao buscar materiais por ginásio: {e}")
        finally:
            cursor.close()
            conexao.close()
        return materiais
    
    def buscar_por_ginasio(self, id_ginasio):
        """
        Busca todos os materiais esportivos de um ginásio específico.
        Retorna uma lista de dicionários.
        """
        conexao = conectar_banco()
        if not conexao:
            return []
        
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.DictCursor)
        materiais = []
        try:
            query = """
                SELECT * FROM material_esportivo 
                WHERE id_ginasio = %s 
                ORDER BY nome;
            """
            cursor.execute(query, (id_ginasio,))
            for linha in cursor.fetchall():
                materiais.append(dict(linha))
        except Exception as e:
            print(f"Erro ao buscar materiais por ginásio: {e}")
        finally:
            cursor.close()
            conexao.close()
        return materiais