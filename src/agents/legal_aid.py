from sentence_transformers import SentenceTransformer
import os, faiss
import numpy as np

class LegalAidAgent:
    def __init__(self, pipe, knowledge_base_path="data/casedocs", embedding_dim=768, index_path="case_index.faiss"):
        self.knowledge_base_path = knowledge_base_path
        self.embedding_dim = embedding_dim
        self.index_path = index_path
        self.embedding_model = SentenceTransformer("all-mpnet-base-v2")
        self.qa_pipeline = pipe
        self.index = self._initialise_index()
        self.index_exist = False

        self.doc_metadata = []

    def _initialise_index(self):
        if os.path.exists(self.index_path):
            index = faiss.read_index(self.index_path)
            print(f"Loaded FAISS index from {self.index_path}")
            self.index_exist = True
        else:
            index = faiss.IndexFlatL2(self.embedding_dim)
            print("Initialized a new FAISS index")
        return index

    def build_index(self):
        # Ensure the knowledge base directory exists; if not, create it
        # so the system can still answer using the LLM even without documents.
        if not os.path.exists(self.knowledge_base_path):
            os.makedirs(self.knowledge_base_path, exist_ok=True)
            print(f"Created missing knowledge base directory at {self.knowledge_base_path}")

        for file_name in os.listdir(self.knowledge_base_path):
            file_path = os.path.join(self.knowledge_base_path, file_name)
            if not os.path.isfile(file_path):
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read()

                embedding = self.embedding_model.encode(content)
                self.index.add(np.array([embedding]))
                self.doc_metadata.append({"file_name": file_name, "content": content})
            except Exception as e:
                print(f"Error processing {file_name}: {e}")

        # Only persist the index if we actually added documents.
        if self.doc_metadata:
            faiss.write_index(self.index, self.index_path)
            print(f"FAISS index saved to {self.index_path}")
            self.index_exist = True

    def find_relevant_documents(self, query: str, top_k: int = 3):
        # If no documents were indexed, just return an empty list.
        if not self.doc_metadata or self.index.ntotal == 0:
            return []

        query_embedding = self.embedding_model.encode(query)
        distances, indices = self.index.search(np.array([query_embedding]), top_k)

        retrieved_docs = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(self.doc_metadata):
                doc_meta = self.doc_metadata[idx]
                retrieved_docs.append({"file_name": doc_meta["file_name"], "content": doc_meta["content"], "score": -distance})

        return retrieved_docs

    def provide_aid(self, query: str):
        if not self.qa_pipeline:
            return {"relevant_docs": [], "answer": "Error: Text generation model not loaded."}
        
        relevant_docs = self.find_relevant_documents(query)

        # If we have no documents, fall back to answering from the LLM alone.
        if not relevant_docs:
            prompt = f"You are a legal assistant. Answer the following question as best as you can based only on your general legal knowledge:\n\nQuestion: {query}"
        else:
            context = "\n\n".join([doc["content"] for doc in relevant_docs])
            prompt = f"Answer the following question using the context from the retrieved legal documents.\n\nQuestion: {query}\n\nContext:\n{context}"

        try:
            completion = self.qa_pipeline(prompt[:4096], max_length=4096, temperature=0.7, top_p=0.9)
            return {"relevant_docs": relevant_docs, "answer": completion[0]["generated_text"]}
        except Exception as e:
            return {"relevant_docs": relevant_docs, "answer": f"Error generating answer: {str(e)}"}

    def __call__(self, query: str):
        self.build_index()
        results = self.provide_aid(query)
        return results["answer"]
