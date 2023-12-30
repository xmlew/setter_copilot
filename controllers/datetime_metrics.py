import requests
from datetime import datetime

### Metrics covered in this file:
# Conversation Start Time
# Conversation End Time
# Total Messages Sent
# Conversation Length
# Average Response Time

### Possible improvements:
# Response Time Variability
# Most Active Times


# Returns a datetime object of now. This is configured to Airtable
# i.e. month/day/year hour:minute:am/pm. e.g. 5/23/2023 5:12am
def set_created_at():
  dt = datetime.now()
  return dt.strftime("%m/%d/%Y %I:%M%p").lower()


# Takes in the created_at (which will be from voiceflow) and compares the total
# difference in seconds.
def get_conversation_length(created_at_time):
  # Convert the string to a datetime object
  time_format = "%d/%m/%Y %I:%M%p"
  time_obj = datetime.strptime(created_at_time, time_format)

  # Get the current time
  now = datetime.now()

  # Calculate the difference
  diff = now - time_obj

  # Convert the difference to minutes, seconds, and total seconds
  total_seconds = int(diff.total_seconds())
  return total_seconds


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


def get_number_of_queries(name, vf_project_id, vf_api_key):
  transcript_id = get_transcript_id_by_os(vf_project_id, vf_api_key, name)
  result_info = {"successful": False, "count": 0}
  if not transcript_id:
    return result_info

  transcript_log = get_transcript_log(vf_project_id, vf_api_key, transcript_id)
  if not transcript_log:
    return result_info

  query_count = 0  # Counter for messages starting with 'query'
  for item in transcript_log:
    # Check for 'request' type and extract 'query'
    if item.get('type') == 'request' and item.get('payload') and item.get(
        'payload').get('payload') and item.get('payload').get('payload').get(
            'query'):
      query_count += 1  # Increment the counter

  # Return the number of 'query' messages along with the response
  result_info['successful'] = True
  result_info['count'] = query_count
  return result_info


def get_average_reply_time(created_at_time, name, vf_project_id, vf_api_key):
  result_info = get_number_of_queries(name, vf_project_id, vf_api_key)
  if result_info['successful']:
    query_count = result_info['count']
    if query_count > 0:
      total_seconds = get_conversation_length(created_at_time)
      average_reply_time = total_seconds / query_count - 60
      # Subtract 60 seconds to account for the time it takes for the agent to respond
      return average_reply_time
    else:
      return 0
