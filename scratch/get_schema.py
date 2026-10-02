import os
import requests
from dotenv import load_dotenv

load_dotenv()
pat = os.getenv('AIRTABLE_PAT')
base_id = os.getenv('AIRTABLE_BASE_ID')

url = f'https://api.airtable.com/v0/meta/bases/{base_id}/tables'
headers = {'Authorization': f'Bearer {pat}'}

response = requests.get(url, headers=headers)
if response.status_code == 200:
    for table in response.json().get('tables', []):
        if table['name'] == 'Returns & Refunds':
            for field in table['fields']:
                if field['name'] == 'Reason':
                    print('Found Reason field options:')
                    if 'options' in field:
                        for opt in field['options'].get('choices', []):
                            print(f"- {opt['name']}")
                    break
else:
    print(f'Failed: {response.status_code} - {response.text}')
