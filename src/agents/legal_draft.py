class LegalDraftingAgent:
    def __init__(self, pipe):
        self.drafting_pipeline = pipe

    def draft_document(self, instructions: str, context: str = ""):
        if not self.drafting_pipeline:
            return "Error: Text generation model not loaded."
        prompt = f"Context: {context}\n\nInstructions: {instructions}\n\nDraft:"
        try:
            draft = self.drafting_pipeline(prompt, max_length=1024, temperature=0.7, top_p=0.9)
            return draft[0]["generated_text"]
        except Exception as e:
            return f"Error generating draft: {str(e)}"

    def generate_clauses(self, instructions: str, clause_type: str):
        if not self.drafting_pipeline:
            return "Error: Text generation model not loaded."
        prompt = f"Draft a {clause_type} clause based on the following instructions:\n{instructions}\n\nClause:"
        try:
            clause = self.drafting_pipeline(prompt, max_length=4096, temperature=0.7, top_p=0.9)
            return clause[0]["generated_text"]
        except Exception as e:
            return f"Error generating clause: {str(e)}"

    def __call__(self, instructions: str, context: str = "", clause_type: str = None):
        if clause_type:
            return self.generate_clauses(instructions, clause_type)
        else:
            return self.draft_document(instructions, context)
