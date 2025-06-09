from modules.gpts import create_gpt_client
from modules.gpts.models import GPTRequest
from modules.gpts.config import GPTConfig


client = create_gpt_client(GPTConfig())

request = GPTRequest(
    prompt="你好，世界！",
)

response = client.complete(request)
print(response)
