from dotenv import load_dotenv
import anthropic
from sentence_transformers import SentenceTransformer

load_dotenv()

model = SentenceTransformer("all-MiniLM-L6-v2")
print("Embedding dims:", len(model.encode("hello")))

client = anthropic.Anthropic()
msg = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=50,
    messages=[{"role": "user", "content": "Say hi in five words."}],
)
print(msg.content[0].text)