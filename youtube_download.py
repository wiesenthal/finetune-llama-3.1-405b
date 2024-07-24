import os
import re
from dotenv import load_dotenv
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from datetime import timedelta

# Load environment variables
load_dotenv()

# Get API key from environment variable
API_KEY = os.getenv('YOUTUBE_API_KEY')

def get_channel_id(youtube, channel_name):
    request = youtube.search().list(
        q=channel_name,
        type='channel',
        part='id',
        maxResults=1
    )
    response = request.execute()
    
    if 'items' in response and len(response['items']) > 0:
        return response['items'][0]['id']['channelId']
    else:
        return None

def get_video_ids(youtube, channel_id, max_results=10):
    video_ids = []
    next_page_token = None

    while len(video_ids) < max_results:
        request = youtube.search().list(
            channelId=channel_id,
            type='video',
            part='id,snippet',
            order='date',
            maxResults=50,  # Request maximum allowed per page
            pageToken=next_page_token
        )
        response = request.execute()
        
        for item in response['items']:
            video_duration = get_video_duration(youtube, item['id']['videoId'])
            if video_duration >= 120:  # Filter videos that are 2+ minutes
                video_ids.append({
                    'id': item['id']['videoId'],
                    'title': item['snippet']['title']
                })
                if len(video_ids) == max_results:
                    break

        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break  # No more videos to fetch

    return video_ids[:max_results]  # Ensure we don't return more than requested

def get_video_duration(youtube, video_id):
    try:
        request = youtube.videos().list(
            part='contentDetails',
            id=video_id
        )
        response = request.execute()
        
        if 'items' in response and len(response['items']) > 0:
            duration = response['items'][0]['contentDetails']['duration']
            return parse_duration(duration)
        else:
            print(f"No content details found for video {video_id}")
            return 0
    except Exception as e:
        print(f"Error getting duration for video {video_id}: {str(e)}")
        return 0

def parse_duration(duration):
    # Use regex to extract hours, minutes, and seconds
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return 0  # Return 0 if the format is not recognized

    hours, minutes, seconds = match.groups()
    
    total_seconds = 0
    if hours:
        total_seconds += int(hours) * 3600
    if minutes:
        total_seconds += int(minutes) * 60
    if seconds:
        total_seconds += int(seconds)

    return total_seconds

def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return ' '.join([entry['text'] for entry in transcript])
    except Exception as e:
        print(f"Error getting transcript for video {video_id}: {str(e)}")
        return None

def main():
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    
    channel_name = input("Enter the YouTube channel name: ")
    num_videos = int(input("Enter the number of videos to process: "))
    output_folder = input("Enter the output folder name: ")
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    channel_id = get_channel_id(youtube, channel_name)
    if not channel_id:
        print("Channel not found.")
        return
    
    video_ids = get_video_ids(youtube, channel_id, num_videos)
    
    for video in video_ids:
        transcript = get_transcript(video['id'])
        if transcript:
            file_name = f"{video['title']}.txt".replace('/', '_')  # Replace '/' with '_' to avoid file path issues
            with open(os.path.join(output_folder, file_name), 'w', encoding='utf-8') as f:
                f.write(transcript)
            print(f"Transcript saved for video: {video['title']}")
        else:
            print(f"No transcript available for video: {video['title']}")

if __name__ == "__main__":
    main()
