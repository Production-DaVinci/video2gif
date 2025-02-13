import streamlit as st
import moviepy.editor as mp
import tempfile
import os

def main():
    st.title("Video to GIF Converter")

    uploaded_file = st.file_uploader(
        "Upload a video file (up to 100MB)",
        type=["mp4", "mov", "avi", "m4v", "mpeg", "mkv"]
    )

    if uploaded_file is not None:
        # ファイルサイズチェック
        uploaded_file.seek(0, os.SEEK_END)
        file_size = uploaded_file.tell()
        uploaded_file.seek(0)
        if file_size > 100 * 1024 * 1024:
            st.error("File size exceeds 100MB. Please upload a smaller file.")
            return

        # 一時ファイルへ書き出し
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
            tmp_file.write(uploaded_file.read())
            original_file_path = tmp_file.name

        # 1) MoviePyで動画読込み
        clip = mp.VideoFileClip(original_file_path)

        # 2) iPhone動画の回転メタデータを取得 (0, 90, 180, 270 のいずれか)
        rotation = getattr(clip, 'rotation', 0)

        # 3) 必要に応じて -rotation 方向に回転 (物理フレームを回転)
        #    expand=True で縦横のピクセル数を正しく再計算する
        if rotation == 90:
            clip = clip.rotate(-90, expand=True)
        elif rotation == 180:
            clip = clip.rotate(180, expand=True)
        elif rotation == 270:
            clip = clip.rotate(90, expand=True)

        # 4) 回転メタデータを強制的に 0 にするために
        #    ffmpeg_params で "rotate=0" を指定して再エンコード
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as oriented_tmp:
            oriented_file_path = oriented_tmp.name

        # エンコード時に -metadata rotate=0 を付与し、回転メタデータを消去
        clip.write_videofile(
            oriented_file_path,
            codec='libx264',
            audio=False,
            verbose=False,
            logger=None,
            ffmpeg_params=['-metadata', 'rotate=0']  # ← これで回転情報を0に
        )

        # 5) 正しい向きになった動画をプレビュー
        st.write("### Original Video (Fixed Orientation)")
        st.video(oriented_file_path)

        # 動画長さを取得
        duration = clip.duration

        # 6) スライダーでサブクリップ区間を指定
        st.write("Select the start and end times (up to 15 seconds).")
        start_time = st.slider("Start time (seconds)", 0.0, float(duration), 0.0, 0.1)
        end_time = st.slider("End time (seconds)", 0.0, float(duration), min(duration, 15.0), 0.1)

        if end_time < start_time:
            st.error("End time must be greater than start time.")
            return
        if (end_time - start_time) > 15:
            st.error("Please select a duration of 15 seconds or less.")
            return

        st.write(f"**Selected range**: {start_time:.2f} - {end_time:.2f} seconds")

        # 7) サブクリップをプレビューする
        if st.button("Preview Subclip"):
            with st.spinner("Generating subclip preview..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as subclip_temp:
                    subclip_path = subclip_temp.name

                # 選択範囲の subclip
                sub_clip = clip.subclip(start_time, end_time)

                # 音声不要なら audio=False
                sub_clip.write_videofile(
                    subclip_path,
                    codec='libx264',
                    audio=False,
                    verbose=False,
                    logger=None,
                    ffmpeg_params=['-metadata', 'rotate=0']
                )
                sub_clip.close()

                st.write("### Subclip Preview")
                st.video(subclip_path)

        # 8) GIF生成
        if st.button("Generate GIF"):
            with st.spinner("Converting to GIF..."):
                gif_subclip = clip.subclip(start_time, end_time)

                # 横幅 640px を超えるなら縮小
                if gif_subclip.w > 640:
                    new_height = int(gif_subclip.h * 640 / gif_subclip.w)
                    gif_subclip = gif_subclip.resize((640, new_height))

                # GIF一時ファイル
                gif_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".gif")
                gif_temp_path = gif_temp.name
                gif_temp.close()

                gif_subclip.write_gif(gif_temp_path, fps=15, program="ffmpeg")

                # GIFを読み込んで表示
                with open(gif_temp_path, "rb") as f:
                    gif_bytes = f.read()

                gif_subclip.close()

                st.image(gif_bytes, caption="Converted GIF", use_container_width=True)
                st.download_button(
                    label="Download GIF",
                    data=gif_bytes,
                    file_name="converted.gif",
                    mime="image/gif"
                )

                os.remove(gif_temp_path)

        # 後処理
        clip.close()
        if os.path.exists(original_file_path):
            os.remove(original_file_path)
        if os.path.exists(oriented_file_path):
            os.remove(oriented_file_path)

    else:
        st.write("Please upload a video file.")


if __name__ == "__main__":
    main()
