# camada_dados/material_dao.py

from .mongo_config import conectar_mongo
from bson import ObjectId

class MaterialDAO:

    # -- Metodos refatorados para o MongoDB --
        
    def buscar_todos(self):
        """
        [MongoDB] Busca todos os materiais de todos os ginásios.
        Desagrupa (unwind) os materiais embutidos para retornar uma lista plana.
        """
        db = conectar_mongo()
        if db is None:
            return []
        
        materiais = []
        try:
            # A 'agregação' é uma ferramenta poderosa do MongoDB.
            # $unwind: "desmonta" o array de materiais, criando um documento para cada material.
            # $project: formata o documento de saída.
            pipeline = [
                {"$unwind": "$materiais_esportivos"},
                {"$project": {
                    "_id": 0,
                    "id_material": "$materiais_esportivos.id_material",
                    "nome": "$materiais_esportivos.nome",
                    "descricao": "$materiais_esportivos.descricao",
                    "marca": "$materiais_esportivos.marca",
                    "status": "$materiais_esportivos.status",
                    "qnt_total": "$materiais_esportivos.qnt_total",
                    "qnt_disponivel": "$materiais_esportivos.qnt_disponivel",
                    "id_ginasio": "$_id",
                    "nome_ginasio": "$nome"
                }}
            ]
            resultados = db.ginasios.aggregate(pipeline)
            materiais = list(resultados)
            print(f"DEBUG[DAO-Mongo]: {len(materiais)} materiais encontrados em todos os ginásios.")
        except Exception as e:
            print(f"Erro ao buscar todos os materiais no MongoDB: {e}")
            
        return materiais

    def buscar_por_ginasio(self, id_ginasio):
        """
        [MongoDB] Busca todos os materiais esportivos de um ginásio específico.
        """
        db = conectar_mongo()
        if db is None:
            return []
            
        try:
            ginasio = db.ginasios.find_one({"_id": id_ginasio}, {"materiais_esportivos": 1})
            if ginasio and 'materiais_esportivos' in ginasio:
                return ginasio['materiais_esportivos']
        except Exception as e:
            print(f"Erro ao buscar materiais por ginásio no MongoDB: {e}")
            
        return []

    def criar(self, id_ginasio, nome, descricao, marca, status, qnt_total):
        db = conectar_mongo()
        if db is None: return False
            
        try:
            # --- CORREÇÃO 1: Validação e conversão do id_ginasio ---
            if not id_ginasio:
                print("ERRO[DAO-Mongo]: ID do Ginásio não foi fornecido para a criação.")
                return False
            id_ginasio_int = int(id_ginasio)
            # --- FIM CORREÇÃO ---

            qnt_total_int = int(qnt_total) if qnt_total else 0
            
            novo_material = {
                "id_material": str(ObjectId()),
                "nome": nome, "descricao": descricao, "marca": marca, "status": status,
                "qnt_total": qnt_total_int,
                "qnt_disponivel": qnt_total_int
            }
            print(f"DEBUG[DAO-Mongo]: Tentando INSERIR o seguinte material no ginásio ID {id_ginasio_int}: {novo_material}")
            
            resultado = db.ginasios.update_one(
                {"_id": id_ginasio_int},
                {"$push": {"materiais_esportivos": novo_material}}
            )
            
            print(f"DEBUG[DAO-Mongo]: Resultado da criação: Matched={resultado.matched_count}, Modified={resultado.modified_count}")
            return resultado.modified_count > 0
        except Exception as e:
            print(f"ERRO[DAO-Mongo] ao criar material: {e}")
            return False

    def atualizar(self, id_material, nome, descricao, marca, status, qnt_total, qnt_disponivel):
        db = conectar_mongo()
        if db is None: return False
            
        try:
            qnt_total_int = int(qnt_total) if qnt_total else 0
            qnt_disponivel_int = int(qnt_disponivel) if qnt_disponivel else 0
            
            print(f"DEBUG[DAO-Mongo]: Tentando ATUALIZAR material ID {id_material}")
            
            # --- CORREÇÃO 2: Conversão de tipo no filtro ---
            # Tenta encontrar o material tanto como string quanto como número para cobrir ambos os casos
            resultado = db.ginasios.update_one(
                {"$or": [
                    {"materiais_esportivos.id_material": id_material},
                    {"materiais_esportivos.id_material": int(id_material) if id_material.isdigit() else -1}
                ]},
                # --- FIM CORREÇÃO ---
                {"$set": {
                    "materiais_esportivos.$.nome": nome,
                    "materiais_esportivos.$.descricao": descricao,
                    "materiais_esportivos.$.marca": marca,
                    "materiais_esportivos.$.status": status,
                    "materiais_esportivos.$.qnt_total": qnt_total_int,
                    "materiais_esportivos.$.qnt_disponivel": qnt_disponivel_int
                }}
            )
            print(f"DEBUG[DAO-Mongo]: Resultado da atualização: Matched={resultado.matched_count}, Modified={resultado.modified_count}")
            return resultado.modified_count > 0
        except Exception as e:
            print(f"ERRO[DAO-Mongo] ao atualizar material: {e}")
            return False

    def excluir(self, id_material):
        db = conectar_mongo()
        if db is None: return False
            
        try:
            print(f"DEBUG[DAO-Mongo]: Tentando EXCLUIR material ID {id_material}")
            
            # --- CORREÇÃO 2: Conversão de tipo no filtro ---
            # Tenta remover o material tanto como string quanto como número
            resultado = db.ginasios.update_one(
                {}, 
                {"$pull": {"materiais_esportivos": {
                    "$or": [
                        {"id_material": id_material},
                        {"id_material": int(id_material) if id_material.isdigit() else -1}
                    ]
                }}}
            )
            # --- FIM CORREÇÃO ---
            print(f"DEBUG[DAO-Mongo]: Resultado da exclusão: Matched={resultado.matched_count}, Modified={resultado.modified_count}")
            return resultado.modified_count > 0
        except Exception as e:
            print(f"ERRO[DAO-Mongo] ao excluir material: {e}")
            return False
    
