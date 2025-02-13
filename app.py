import streamlit as st
import moviepy.editor as mp
import tempfile
import os
import io

def main():
    st.title("Video to GIF Converter")

    # 1. ファイルアップロード
    uploaded_file = st.file_uploader(
        "Upload a video file (up to 100MB)", 
        type=["mp4", "mov", "avi", "m4v", "mpeg", "mkv"]
    )

    if uploaded_file is not None:
        # ファイルサイズ確認
        uploaded_file.seek(0, os.SEEK_END)
        file_size = uploaded_file.tell()
        uploaded_file.seek(0)
        if file_size > 100 * 1024 * 1024:
            st.error("File size exceeds 100MB. Please upload a smaller file.")
            return

        # 動画のプレビュー
        st.video(uploaded_file)

        # 一時ファイルに保存 (moviepyはファイルパスを必要とすることが多いため)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_file_path = tmp_file.name

        # 2. 動画読み込みとメタ情報取得
        clip = mp.VideoFileClip(tmp_file_path)
        duration = clip.duration  # 動画の長さ(秒)

        # 3. スライダーで切り出し区間を指定（最大15秒まで）
        st.write("Select the start and end times (up to 15 seconds range).")
        max_end = min(duration, 15.0)  # 上限15秒か、動画が15秒未満なら動画の長さ
        start_time = st.slider("Start time (seconds)", 0.0, float(duration), 0.0, 0.1)
        end_time = st.slider("End time (seconds)", 0.0, float(duration), min(duration, 15.0), 0.1)

        # start_time <= end_time かつ (end_time - start_time) <= 15 となるように制限
        if end_time < start_time:
            st.error("End time must be greater than start time.")
            return
        if (end_time - start_time) > 15:
            st.error("Please select a duration of 15 seconds or less.")
            return

        st.write(f"**Selected range**: {start_time:.2f} - {end_time:.2f} seconds")

        # GIF作成ボタン
        if st.button("Generate GIF"):
            with st.spinner("Converting to GIF..."):
                # 4. MoviePy でサブクリップ作成
                subclip = clip.subclip(start_time, end_time)

                # 5. リサイズ（横幅を最大640pxにしてアスペクト比を保つ）
                if subclip.w > 640:
                    new_height = int(subclip.h * 640 / subclip.w)
                    subclip = subclip.resize((640, new_height))

                # 6. GIF生成
                # 一時ファイルに出力してから読み込む
                gif_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".gif")
                gif_temp_path = gif_temp.name
                gif_temp.close()

                # fps=15, program='ImageMagick' を指定 (or 'ffmpeg')
                subclip.write_gif(gif_temp_path, fps=15, program="ffmpeg")

                # 7. GIFの表示 & ダウンロード用バイナリ取得
                with open(gif_temp_path, "rb") as f:
                    gif_bytes = f.read()

                # GIFを画面に表示
                st.image(gif_bytes, caption="Converted GIF", use_column_width=True)

                # ダウンロードボタン
                st.download_button(
                    label="Download GIF",
                    data=gif_bytes,
                    file_name="converted.gif",
                    mime="image/gif"
                )

                # 後始末
                clip.close()
                subclip.close()
                os.remove(gif_temp_path)
                os.remove(tmp_file_path)

    else:
        st.write("Please upload a video file.")

if __name__ == "__main__":
    main()