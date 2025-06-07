from PIL import Image, ImageDraw, ImageFont
from PIL.ExifTags import TAGS
from datetime import datetime
import pandas as pd
import os
import shutil
import subprocess

TEXT_CONFIG = {
    'font_size_ratio': 0.03,
    'padding': 50,
    'outline_range': 2,
    'font_path': "DejaVuSans-Bold.ttf",
    'text_fill': "white",
    'outline_fill': "black"
}

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

def get_image_dataframe(dir_path, force_alphabetical_order=False):
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
    print(df[['width', 'height', 'aspect_ratio']]
      .describe()
      .loc[['count', 'mean', 'std']])

    print(f"Using order based on {'filename' if force_alphabetical_order else 'timestamp'}")
    print(f"First image: {df.iloc[0]['file']}, Last image: {df.iloc[-1]['file']}")

    if force_alphabetical_order:
        df = df.sort_values(by='file')
    else:
        df = df.sort_values(by='timestamp')

    return df.reset_index(drop=True)

def suggest_common_scale(df):
    valid_df = df.dropna(subset=['width', 'height'])
    if valid_df.empty:
        print("No valid image dimensions found.")
        return None

    most_common_width = valid_df['width'].mode()[0]
    most_common_height = valid_df['height'].mode()[0]
    print(f"Suggested common scale: {most_common_width}:{most_common_height}")
    return f"{most_common_width}:{most_common_height}"

def generate_images_with_timestamps(df, output_dir):
    print(f"Generating timestamped images in '{output_dir}'...")
    os.makedirs(output_dir, exist_ok=True)
    temp_paths = []

    for i, row in df.iterrows():
        try:
            img = Image.open(row['path']).convert("RGB")
            draw = ImageDraw.Draw(img)
            width, height = img.size
            timestamp_str = row['timestamp'].strftime("%Y-%m-%d %H:%M:%S") if row['timestamp'] else "Unknown"

            font_size = int(height * TEXT_CONFIG['font_size_ratio'])
            try:
                font = ImageFont.truetype(TEXT_CONFIG['font_path'], font_size)
            except:
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), timestamp_str, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            x = TEXT_CONFIG['padding']
            y = height - text_height - TEXT_CONFIG['padding']

            for ox in range(-TEXT_CONFIG['outline_range'], TEXT_CONFIG['outline_range'] + 1):
                for oy in range(-TEXT_CONFIG['outline_range'], TEXT_CONFIG['outline_range'] + 1):
                    if ox == 0 and oy == 0:
                        continue
                    draw.text((x + ox, y + oy), timestamp_str, font=font, fill=TEXT_CONFIG['outline_fill'])

            draw.text((x, y), timestamp_str, fill=TEXT_CONFIG['text_fill'], font=font)

            temp_path = os.path.join(output_dir, f"frame_{i:04d}.jpg")
            img.save(temp_path)
            temp_paths.append(temp_path)
            print(f"Saved: {temp_path}")
        except Exception as e:
            print(f"Error processing image {row['path']}: {e}")

    print("Finished generating timestamped images.")
    return temp_paths

def generate_timelapse_ffmpeg(
    df,
    output_path="timelapse.mp4",
    fps=30,
    overlay_timestamp=False,
    crf=23,
    preset="medium",
    scale=None,
    codec="libx264",
    pix_fmt="yuv420p",
    delete_temp_files=True
):
    temp_dir = "./temp_with_text"
    if overlay_timestamp:
        df = df.reset_index(drop=True)
        image_paths = generate_images_with_timestamps(df, temp_dir)
    else:
        image_paths = df['path'].tolist()

    print("Creating input list for FFmpeg...")
    temp_list_file = "input_list.txt"
    with open(temp_list_file, "w") as f:
        for path in image_paths:
            f.write(f"file '{path}'\n")

    filters = []
    if scale:
        filters.append(f"scale={scale}")

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

    print("Running FFmpeg command:")
    print(command)
    subprocess.run(command, shell=True)
    os.remove(temp_list_file)

    if delete_temp_files and overlay_timestamp:
        print(f"Removing temporary directory '{temp_dir}'...")
        shutil.rmtree(temp_dir, ignore_errors=True)

    print(f"Timelapse video saved as: {final_output_path}")
