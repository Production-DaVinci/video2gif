import streamlit as st
import subprocess
import moviepy.editor as mp
import tempfile
import os
import json

def ffmpeg_subclip_rotate(
    input_path: str,
    output_path: str,
    start: float,
    end: float,
    rotation: int
):
    """
    FFmpeg を使い、[start, end]秒の区間を切り出し & 回転を補正した MP4 を出力。
    回転メタデータ (rotate=0) と map_metadata=-1 で余計なメタデータを消去。
    """
    vf_filter = None
    if rotation == 90:
        vf_filter = "transpose=2"    # -90度回転
    elif rotation == 180:
        vf_filter = "hflip,vflip"    # 180度回転
    elif rotation == 270:
        vf_filter = "transpose=1"    # +90度回転

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-ss", str(start),
        "-to", str(end),
    ]
    if vf_filter:
        cmd += ["-vf", vf_filter]

    cmd += [
        "-c:v", "libx264",
        "-c:a", "aac",  # 必要に応じて "copy" に変更可
        "-metadata", "rotate=0",
        "-map_metadata", "-1",
        output_path
    ]
    subprocess.run(cmd, check=True)


def get_video_metadata(video_path: str) -> dict:
    """
    ffprobe を使って動画のメタデータを取得し、辞書形式で返す。
    - デバイス名 (iPhoneなどの場合は com.apple.quicktime.make / model)
    - 解像度 (width, height)
    - ファイルサイズ (MB)
    - 動画長さ (duration, 秒)
    """
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        return {}

    data = json.loads(result.stdout)

    # 1) format 情報
    fmt = data.get("format", {})
    tags = fmt.get("tags", {})
    size_bytes = float(fmt.get("size", 0))
    duration_sec = float(fmt.get("duration", 0))

    # Apple系タグの場合
    camera_make = tags.get("com.apple.quicktime.make", "Unknown")
    camera_model = tags.get("com.apple.quicktime.model", "")
    device_name = (camera_make + " " + camera_model).strip()

    # 2) streams から video stream を見つけて解像度
    width = height = 0
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            width = stream.get("width", 0)
            height = stream.get("height", 0)
            break

    return {
        "device_name": device_name,
        "width": width,
        "height": height,
        "filesize_mb": size_bytes / (1024 * 1024),
        "duration": duration_sec
    }


def main():
    st.set_page_config(page_title="Video to GIF Converter by Production da Vinci Inc.")
    st.title("Video to GIF Converter by Production da Vinci Inc.")

    uploaded_file = st.file_uploader(
        "Upload a video file (up to 100MB)",
        type=["mp4", "mov", "avi", "m4v", "mpeg", "mkv"]
    )

    if uploaded_file is not None:
        # ▼ 処理中アイコンを画面下に表示
        bottom_spinner = st.empty()
        bottom_spinner.markdown(
            """
            <div style='position: fixed; bottom: 10px; left: 50%; transform: translateX(-50%); z-index:9999;'>
                <img src='https://media.tenor.com/On7kvXhzml4AAAAj/loading-gif.gif' width='40'/>
                <div style='text-align:center; font-size:0.8em; color:#555;'>Processing...</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # ファイルサイズチェック
        uploaded_file.seek(0, os.SEEK_END)
        size = uploaded_file.tell()
        uploaded_file.seek(0)
        if size > 100 * 1024 * 1024:
            st.error("File size exceeds 100MB.")
            bottom_spinner.empty()
            return

        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            input_path = f.name
            f.write(uploaded_file.read())

        # MoviePy で回転取得 (あとでFFmpegに使うため)
        clip = mp.VideoFileClip(input_path)
        rotation = getattr(clip, 'rotation', 0)
        clip.close()

        # ffprobe でメタデータ取得
        meta = get_video_metadata(input_path)
        device_name = meta.get("device_name", "Unknown")
        width = meta.get("width", 0)
        height = meta.get("height", 0)
        filesize_mb = meta.get("filesize_mb", 0)
        duration_sec = meta.get("duration", 0)

        # 取得した情報を表示
        st.write(f"**Device**: {device_name}")
        st.write(f"**Resolution**: {width} x {height}")
        st.write(f"**File Size**: {filesize_mb:.2f} MB")
        st.write(f"**Duration**: {duration_sec:.2f} s")
        st.write(f"**Rotation tag**: {rotation} deg")

        # （プレビュー用MP4生成は不要とのことなのでコメントアウト）
        # with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_whole:
        #     oriented_whole_path = tmp_whole.name
        # ffmpeg_subclip_rotate(
        #     input_path,
        #     oriented_whole_path,
        #     0,
        #     duration_sec,
        #     rotation
        # )
        # st.video(oriented_whole_path)

        # 処理完了したので下部ローディングを消す
        bottom_spinner.empty()

        # サブクリップ指定 (最大15秒)
        start_time = st.slider("Start Time (s)", 0.0, float(duration_sec), 0.0, 0.1)
        end_time = st.slider("End Time (s)", 0.0, float(duration_sec), min(duration_sec, 15.0), 0.1)

        if end_time < start_time:
            st.error("End time must be >= start time.")
            return
        if (end_time - start_time) > 15:
            st.error("Please select a duration of 15s or less.")
            return

        # Generate GIF ボタン
        if st.button("Generate GIF"):
            # 下部にローディング表示を再度出す
            bottom_spinner = st.empty()
            bottom_spinner.markdown(
                """
                <div style='position: fixed; bottom: 10px; left: 50%; transform: translateX(-50%); z-index:9999;'>
                    <img src='https://media.tenor.com/On7kvXhzml4AAAAj/loading-gif.gif' width='40'/>
                    <div style='text-align:center; font-size:0.8em; color:#555;'>Converting to GIF...</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                fixed_mp4_path = tmp.name

            ffmpeg_subclip_rotate(
                input_path,
                fixed_mp4_path,
                start_time,
                end_time,
                rotation
            )

            subclip_fixed = mp.VideoFileClip(fixed_mp4_path)
            if subclip_fixed.w > 240:
                new_h = int(subclip_fixed.h * 240 / subclip_fixed.w)
                subclip_fixed = subclip_fixed.resize((240, new_h))

            gif_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".gif")
            gif_temp_path = gif_temp.name
            gif_temp.close()

            subclip_fixed.write_gif(
                gif_temp_path,
                fps=5,
                program="ffmpeg",
                opt="nq",
                colors=32
            )
            subclip_fixed.close()

            with open(gif_temp_path, "rb") as f:
                gif_bytes = f.read()

            st.image(gif_bytes, caption="Converted GIF (max width=240)", use_container_width=True)
            st.download_button(
                label="Download GIF",
                data=gif_bytes,
                file_name="converted.gif",
                mime="image/gif"
            )

            os.remove(gif_temp_path)
            if os.path.exists(fixed_mp4_path):
                os.remove(fixed_mp4_path)

            # 処理完了したのでローディングを消す
            bottom_spinner.empty()

        # 後片付け
        if os.path.exists(input_path):
            os.remove(input_path)

    else:
        st.write("Please upload a video file.")


if __name__ == "__main__":
    main()
