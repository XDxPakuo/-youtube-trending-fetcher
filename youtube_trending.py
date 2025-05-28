import os
import datetime
import argparse # Added for command-line argument parsing
# import google_auth_oauthlib.flow # Potentially not needed for API key auth
import googleapiclient.discovery
import googleapiclient.errors
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
DEFAULT_REGION_CODE = "US"
HOURS_TO_FILTER = 12
MAX_RESULTS_TO_FETCH = 25

# --- Helper Functions ---
def get_youtube_service():
    """
    Builds and returns a YouTube API service object.

    Raises:
        ValueError: If the API key is not found.

    Returns:
        googleapiclient.discovery.Resource: YouTube API service object.
    """
    if not API_KEY:
        raise ValueError(
            "API key not found. Please set YOUTUBE_API_KEY in your .env file or environment."
        )
    return googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, developerKey=API_KEY
    )

def fetch_popular_videos(youtube, region_code=DEFAULT_REGION_CODE, max_results=MAX_RESULTS_TO_FETCH):
    """
    Fetches the most popular videos for a given region.

    Args:
        youtube: YouTube API service object.
        region_code (str): Region code for fetching videos (e.g., "US", "GB").
        max_results (int): Maximum number of videos to fetch.

    Returns:
        list: A list of video items, or an empty list if an error occurs.
    """
    try:
        request = youtube.videos().list(
            part="snippet,contentDetails,statistics",
            chart="mostPopular",
            regionCode=region_code,
            maxResults=max_results,
        )
        response = request.execute()
        return response.get("items", [])
    except googleapiclient.errors.HttpError as e:
        print(f"An API error occurred: {e}")
        return []

def filter_videos_by_time(videos, hours=None): # Allow hours to be passed, defaulting to global if None
    if hours is None:
        hours = HOURS_TO_FILTER # Use the global config if not specified

    filtered_videos = []
    # Ensure 'now' is timezone-aware (UTC)
    now = datetime.datetime.now(datetime.timezone.utc)
    time_threshold = now - datetime.timedelta(hours=hours)

    for video in videos:
        published_at_str = video.get("snippet", {}).get("publishedAt")
        if published_at_str:
            try:
                # Ensure 'Z' (Zulu time/UTC) is handled correctly for fromisoformat
                if published_at_str.endswith('Z'):
                    published_at_str = published_at_str[:-1] + '+00:00'
                
                published_at_dt = datetime.datetime.fromisoformat(published_at_str)

                # Ensure published_at_dt is timezone-aware (it should be if parsed from ISO with offset).
                # If it were naive, it would need localization:
                # if published_at_dt.tzinfo is None:
                #    published_at_dt = published_at_dt.replace(tzinfo=datetime.timezone.utc)
                # However, fromisoformat with +00:00 should make it aware.

                if published_at_dt >= time_threshold:
                    filtered_videos.append(video)
            except ValueError as e:
                # Log error for this specific video's date parsing
                print(f"Error parsing date string '{published_at_str}' for video ID '{video.get('id', 'N/A')}': {e}")
                # Optionally, skip this video or handle as per requirements
                continue 
    return filtered_videos

def display_videos(videos, count, display_hours, display_region): # Modified signature
    if not videos:
        print("No videos found matching the criteria.")
        return

    # Determine the actual number of videos to display
    num_to_display = min(len(videos), count)

    # Print header using passed-in parameters for context
    print(f"\nTop {num_to_display} YouTube Videos from the Last {display_hours} Hours (Region: {display_region}):")
    print("-" * 80)

    for i, video in enumerate(videos[:num_to_display]):
        title = video.get("snippet", {}).get("title", "No Title")
        video_id = video.get("id", "")
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        print(f"{i+1}. {title}")
        print(f"   Link: {video_url}\n") # Adding an extra newline for spacing

def main():
    """
    Main function to orchestrate fetching, filtering, and displaying YouTube videos.
    """
    parser = argparse.ArgumentParser(description="Fetch, filter, and display trending YouTube videos.")
    parser.add_argument(
        "-r", "--region",
        default=DEFAULT_REGION_CODE,
        help="YouTube region code (e.g., US, GB, JP)."
    )
    parser.add_argument(
        "-hr", "--hours",
        type=int,
        default=HOURS_TO_FILTER,
        help="How many hours back to filter videos (e.g., 12)."
    )
    parser.add_argument(
        "-f", "--fetch",
        type=int,
        default=MAX_RESULTS_TO_FETCH,
        help="Number of videos to initially fetch from the API."
    )
    parser.add_argument(
        "-c", "--count",
        type=int,
        default=5, # As per requirement, default 5 for count
        help="Number of top videos to display."
    )
    args = parser.parse_args()

    try:
        youtube_service = get_youtube_service()
    except ValueError as e:
        print(e)
        return

    if not youtube_service:
        print("Failed to get YouTube service. Exiting.")
        return

    videos = fetch_popular_videos(youtube_service, region_code=args.region, max_results=args.fetch)
    if not videos:
        print(f"No popular videos found for region {args.region}.")
        return

    filtered_videos = filter_videos_by_time(videos, hours=args.hours)
    if not filtered_videos:
        print(f"No videos found published in the last {args.hours} hours for region {args.region}.")
        return
        
    display_videos(filtered_videos, count=args.count, display_hours=args.hours, display_region=args.region)

if __name__ == "__main__":
    main()