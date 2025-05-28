
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

***Alternatively, and preferrably you can set up a Conda environment to run the script. ***

### Installing Miniconda (macOS & Windows)

Miniconda is a minimal distribution of Conda, which is lightweight and ideal for managing Python environments and packages.

#### macOS Installation

1. **Download Miniconda for macOS**:
   - Visit the official Miniconda download page: [Miniconda Download](https://docs.conda.io/en/latest/miniconda.html)
   - Under "Miniconda3 MacOSX 64-bit", click on the **Miniconda3 macOS 64-bit pkg** installer.

2. **Install Miniconda**:
   - Once the installer is downloaded, open the `.pkg` file to start the installation process.
   - Follow the on-screen instructions to complete the installation.

3. **Verify Installation**:
   - Open a terminal and run the following command to verify the installation:
     ```bash
     conda --version
     ```
   - This should return the version of Conda you just installed.

#### Windows Installation

1. **Download Miniconda for Windows**:
   - Visit the official Miniconda download page: [Miniconda Download](https://docs.conda.io/en/latest/miniconda.html)
   - Under "Miniconda3 Windows 64-bit", click on the **Miniconda3 Windows 64-bit exe** installer.

2. **Install Miniconda**:
   - Once the installer is downloaded, run the `.exe` file to start the installation process.
   - Follow the on-screen instructions to complete the installation. You can choose the default installation options.

3. **Verify Installation**:
   - Open **Command Prompt** (or **Anaconda Prompt**) and run the following command to verify the installation:
     ```bash
     conda --version
     ```
   - This should return the version of Conda you just installed.

### Installing Dependencies

After installing Miniconda, you can create a Conda environment with the required dependencies for the script:

1. **Create a Conda Environment**:
   - Open your terminal (macOS) or Command Prompt (Windows) and run the following command to create a new environment named `geotagging-env`:
     ```bash
     conda create -n geotagging-env python=3.8
     ```
   - You can replace `geotagging-env` with any name you prefer for the environment.

2. **Activate the Conda Environment**:
   - To activate the environment, run:
     ```bash
     conda activate geotagging-env
     ```

3. **Install Required Packages**:
   - Install the necessary packages by running the following command:
     ```bash
     conda install -c conda-forge opencv tqdm pandas pyexiftool
     ```

## Files in the working dir

- **`main.py`**: The main script that grabs frames from the video and geotags them.
- **`gps.csv`**: A CSV file containing GPS data, including timestamps (in unix epoch) and coordinates. Example format:

    | latitude   | longitude   | depth       | unix_ts   |
    |------------|-------------|-------------|-----------|
    | -9.7900168 | 143.0363168 | 36.73999786 | 1738020473 |
    | -9.7900166 | 143.0363168 | 36.73999786 | 1738020473 |
    | -9.7900163 | 143.036317  | 36.73999786 | 1738020473 |


## GPS CSV Conversion

The CSV file should include the following columns:

- `timestamp(ms)`: Timestamp in milliseconds from blueboat log.

- `GPS.NSats`: Number of GPS satellites used from blueboat log.

- `GPS.Lat`: Latitude in nanodegrees (multiply by 10^-9 to get degrees) from blueboat log.

- `GPS.Lng`: Longitude in nanodegrees (multiply by 10^-9 to get degrees) from blueboat log.

- `GPS.GWk`: GPS week number from blueboat log.

- `GPS.GMS`: GPS milliseconds from blueboat log.

- `DPTH.Depth`: Depth value from blueboat log.

- `unix_ts`: Unix timestamp (seconds since 1970).

- `utc_time`: UTC time as YYYY/MM/DDTHH:MM:SS.

- `local_time`: Local time as YYYY/MM/DDTHH:MM:SS.

- `name`: Local time as YYYY/MM/DDTHH:MM:SS (Used for upload to geonadir, not a compulsory column).

- `latitude`: Latitude value.

- `longitude`: Longitude value.

- `altitude`: Altitude value.

### Converting GPS.GWk and GPS.GMS to Unix Timestamp

**Converting GPS.GWk and GPS.GMS to Unix Timestamp via Excel**

To convert GPS.GWk and GPS.GMS to Unix timestamp in Excel, you can use the following formula:

1. Formula for Unix Timestamp:

```
= ((GPS_Week * 7 * 24 * 3600) + (GPS_GMS / 1000)) - 18 + (DATE(1980,1,6) - DATE(1970,1,1)) * 86400
```
Here's the breakdown:

- `GPS_Week * 7 * 24 * 3600`: Converts the GPS week to seconds (7 days/week, 24 hours/day, 3600 seconds/hour).

- `GPS_GMS / 1000`: Converts the milliseconds to seconds.

- `-18`: Corrects for the 18 leap seconds between GPS time and UTC time.

- `(DATE(1980,1,6) - DATE(1970,1,1)) * 86400`: Converts the GPS epoch (January 6, 1980) to Unix epoch seconds (starting from January 1, 1970).

2. Converting GPS time to UTC:

You can double-check your results by converting the GPS time to UTC using this online calculator: [Labsat GPS Time Converter](https://www.labsat.co.uk/index.php/en/gps-time-calculator).

 3. Convert UTC to Unix Timestamp:
 
After confirming the UTC time, you can convert it to Unix timestamp using this online tool: [Unix Timestamp Converter](https://www.unixtimestamp.com/).

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
1. Input:

- A folder that contain video files from blueboat DJI_20251228110634_0007_D.MP4.

- A GPS CSV file gps.csv containing timestamps and GPS coordinates. Make sure the CSV includes Unix timestamps in seconds.

2. Configure Frame Extraction:

- Open `main.py` and modify the `gps_csv_path` (path to your GPS CSV file) and `output_folder` (path where images will be saved).

- Set the frame extraction interval:

   - Long interval (`long_saving_interval`): The frame extraction interval when the time duration for extraction is longer than 5 minutes (300 seconds). Default is set to 30 seconds.

   - Short interval (`short_saving_interval`): The frame extraction interval when the time duration for extraction is shorter than 5 minutes. Default is set to 5 seconds.

   - You can adjust these intervals in the script to capture frames at the desired frequency.

3. Processing:

- The script will process each video and extract frames according to the intervals you’ve set. The extracted frames will be saved as images in the specified output folder and geotagged with GPS coordinates.

4. Output:

- Each frame will be saved as an image (e.g., DJI_20251228110634_0007_D_17380263940.jpg).

- The corresponding GPS coordinates (latitude, longitude) and depth are written to the image’s EXIF metadata.

## Notes

- Make sure the video filename contains a timestamp in the `YYYYMMDDHHMMSS` format.
- The GPS CSV file should have Unix epoch time in seconds (not milliseconds).
- Modify the frame extraction interval as needed by adjusting long_saving_interval and short_saving_interval in the code.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**© Joan Li, 2025**
