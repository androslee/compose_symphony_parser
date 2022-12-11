import io
import typing

from . import logic, manual_testing

from revChatGPT.revChatGPT import Chatbot

# Credentials for: https://chat.openai.com/chat
config = {
  "email": "YOUR-EMAIL",
  "password": "YOUR-PASSWORD"
}

def main():
    path = 'inputs/tqqq_long_term.edn'
    root_node = manual_testing.get_root_node_from_path(path)
    print(output_strategy(root_node))


def output_strategy(text) -> str:
    # Initialize the Chatbot
    chatbot = Chatbot(config, conversation_id=None)
    # Generate the prompt to ask ChatGPT for the code
    prompt = f"""Could you convert the following trading logic into a C# QuantConnect strategy? When finished please say "THE END".

    ```
    {text}
    ```
    """

    # Wait on ChatGPT
    print('---------------------------------------------------------------')
    print('Asking ChatGPT for the QuantConnect strategy...')
    print('---------------------------------------------------------------')
    print('PROMPT: ')
    print(prompt)
    print('---------------------------------------------------------------')

    response = chatbot.get_chat_response(prompt, output="text")
    message = response['message']

    if 'THE END' in message:
        print('[*] Received "THE END", returning output.')
        return message
    else:
        while True:
            print('[*] Asking ChatGPT for more (code was truncated)...')
            more = chatbot.get_chat_response("continue", output="text")

            if 'THE END' in more['message']:
                print('[*] Received "THE END", concatinating output.')
                message += more['message']
                return message

            print('[*] Still waiting on ChatGPT...')
            message += more['message']
