
# Video Frame Extraction and Geotagging

This script extracts frames from MP4 video files at regular intervals, assigns timestamps based on the video filename, and geotags the frames using GPS data from a CSV file.

## Requirements

- Python 3.x
- OpenCV (`cv2`) for video processing
- `tqdm` for progress bars
- `pyexiftool` for geotagging images
- `pandas` for handling CSV data

You can install the necessary Python packages using pip:

```bash
pip install opencv-python tqdm pandas pyexiftool
```

## Files

- **`main.py`**: The main script that grabs frames from the video and geotags them.
- **`gps.csv`**: A CSV file containing GPS data, including timestamps (in unix epoch) and coordinates. Example format:

    | latitude   | longitude   | depth       | unix_ts   |
    |------------|-------------|-------------|-----------|
    | -9.7900168 | 143.0363168 | 36.73999786 | 1738020473 |
    | -9.7900166 | 143.0363168 | 36.73999786 | 1738020473 |
    | -9.7900163 | 143.036317  | 36.73999786 | 1738020473 |

- **Video File(s)**: MP4 video files where the filename contains the timestamp of when the video started recording.

## Video Filename Structure

The script assumes the following filename structure for the MP4 videos:

```
DJI_YYYYMMDDHHMMSS_XXXX_XXX.MP4
```

Where:
- `YYYYMMDDHHMMSS`: The timestamp when the video recording started (e.g., `20251228110634`).
- `XXXX_XXX`: Additional identifiers for the video (e.g., `0007_D`).

## Usage
 (need to modify still)

### Script Overview

1. **Extracts Frames**: Grabs a frame from the video every `interval` seconds based on the video's frame rate.
2. **Assigns Timestamp**: Uses the timestamp in the filename to assign a timestamp to the image.
3. **Geotags Image**: Finds the closest GPS timestamp from the CSV file and writes the corresponding coordinates into the image’s EXIF data.

## Example Workflow

1. **Input**:
   - A video file `DJI_20251228110634_0007_D.MP4`
   - A GPS CSV file `gps.csv` containing timestamps and GPS coordinates.

2. **Process**:
   - The script extracts frames from the video every 5 seconds.
   - The timestamp from the video filename (`20251228110634`) is used to determine the time each frame is extracted.
   - The script finds the closest GPS timestamp from the CSV file and geotags each image.

3. **Output**:
   - Each frame is saved as an image (e.g., `DJI_20251228110634_0007_D_17380263940.jpg`).
   - The corresponding GPS coordinates (latitude, longitude) and depth collected from depth sounder (if below 5m, above 5m is a depth sounder failure since the boat was only driven in the shallow) are written to the image's EXIF metadata.

## Notes

- Make sure the video filename contains a timestamp in the `YYYYMMDDHHMMSS` format.
- Ensure the gps file has unix epoch time in unit s.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**© Joan Li, 2025**
