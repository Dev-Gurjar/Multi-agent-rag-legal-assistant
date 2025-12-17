from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
from functools import lru_cache
import os

from .agents.case_discovery import CaseDiscoveryAgent
from .agents.legal_aid import LegalAidAgent
from .agents.legal_draft import LegalDraftingAgent
from .query_decompose.decompose import Decomposer


@lru_cache(maxsize=1)
def _load_generation_pipeline():
    """
    Load and cache the text-generation pipeline.

    The base model can be configured via the GEN_MODEL_ID environment variable.
    By default it uses 'TinyLlama/TinyLlama-1.1B-Chat-v1.0' for faster loading.
    """
    import torch
    
    model_id = os.getenv("GEN_MODEL_ID", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")

    try:
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            device_map="cpu",
            torch_dtype=torch.float32,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )

        tokenizer = AutoTokenizer.from_pretrained(model_id)

        return pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            device=-1,  # CPU
        )
    except Exception as e:
        print(f"Error loading model {model_id}: {e}")
        raise


class Assistant:
    def __init__(self, pipe=None):
        # Lazily load the generation pipeline so we only create it once,
        # which is important for deployment on limited free tiers.
        self.pipe = pipe or _load_generation_pipeline()
        self.case_discovery_agent = CaseDiscoveryAgent(self.pipe)
        self.legal_aid_agent = LegalAidAgent(self.pipe)
        self.legal_drafting_agent = LegalDraftingAgent(self.pipe)
        self.decomposer = Decomposer()

        self.task_alloc = {
            "case discovery": self.case_discovery_agent,
            "document summarization": self.case_discovery_agent,
            "legal drafting": self.legal_drafting_agent,
            "query resolution": self.legal_aid_agent
        }

    def _find_intent(self, text_query: str = None, attachment: str = None):
        intent = self.decomposer(text_query, attachment)
        
        return intent
    
    def __call__(self, text_query: str = None, attachment: str = None):
        intent = self._find_intent(text_query, attachment)
        
        # Handle errors from decomposer
        if 'error' in intent:
            return f"Error processing input: {intent['error']}"
        
        if 'sub_queries' not in intent or not intent['sub_queries']:
            return "No valid queries could be extracted from the input."
        
        subqueries = intent['sub_queries']

        results = []

        for subquery in subqueries:
            try:
                task = subquery.get('task')
                if task not in self.task_alloc:
                    results.append(f"Unknown task: {task}")
                    continue
                results.append(self.task_alloc[task](subquery['text']))
            except Exception as e:
                results.append(f"Error processing subquery '{subquery.get('text', '')}': {str(e)}")

        return "".join(results)
    