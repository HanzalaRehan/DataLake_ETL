# Embeddings & keywords
from sentence_transformers import SentenceTransformer
from keybert import KeyBERT

# Sentiment
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Device
device = (
    "mps" if torch.backends.mps.is_available()
    else "cpu"
)

# ---------- Embedding & Keyword Models ----------
EMBEDDING_MODEL_NAME = "all-mpnet-base-v2"
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=device)
kw_model = KeyBERT(model=embedding_model)

# ---------- Sentiment Model ----------
SENTIMENT_MODEL = "cardiffnlp/twitter-roberta-base-sentiment"
sent_tokenizer = AutoTokenizer.from_pretrained(SENTIMENT_MODEL)
sent_model = AutoModelForSequenceClassification.from_pretrained(SENTIMENT_MODEL)
sent_model.eval()

SENTIMENT_LABELS = ["Negative", "Neutral", "Positive"]