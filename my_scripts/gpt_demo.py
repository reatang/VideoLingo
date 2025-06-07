from modules.gpt import create_gpt_client
from modules.gpt.models import GPTRequest
from modules.gpt.config import GPTConfig


client = create_gpt_client(GPTConfig())

request = GPTRequest(
    prompt="你好，世界！",
)

response = client.complete(request)
print(response)
