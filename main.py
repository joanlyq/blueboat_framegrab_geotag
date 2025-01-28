import cv2
import os
import pandas as pd
from datetime import datetime
from tqdm import tqdm
import exiftool

def get_video_start_time(filename):
    """ Extract the timestamp from the video filename. """
    timestamp_str = filename.split('_')[1]  # assuming structure DJI_YYYYMMDDHHMMSS_XXXX_XXX.MP4
    return datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')

def get_timestamp_from_video(video_dir):
    """ Get timestamp from the video filename. """
    filename = os.path.basename(video_dir)
    return get_video_start_time(filename)

def find_closest_timestamp(gps_df, target_unix_ts):
    """ Find the closest timestamp in the GPS dataframe using Unix timestamps. """
    gps_df['timestamp'] = pd.to_datetime(gps_df['unix_ts'], unit='s')  # Convert unix_ts to datetime
    gps_df['time_diff'] = (gps_df['timestamp'].astype('int64') / 10**9 - target_unix_ts).abs()
    
    # Find the closest timestamp
    closest_row = gps_df.loc[gps_df['time_diff'].idxmin()]
    
    # Check if the depth at the closest timestamp is greater than 5m
    if closest_row['depth'] > 5:
        # Find the next closest point with depth <= 5m for estimating depth
        gps_df_valid = gps_df[gps_df['depth'] <= 5]
        if not gps_df_valid.empty:
            closest_depth_row = gps_df_valid.loc[gps_df_valid['time_diff'].idxmin()]
            estimated_depth = closest_depth_row['depth']
        else:
            estimated_depth = closest_row['depth']
    else:
        estimated_depth = closest_row['depth']
    
    return closest_row, estimated_depth

def write_geotag(image_path, lat, lon, altitude):
    """ Write latitude, longitude, and altitude into the image's EXIF metadata. """
    with exiftool.ExifToolHelper() as et:
        et.execute(
            f"-GPSLatitude={lat}",
            f"-GPSLatitudeRef={'N' if lat >= 0 else 'S'}",
            f"-GPSLongitude={lon}",
            f"-GPSLongitudeRef={'E' if lon >= 0 else 'W'}",
            f"-GPSAltitude={altitude}",
            f"-overwrite_original", 
            image_path
        )

def process_frame(frame, video_start_time, gps_df, fps, frame_count, video_name, output_folder, i):
    """Process a single frame (grab frame and geotag)."""
    timestamp = video_start_time + pd.to_timedelta(frame_count / fps, unit='s')
    # Convert frame timestamp to Unix timestamp with 2 decimal places
    frame_unix_ts = round(timestamp.timestamp(), 2)
    
    timestamp_str = timestamp.strftime('%Y%m%d%H%M%S')

    # Create the image filename with video name and timestamp
    image_filename = os.path.join(output_folder, f"{video_name}_{int(frame_unix_ts*10)}.jpg")

    # Save the frame
    cv2.imwrite(image_filename, frame)
    
    # Call find_closest_timestamp to find the closest GPS and depth
    closest_row, estimated_depth = find_closest_timestamp(gps_df, frame_unix_ts)

    # Latitude and longitude from the closest timestamp
    lat, lon = closest_row['latitude'], closest_row['longitude']

    # Use the estimated depth (from the next valid point or the original if no valid point exists)
    altitude = estimated_depth
    
    # Geotag the image
    write_geotag(image_filename, lat, lon, altitude)

    return i + 1  # Update index for next image

def process_video(video_path, gps_csv_path, interval_seconds, output_folder):
    """ Main function to grab frames, assign timestamps and geotag them for a video file. """
    gps_df = pd.read_csv(gps_csv_path)
    
    # Get video start time and frame rate
    # video_start_time = get_timestamp_from_video(video_path)
    video_start_time = datetime.strptime("20250128110634", '%Y%m%d%H%M%S')  # Use your video start time
    video = cv2.VideoCapture(video_path)
    fps = round(video.get(cv2.CAP_PROP_FPS))  # Frames per second
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))  # Total number of frames in the video
    
    # Ensure output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    frame_count = 0
    i = 1
    video_name = os.path.splitext(os.path.basename(video_path))[0]  # Get video filename without extension
    
    # Wrap the frame loop with tqdm for progress tracking
    with tqdm(total=total_frames, desc="Processing frames", unit="frame") as pbar:
        while True:
            ret, frame = video.read()
            if not ret:
                break

            # Grab frame every `interval_seconds`
            if frame_count % (fps * interval_seconds) == 0:
                # Process the frame and geotag it
                i = process_frame(frame, video_start_time, gps_df, fps, frame_count, video_name, output_folder, i)

            frame_count += 1
            pbar.update(1)  # Update progress bar after processing each frame

    video.release()

def main():
    video_path = "c:/a/0Jan2025/20250128/blueboat/videos/DJI_20251228110634_0007_D.MP4"  # Change this to your video file
    gps_csv_path = "c:/a/0Jan2025/20250128/blueboat/gps_Warrior_Blueboat_28012025.csv"  # Change this to your GPS CSV file
    output_folder = "c:/a/0Jan2025/20250128/blueboat/framegrab_test"  # Specify the folder where images will be saved
    interval_seconds = 0.3  # Specify how often (in seconds) to grab a frame
    
    process_video(video_path, gps_csv_path, interval_seconds, output_folder)

if __name__ == "__main__":
    main()
    print("DONE")

    print("\n\n\n\t /\_ /\    ♡\n\t(• - • ̳)\n\t |、ﾞ~ヽ\n\t じしf_; )ノ \n    © Joan Li, 2025")

