import streamlit as st
import subprocess
import moviepy.editor as mp
import tempfile
import os

def ffmpeg_subclip_rotate(
    input_path: str,
    output_path: str,
    start: float,
    end: float,
    rotation: int
):
    """
    FFmpeg を使い、[start, end]秒の区間を切り出し & 回転を補正して MP4 出力。
    回転メタデータ (rotate=0) と map_metadata=-1 で余計なメタデータを消去。
    """
    vf_filter = None
    if rotation == 90:
        # 90度回転メタデータ → 実際には -90 で補正 → transpose=2
        vf_filter = "transpose=2"
    elif rotation == 180:
        # 180度 → hflip + vflip
        vf_filter = "hflip,vflip"
    elif rotation == 270:
        # 270度 → +90 で補正 → transpose=1
        vf_filter = "transpose=1"

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

def main():
    st.title("Video to GIF Converter (Extra Compact)")

    uploaded_file = st.file_uploader(
        "Upload a video file (up to 100MB)",
        type=["mp4", "mov", "avi", "m4v", "mpeg", "mkv"]
    )

    if uploaded_file is not None:
        # ファイルサイズチェック
        uploaded_file.seek(0, os.SEEK_END)
        size = uploaded_file.tell()
        uploaded_file.seek(0)
        if size > 100 * 1024 * 1024:
            st.error("File size exceeds 100MB.")
            return

        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            input_path = f.name
            f.write(uploaded_file.read())

        # MoviePyで読み込み (長さと回転を取得)
        clip = mp.VideoFileClip(input_path)
        duration = clip.duration
        rotation = getattr(clip, 'rotation', 0)
        clip.close()

        st.write(f"Detected rotation: {rotation} deg")
        st.write(f"Video duration: {duration:.2f} seconds")

        # スライダーで開始・終了時間を指定 (最大15秒)
        start_time = st.slider("Start Time (s)", 0.0, float(duration), 0.0, 0.1)
        end_time = st.slider("End Time (s)", 0.0, float(duration), min(duration, 15.0), 0.1)

        if end_time < start_time:
            st.error("End time must be >= start time.")
            return
        if (end_time - start_time) > 15:
            st.error("Please select a duration of 15s or less.")
            return

        # プレビュー用ボタン
        if st.button("Preview Subclip"):
            with st.spinner("FFmpeg cutting & rotating..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                    preview_path = tmp.name

                ffmpeg_subclip_rotate(
                    input_path,
                    preview_path,
                    start_time,
                    end_time,
                    rotation
                )
                st.video(preview_path)

        # GIF生成ボタン
        if st.button("Generate GIF"):
            with st.spinner("Generating GIF..."):
                # 1) FFmpegで回転補正＋サブクリップしたMP4を生成
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                    fixed_mp4_path = tmp.name

                ffmpeg_subclip_rotate(
                    input_path,
                    fixed_mp4_path,
                    start_time,
                    end_time,
                    rotation
                )

                # 2) 生成されたMP4をMoviePyで開き、幅が240を超える場合は縮小
                subclip_fixed = mp.VideoFileClip(fixed_mp4_path)
                if subclip_fixed.w > 240:
                    new_h = int(subclip_fixed.h * 240 / subclip_fixed.w)
                    subclip_fixed = subclip_fixed.resize((240, new_h))

                # 3) GIFを出力 (fps=5, colors=32)
                gif_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".gif")
                gif_temp_path = gif_temp.name
                gif_temp.close()

                subclip_fixed.write_gif(
                    gif_temp_path,
                    fps=5,          # 5 FPS → さらに軽量化
                    program="ffmpeg",
                    opt="nq",       # カラーパレット最適化
                    colors=32       # 32色まで減色
                )

                subclip_fixed.close()

                # 表示 & ダウンロード
                with open(gif_temp_path, "rb") as f:
                    gif_bytes = f.read()

                st.image(gif_bytes, caption="Converted GIF (max width=240)", use_container_width=True)
                st.download_button(
                    label="Download GIF",
                    data=gif_bytes,
                    file_name="converted.gif",
                    mime="image/gif"
                )

                # 後片付け
                os.remove(gif_temp_path)
                if os.path.exists(fixed_mp4_path):
                    os.remove(fixed_mp4_path)

        # 後片付け
        if os.path.exists(input_path):
            os.remove(input_path)

    else:
        st.write("Please upload a video file.")


if __name__ == "__main__":
    main()
