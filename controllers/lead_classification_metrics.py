import json
import requests

# ###
# Interest Tags: analyse convo transcript to see what user is interested in, max 5
# Engagement Score: use openai to qualify based on a set of metrics (we can decide or just use openai to test)
# Conversation Tone: openai's analysis of the convo tone based on the transcript
# User Objections: any objections based on the transcript
# Lead Priority Rating: for sales team to classify, we can possibly classify rating based on engagement score and separate to high/mid/low prio
# ###

openai_api_key = os.getenv('OPENAI_API_KEY')

data = {
    "model":
    "gpt-3.5-turbo-1106",
    "messages": [{
        "role":
        "system",
        "content":
        "Summarize the key details of the conversation below:"
    }, {
        "role": "user",
        "content": conversation.strip()
    }]
}

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {openai_api_key}"
}
response = requests.post(
    "https://api.openai.com/v1/chat/completions",
    headers=headers,
    data=json.dumps(data)).json()["choices"][0]["message"]["content"]
