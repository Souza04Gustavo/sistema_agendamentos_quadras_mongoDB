# camada_dados/chamado_dao.py

from .mongo_config import conectar_mongo
from bson import ObjectId

class ChamadoDAO:
    # --- metodos do MongoDB ---
    def buscar_todos(self):
        """
        [MongoDB] Busca todos os documentos da coleção 'chamados'.
        Os dados do usuário e local já estão embutidos (desnormalizados).
        """
        db = conectar_mongo()
        if db is None:
            return []
        
        chamados = []
        try:
            # Busca todos os documentos e ordena pela data de criação, da mais nova para a mais antiga
            resultados = db.chamados.find({}).sort("data", -1)
            chamados = list(resultados)
            print(f"DEBUG[DAO-Mongo]: {len(chamados)} chamados encontrados na coleção.")
        except Exception as e:
            print(f"Erro ao buscar todos os chamados no MongoDB: {e}")
            
        return chamados

    def excluir(self, id_chamado):
        """
        [MongoDB] Exclui um chamado da coleção 'chamados' pelo seu _id.
        """
        db = conectar_mongo()
        if db is None:
            return False
            
        sucesso = False
        try:
            # Converte a string do ID para um objeto ObjectId do MongoDB
            obj_id = ObjectId(id_chamado)
            
            # Comando Mongo: db.<colecao>.delete_one({filtro})
            resultado = db.chamados.delete_one({"_id": obj_id})
            
            if resultado.deleted_count > 0:
                sucesso = True
                print(f"DEBUG[DAO-Mongo]: Chamado ID {id_chamado} excluído com sucesso.")
            else:
                print(f"DEBUG[DAO-Mongo]: Nenhum chamado encontrado com o ID {id_chamado} para excluir.")

        except Exception as e:
            print(f"Erro ao excluir chamado no MongoDB: {e}")
            
        return sucesso