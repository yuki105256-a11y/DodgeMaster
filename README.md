Dodge Master (Cartoon) - Colab instructions

Files:
- main.py
- buildozer.spec
- assets/ (player.png, enemy.png, background.png, icon.png, explosion.wav)

How to use with the MagnoEfren Colab notebook:
1) Upload the ZIP to Colab and unzip into working dir.
2) Ensure the notebook installs buildozer, python-for-android, and required packages.
3) In the notebook, cd to the project folder and run:
     !yes | buildozer android debug
4) After build finishes, download the generated APK from the notebook file browser.

Notes:
- The assets are cartoon-style placeholders; replace them with your own art if desired.
- Highscore is saved to the app's user_data_dir on Android.
- If you want image loading, pillow is included in requirements so CoreImage can load PNGs.
