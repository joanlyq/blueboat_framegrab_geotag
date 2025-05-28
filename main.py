import cv2
import os
import pandas as pd
from datetime import datetime
from tqdm import tqdm
import exiftool

def get_video_start_time(video_path):
    """
    Extract the timestamp from the video filename if it follows the DJI pattern.
    If not (e.g. for GoPro videos), extract the creation time from the video's EXIF metadata.
    """
    import os
    from datetime import datetime
    import exiftool

    basename = os.path.basename(video_path)
    if basename.startswith("DJI_"):
        try:
            # Expecting a name like: DJI_YYYYMMDDHHMMSS_XXXX_XXX.MP4
            timestamp_str = basename.split('_')[1]
            return datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
        except Exception:
            pass  # If parsing fails, fall back to metadata extraction

    # For GoPro or other videos: use exif metadata (e.g. "File:FileModifyDate")
    with exiftool.ExifToolHelper() as et:
        metadata_list = et.get_metadata(video_path)
    if metadata_list and isinstance(metadata_list, list):
        metadata = metadata_list[0]
        creation_time_str = metadata.get("File:FileModifyDate") or metadata.get("SourceFile:FileModifyDate")
    else:
        raise ValueError("No metadata found for the video")

    if creation_time_str:
        # Remove timezone offset by splitting on space and then splitting the time part on '+'
        date_part, time_part = creation_time_str.split(" ")[0], creation_time_str.split(" ")[1]
        # Remove the timezone (if present) from the time part.
        time_part = time_part.split('+')[0].strip()
        clean_time_str = date_part + " " + time_part
        # Assume a format like "2025:01:29 10:13:00" (adjust the format string if needed)
        return datetime.strptime(clean_time_str, "%Y:%m:%d %H:%M:%S")
    
    raise ValueError("Could not extract video creation time from metadata.")

def find_closest_timestamp(gps_df, target_unix_ts):
    """Find the closest timestamp in the GPS dataframe using Unix timestamps.
    
    Retries up to 5 times if a FloatingPointError occurs.
    """
    attempts = 5
    for attempt in range(attempts):
        try:
            # Convert unix_ts to datetime (assuming seconds) and then to seconds as float.
            gps_df['timestamp'] = pd.to_datetime(gps_df['unix_ts'], unit='s')
            ts_sec = gps_df['timestamp'].astype('int64').astype('float64') / 1e9
            gps_df['time_diff'] = (ts_sec - target_unix_ts).abs()
            
            closest_row = gps_df.loc[gps_df['time_diff'].idxmin()]
            
            # Check altitude and try to use a valid altitude if necessary.
            if closest_row['altitude'] > 5:
                gps_df_valid = gps_df[gps_df['altitude'] <= 5]
                if not gps_df_valid.empty:
                    closest_depth_row = gps_df_valid.loc[gps_df_valid['time_diff'].idxmin()]
                    estimated_depth = closest_depth_row['altitude']
                else:
                    estimated_depth = closest_row['altitude']
            else:
                estimated_depth = closest_row['altitude']
            
            return closest_row, estimated_depth
        except FloatingPointError as e:
            print(f"FloatingPointError encountered on attempt {attempt+1}/{attempts}. Retrying...")
            if attempt == attempts - 1:
                raise e

    """Find the closest timestamp in the GPS dataframe using Unix timestamps."""
    print(gps_df['unix_ts'].tail())

    gps_df['timestamp'] = pd.to_datetime(gps_df['unix_ts'], unit='s')
    gps_df['time_diff'] = (gps_df['timestamp'].astype('int64').astype('float64') / 10**9 - target_unix_ts).abs()
    
    closest_row = gps_df.loc[gps_df['time_diff'].idxmin()]
    
    if closest_row['altitude'] > 5:
        gps_df_valid = gps_df[gps_df['altitude'] <= 5]
        if not gps_df_valid.empty:
            closest_depth_row = gps_df_valid.loc[gps_df_valid['time_diff'].idxmin()]
            estimated_depth = closest_depth_row['altitude']
        else:
            estimated_depth = closest_row['altitude']
    else:
        estimated_depth = closest_row['altitude']
    
    return closest_row, estimated_depth

def write_geotag(image_path, lat, lon, altitude):
    """Write latitude, longitude, and altitude into the image's EXIF metadata."""
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
    """Process a single frame: save and geotag it."""
    timestamp = video_start_time + pd.to_timedelta(frame_count / fps, unit='s')
    frame_unix_ts = round(timestamp.timestamp(), 2)
    
    image_filename = os.path.join(output_folder, f"{video_name}_{int(frame_unix_ts*10)}.jpg")
    cv2.imwrite(image_filename, frame)
    
    closest_row, estimated_depth = find_closest_timestamp(gps_df, frame_unix_ts)
    lat, lon = closest_row['latitude'], closest_row['longitude']
    altitude = estimated_depth
    
    write_geotag(image_filename, lat, lon, altitude)
    
    return i + 1

def process_video(video_path, gps_csv_path, output_folder, time_intervals):
    """
    Process the video by extracting frames based on specified time intervals.
    
    For each interval that overlaps with the video:
      - If the overlapping interval lasts more than 60 seconds, extract a frame every 20 seconds.
      - Otherwise, extract a frame every 5 seconds.
      
    This version uses direct frame seeking (via cv2.CAP_PROP_POS_FRAMES) to efficiently jump
    to the desired frames.
    """

    # Load GPS data and get the video start time
    gps_df = pd.read_csv(gps_csv_path)
    video_start_time = get_video_start_time(video_path)
    
    video = cv2.VideoCapture(video_path)
    fps = round(video.get(cv2.CAP_PROP_FPS))
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_seconds = total_frames / fps
    video_end_time = video_start_time + pd.to_timedelta(duration_seconds, unit='s')
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    i = 1  # image counter

    # Process each time interval
    for interval in time_intervals:
        start_interval, end_interval = interval
        # Determine the effective interval (overlap between video and given interval)
        effective_start = max(video_start_time, start_interval)
        effective_end = min(video_end_time, end_interval)
        
        if effective_start >= effective_end:
            # No overlap with the video.
            continue
        
        # Determine saving interval based on the effective interval's duration.
        effective_duration = (effective_end - effective_start).total_seconds()
        if effective_duration > 300:
            saving_interval = 20  # seconds
        else:
            saving_interval = 5   # seconds
        
        # Calculate the step in frames corresponding to the saving interval.
        step = int(fps * saving_interval)
        # Compute the start and end frame numbers corresponding to the effective time window.
        start_frame = int((effective_start - video_start_time).total_seconds() * fps)
        end_frame = int((effective_end - video_start_time).total_seconds() * fps)
        
        # Loop through the frames for this effective interval.
        for frame_num in tqdm(range(start_frame, end_frame + 1, step),
                              desc=f"Processing {video_name} for interval {effective_start.strftime('%H:%M:%S')}-{effective_end.strftime('%H:%M:%S')}",
                              unit="frame"):
            video.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = video.read()
            if not ret:
                break
            # Compute the timestamp for this frame.
            timestamp = video_start_time + pd.to_timedelta(frame_num / fps, unit='s')
            # Process (save and geotag) the frame.
            i = process_frame(frame, video_start_time, gps_df, fps, frame_num,
                              video_name, output_folder, i)
    
    video.release()


# Assume get_video_start_time, process_video, and process_frame are defined as before

def video_overlaps_interval(video_path, time_intervals):
    """
    Determine whether the video at video_path overlaps any of the given time_intervals.
    Returns a tuple (overlap, video_start_time, video_end_time)
    """
    try:
        video_start_time = get_video_start_time(video_path)
    except Exception as e:
        print(f"Error reading start time for {video_path}: {e}")
        return False, None, None

    cap = cv2.VideoCapture(video_path)
    fps = round(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    
    if fps <= 0:
        print(f"Warning: {video_path} has an invalid FPS value ({fps}). Skipping.")
        return False, video_start_time, video_start_time

    duration_seconds = total_frames / fps
    video_end_time = video_start_time + pd.to_timedelta(duration_seconds, unit='s')
    
    # Check if video time overlaps any interval:
    for start, end in time_intervals:
        if video_end_time >= start and video_start_time <= end:
            return True, video_start_time, video_end_time
    return False, video_start_time, video_end_time

def process_videos_in_folder(root_folder, gps_csv_path, output_folder,
                             time_intervals):
    """
    Recursively search for video files in root_folder (including subfolders),
    check if their time range overlaps any of the time_intervals, and if so, process them.
    """
    video_extensions = ('.MP4', '.MOV', '.mp4', '.mov', '.avi')
    video_files = []
    for dirpath, dirnames, filenames in os.walk(root_folder, followlinks=True):
        for filename in filenames:
            if filename.lower().endswith(('.mp4')):
                video_files.append(os.path.join(dirpath, filename))
    
    print(f"Found {len(video_files)} video files.")
    
    for video_path in video_files:
        overlaps, video_start, video_end = video_overlaps_interval(video_path, time_intervals)
        if overlaps:
            print(f"Processing video: {video_path}")
            print(f"   Video start: {video_start}, Video end: {video_end}")
            process_video(video_path, gps_csv_path, output_folder, time_intervals)
        else:
            print(f"Skipping video (no overlapping interval): {video_path}")


def main():
    # # Define your root folder containing subfolders with videos.
    # root_folder = "/Users/jlimini/GeoNadir/blueboat_framegrab_geotag/videos"
    
    # # GPS CSV path, output folder, and other parameters remain as before.
    # # gps_csv_path = "/Users/jlimini/GeoNadir/blueboat_framegrab_geotag/blueboad_20250129_gps.csv"
    # gps_csv_path = "/Users/jlimini/GeoNadir/blueboat_framegrab_geotag/rov_20250129_gps.csv"
    # output_folder = "/Users/jlimini/GeoNadir/blueboat_framegrab_geotag/output"

    # Define your root folder containing subfolders with videos.
    root_folder = "/Users/jlimini/GeoNadir/blueboat_framegrab_geotag/20250202/video"
    
    # GPS CSV path, output folder, and other parameters remain as before.
    # gps_csv_path = "/Users/jlimini/GeoNadir/blueboat_framegrab_geotag/blueboad_20250129_gps.csv"
    gps_csv_path = "/Users/jlimini/GeoNadir/blueboat_framegrab_geotag/20250202/blueboat_dungeness_20250202_1102.csv"
    output_folder = "/Users/jlimini/GeoNadir/blueboat_framegrab_geotag/20250202/blueboat_output"

    # # Define the date to use for all time intervals.
    # date_str = "20250129"  # January 29, 2025

    # time_intervals = [
    #     # Interval 1: 10:13-10:20 (assumes seconds are 00)
    #     (
    #         datetime.strptime(date_str + "101300", "%Y%m%d%H%M%S"),
    #         datetime.strptime(date_str + "102000", "%Y%m%d%H%M%S")
    #     ),
    #     # Interval 2: 12:25-12:44
    #     (
    #         datetime.strptime(date_str + "122500", "%Y%m%d%H%M%S"),
    #         datetime.strptime(date_str + "124400", "%Y%m%d%H%M%S")
    #     ),
    #     # Interval 3: 12:29-12:31
    #     (
    #         datetime.strptime(date_str + "122900", "%Y%m%d%H%M%S"),
    #         datetime.strptime(date_str + "123100", "%Y%m%d%H%M%S")
    #     ),
    #     # Interval 4: 12:32-12:37
    #     (
    #         datetime.strptime(date_str + "123200", "%Y%m%d%H%M%S"),
    #         datetime.strptime(date_str + "123700", "%Y%m%d%H%M%S")
    #     ),
    #     # Interval 5: 14:21:57-14:21:57 (a single moment)
    #     (
    #         datetime.strptime(date_str + "142157", "%Y%m%d%H%M%S"),
    #         datetime.strptime(date_str + "142157", "%Y%m%d%H%M%S")
    #     ),
    #     # Interval 6: 12:56:10-13:13:42
    #     (
    #         datetime.strptime(date_str + "125610", "%Y%m%d%H%M%S"),
    #         datetime.strptime(date_str + "131342", "%Y%m%d%H%M%S")
    #     ),
    #     # Interval 7: 13:09:16-13:10:17
    #     (
    #         datetime.strptime(date_str + "130916", "%Y%m%d%H%M%S"),
    #         datetime.strptime(date_str + "131017", "%Y%m%d%H%M%S")
    #     ),
    #     # Interval 8: 13:06:54-13:07:30
    #     (
    #         datetime.strptime(date_str + "130654", "%Y%m%d%H%M%S"),
    #         datetime.strptime(date_str + "130730", "%Y%m%d%H%M%S")
    #     ),
    #     # Interval 9: 13:05:03-13:05:12
    #     (
    #         datetime.strptime(date_str + "130503", "%Y%m%d%H%M%S"),
    #         datetime.strptime(date_str + "130512", "%Y%m%d%H%M%S")
    #     )
    # ]
    
    # Define the date to use for all time intervals.
    date_str = "20250202"  # January 29, 2025

    time_intervals = [
        # Interval 1: 10:13-10:20 (assumes seconds are 00)
        (
            datetime.strptime(date_str + "111434", "%Y%m%d%H%M%S"),
            datetime.strptime(date_str + "112018", "%Y%m%d%H%M%S")
        ),
        # Interval 2: 12:25-12:44
        (
            datetime.strptime(date_str + "110410", "%Y%m%d%H%M%S"),
            datetime.strptime(date_str + "111142", "%Y%m%d%H%M%S")
        ),
        # Interval 3: 12:29-12:31
        (
            datetime.strptime(date_str + "124452", "%Y%m%d%H%M%S"),
            datetime.strptime(date_str + "125631", "%Y%m%d%H%M%S")
        ),
        # Interval 4: 12:32-12:37
        (
            datetime.strptime(date_str + "115239", "%Y%m%d%H%M%S"),
            datetime.strptime(date_str + "120323", "%Y%m%d%H%M%S")
        )
    ]
    # Define the saving interval (e.g., only save one frame every 10 seconds per interval).
    saving_interval = 10  # seconds
    
    
    # Process all videos in the folder structure
    process_videos_in_folder(root_folder, gps_csv_path, output_folder,
                             time_intervals)

if __name__ == "__main__":
    main()
    print("DONE")
    print("\n\n\n\t /\_ /\    ♡\n\t(• - • ̳)\n\t |、ﾞ~ヽ\n\t じしf_; )ノ \n    © Joan Li, 2025")
