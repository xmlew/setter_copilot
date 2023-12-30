from datetime import datetime
from flask import Flask, request, jsonify
from replit import db
import requests
import json
import os


app = Flask(__name__)

# Test Endpoint to make sure app is working
@app.route("/", methods=["GET"])
def home_page():
  return jsonify({"message": "Hello"})


@app.route("/test_data", methods=["POST"])
def test_data():
  return jsonify(str(request.json.get("data")))


# Data Preprocessing Step
# Updates Voiceflow Variable for Name, to be inserted into Airtable.
@app.route("/update_voiceflow/", methods=["POST"])
def update_voiceflow():
  # Extract necessary information from the incoming JSON request
  full_name = request.json.get("full_name")
  user_id = request.json.get("user_id")

  # Construct the Voiceflow API URL
  voiceflow_api_url = f"https://general-runtime.voiceflow.com/state/user/{user_id}/variables"

  # Set up the headers, including the API key
  headers = {
      "accept": "application/json",
      "content-type": "application/json",
      "Authorization": os.getenv('ISAIAH_VF_API_KEY')
  }

  # Prepare the data payload
  data = {"variables": {"userFullName": full_name}}

  # Send a PATCH request to the Voiceflow API
  response = requests.patch(voiceflow_api_url, json=data, headers=headers)

  # Handle the response
  if response.status_code == 200:
    return jsonify({"message": "Variable updated successfully"})
  else:
    return jsonify(response.json()), response.status_code


def get_transcript_id_by_os(vf_project_id, vf_api_key, os_name):
  url = f"https://api.voiceflow.com/v2/transcripts/{vf_project_id}"
  headers = {'Authorization': vf_api_key, 'accept': 'application/json'}

  try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    transcripts = response.json()

    for transcript in transcripts:
      if transcript["os"] == os_name:
        return transcript["_id"]
  except requests.RequestException as e:
    print(e)
    return None


def get_transcript_log(vf_project_id, vf_api_key, transcript_id):
  url = f"https://api.voiceflow.com/v2/transcripts/{vf_project_id}/{transcript_id}"
  headers = {'Authorization': vf_api_key, 'accept': 'application/json'}

  try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()
  except requests.RequestException as e:
    print(e)
    return []


def fetch_and_update_transcript_data(name, vf_project_id, vf_api_key):
  openai_api_key = os.getenv('OPENAI_API_KEY')

  transcript_id = get_transcript_id_by_os(vf_project_id, vf_api_key, name)
  if not transcript_id:
    return jsonify({"error":
                    "No transcript found for the given OS name."}), 404

  transcript_log = get_transcript_log(vf_project_id, vf_api_key, transcript_id)
  if not transcript_log:
    return jsonify({"error": "Failed to fetch transcript log."}), 500

  conversation = ""
  for item in transcript_log:
    # Check for 'text' type and extract 'message'
    if item.get('type') == 'text' and item.get('payload') and item.get(
        'payload').get('payload') and item.get('payload').get('payload').get(
            'message'):
      conversation += "Agent: " + item.get('payload').get('payload').get(
          'message') + "\n"
    # Check for 'request' type and extract 'query'
    elif item.get('type') == 'request' and item.get('payload') and item.get(
        'payload').get('payload') and item.get('payload').get('payload').get(
            'query'):
      conversation += "User: " + item.get('payload').get('payload').get(
          'query') + "\n"

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

  return response


# Step to update Airtable from Voiceflow using the name as the primary key and an object as the rest of the columns.
@app.route("/update_airtable/", methods=["POST"])
def update_airtable():
  name = request.json.get("name")
  data = request.json.get("data")
  airtable_token_name = str(request.json.get("airtable_token_id"))
  airtable_project_name = str(request.json.get("airtable_project_id"))
  voiceflow_project_name = str(request.json.get("voiceflow_project_name"))
  voiceflow_api_key_name = str(request.json.get("voiceflow_api_key_name"))
  base_name = str(request.json.get("base_name"))
  airtable_token_id = os.getenv(airtable_token_name)
  airtable_project_id = os.getenv(airtable_project_name)
  voiceflow_project_id = os.getenv(voiceflow_project_name)
  voiceflow_api_key = os.getenv(voiceflow_api_key_name)

  # Airtable API URL and headers
  airtable_api_url = f"https://api.airtable.com/v0/{airtable_project_id}/{base_name}"
  headers = {
      "Authorization": f"Bearer {airtable_token_id}",
      "Content-Type": "application/json"
  }

  # Prepare the data payload according to the documentation
  data["User Full Name"] = name
  if base_name == "UserConversionData":
    transcript_data = fetch_and_update_transcript_data(name,
                                                       voiceflow_project_id,
                                                       voiceflow_api_key)
    data["Chat Summary"] = "Summary"
  payload = {"records": [{"fields": data}]}

  # Send a POST request to the Airtable API
  response = requests.post(airtable_api_url, json=payload, headers=headers)

  # Handle the response
  if response.status_code in [200, 210]:
    return jsonify({
        "message": "Record updated successfully",
        "updated_record": response.json()
    }), response.status_code
  else:
    return jsonify({
        "message": "Record failed",
        "updated_record": response.json()
    }), response.status_code


@app.route("/update_queue", methods=["POST"])
def update_message_queue():
  userId = request.json.get("userId")
  message = request.json.get("message")
  keys = db.keys()

  if userId in keys:
    current_message = db[userId]["message"]
    current_message += " " + message
    db[userId][
        "message"] = current_message  # Update the message in the database
  else:
    db[userId] = {"message": message, "timestamp": datetime.now().isoformat()}
    current_message = message

  if (datetime.now() -
      datetime.fromisoformat(db[userId]["timestamp"])).total_seconds() > 60:
    del db[userId]
    return jsonify({"personalizedMessage": current_message}), 200
  else:
    return jsonify({"personalizedMessage": "oneMinuteTimer"}), 200


if __name__ == "__main__":
  app.run(host="0.0.0.0", debug=True)
