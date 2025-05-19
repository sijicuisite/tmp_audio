import requests
import json
import time
import os
import uuid
from urllib.parse import urljoin
from github import Github
import base64

class VolcengineASR:
    def __init__(self, appid, token, cluster, github_token=None, github_repo=None):
        self.appid = appid
        self.token = token
        self.cluster = cluster
        self.service_url = 'https://openspeech.bytedance.com/api/v1/auc'
        self.headers = {'Authorization': f'Bearer; {token}'}
        self.github_token = github_token
        self.github_repo = github_repo

    def submit_task(self, audio_path):
        audio_url = self._get_audio_url(audio_path)

        request = {
            "app": {
                "appid": self.appid,
                "token": self.token,
                "cluster": self.cluster
            },
            "user": {
                "uid": str(uuid.uuid4())
            },
            "audio": {
                "format": "mp4",
                "url": audio_url
            },
            "additions": {
                'with_speaker_info': 'False',
            }
        }

        response = requests.post(
            urljoin(self.service_url, '/submit'),
            data=json.dumps(request),
            headers=self.headers
        )
        resp_dict = json.loads(response.text)
        return resp_dict['resp']['id']

    def query_task(self, task_id):
        query_dict = {
            'appid': self.appid,
            'token': self.token,
            'id': task_id,
            'cluster': self.cluster
        }
        response = requests.post(
            urljoin(self.service_url, '/query'),
            data=json.dumps(query_dict),
            headers=self.headers
        )
        return json.loads(response.text)

    def _get_audio_url(self, audio_path):
        if not self.github_token or not self.github_repo:
            raise ValueError("GitHub token and repository name are required for file upload")
        
        # Initialize GitHub client
        g = Github(self.github_token)
        repo = g.get_repo(self.github_repo)
        
        # Read file content
        with open(audio_path, 'rb') as file:
            content = file.read()
        
        # Get filename from path
        filename = os.path.basename(audio_path)
        
        # Upload file to GitHub
        try:
            # Try to get the file first to check if it exists
            repo.get_contents(filename)
            # If file exists, update it
            contents = repo.get_contents(filename)
            repo.update_file(
                path=filename,
                message=f"Update {filename}",
                content=content,
                sha=contents.sha
            )
        except:
            # If file doesn't exist, create it
            repo.create_file(
                path=filename,
                message=f"Add {filename}",
                content=content
            )
        
        # Get raw file URL
        raw_url = f"https://raw.githubusercontent.com/{self.github_repo}/main/{filename}"
        return raw_url

    def process_audio(self, audio_path, max_wait_time=300):
        task_id = self.submit_task(audio_path)
        start_time = time.time()
        
        while True:
            time.sleep(2)  # Wait 2 seconds between queries
            resp_dict = self.query_task(task_id)
            
            if resp_dict['resp']['code'] == 1000:  # Task finished successfully
                return self._process_results(resp_dict)
            elif resp_dict['resp']['code'] < 2000:  # Task failed
                raise Exception(f"ASR task failed with code: {resp_dict['resp']['code']}")
            
            if time.time() - start_time > max_wait_time:
                raise Exception("ASR task timed out")

    def _process_results(self, resp_dict):
        results = []
        for utterance in resp_dict['resp']['utterances']:
            for word in utterance['words']:
                results.append({
                    'text': word['text'],
                    'start_time': word['start_time'],
                    'end_time': word['end_time']
                })
        return results

def main():
    # Replace these with your actual credentials
    appid = ''
    token = ''
    cluster = ''
    
    # GitHub credentials
    github_token = os.getenv('GITHUB_TOKEN')
    github_repo = 'sijicuisite/tmp_audio'  # Format: username/repository
    
    # Initialize the ASR client with GitHub credentials
    asr_client = VolcengineASR(appid, token, cluster, github_token, github_repo)
    
    # Path to your MP4 file
    audio_path = './clips/bribe/便会把安比怀受贿一事一笔勾销.mp4'
    
    # Process the audio file
    results = asr_client.process_audio(audio_path)
    
    # Print results
    print("\nASR Results:")
    print("=" * 50)
    for word in results:
        print(f"Word: {word['text']}")
        print(f"Start Time: {word['start_time']}ms")
        print(f"End Time: {word['end_time']}ms")
        print("-" * 30)

if __name__ == '__main__':
    main()
