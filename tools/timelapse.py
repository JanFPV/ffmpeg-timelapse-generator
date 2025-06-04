from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime
import pandas as pd
import os
import subprocess

def extract_exif_timestamp(image_path):
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        if exif_data is None:
            return None
        for tag, value in exif_data.items():
            tag_name = TAGS.get(tag, tag)
            if tag_name == "DateTimeOriginal":
                return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
    except Exception as e:
        print(f"Error reading EXIF from {image_path}: {e}")
    return None

def get_image_dataframe(dir_path):
    files = sorted([f for f in os.listdir(dir_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    data = []

    for file in files:
        path = os.path.join(dir_path, file)
        timestamp = extract_exif_timestamp(path)
        if timestamp is None:
            try:
                timestamp = datetime.fromtimestamp(os.path.getmtime(path))
            except Exception as e:
                print(f"Error reading file timestamp for {path}: {e}")
                timestamp = None

        try:
            with Image.open(path) as img:
                width, height = img.size
                aspect_ratio = round(width / height, 4)
        except Exception as e:
            print(f"Error reading dimensions for {path}: {e}")
            width, height, aspect_ratio = None, None, None

        data.append({
            'file': file,
            'path': path,
            'timestamp': timestamp,
            'width': width,
            'height': height,
            'aspect_ratio': aspect_ratio
        })

    df = pd.DataFrame(data)

    print("Image resolution summary:")
    print(df[['width', 'height', 'aspect_ratio']].describe(include='all'))

    return df.sort_values(by='timestamp').reset_index(drop=True)

def suggest_common_scale(df):
    valid_df = df.dropna(subset=['width', 'height'])
    if valid_df.empty:
        print("No valid image dimensions found.")
        return None

    most_common_width = valid_df['width'].mode()[0]
    most_common_height = valid_df['height'].mode()[0]
    print(f"Suggested common scale: {most_common_width}:{most_common_height}")
    return f"{most_common_width}:{most_common_height}"

def generate_timelapse_ffmpeg(
    df,
    output_path="timelapse.mp4",
    fps=30,
    overlay_timestamp=False,
    crf=23,
    preset="medium",
    scale=None,
    codec="libx264",
    pix_fmt="yuv420p"
):
    temp_list_file = "input_list.txt"

    with open(temp_list_file, "w") as f:
        for _, row in df.iterrows():
            f.write(f"file '{row['path']}'\n")

    filters = []
    if scale:
        filters.append(f"scale={scale}")

    if overlay_timestamp:
        drawtext = (
            "drawtext=\""
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"text='%{{pts\\:localtime\\:{int(df.iloc[0]['timestamp'].timestamp())}+t}}':"
            "fontcolor=white: fontsize=24: box=1: boxcolor=black@0.5: x=10: y=10\""
        )
        filters.append(drawtext)

    filter_str = f"-vf {','.join(filters)}" if filters else ""

    base, ext = os.path.splitext(output_path)
    counter = 1
    final_output_path = output_path
    while os.path.exists(final_output_path):
        final_output_path = f"{base}_{counter}{ext}"
        counter += 1

    command = (
        f"ffmpeg -y -f concat -safe 0 -r {fps} -i {temp_list_file} {filter_str} "
        f"-c:v {codec} -crf {crf} -preset {preset} -pix_fmt {pix_fmt} {final_output_path}"
    )

    print("Running:", command)
    subprocess.run(command, shell=True)
    os.remove(temp_list_file)
