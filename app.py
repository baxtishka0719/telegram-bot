from flask import Flask, request
import requests
import yt_dlp
import os

TOKEN = "8879492437:AAHondmiPES1UjNmmp7RzogThoID3VgLcio"
BOT_URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data and 'message' in data:
        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', '')

        if text == '/start':
            send_message(chat_id, "Salom! Menga YouTube, TikTok yoki Instagram havolasini yuboring, video yuklab beraman.")
        elif text.startswith('http'):
            send_message(chat_id, "Video yuklanmoqda, biroz kuting...")
            download_and_send(chat_id, text)
        else:
            send_message(chat_id, "Menga video havolasini (link) yuboring.")

    return {'ok': True}

def download_and_send(chat_id, url):
    filename = f"/tmp/{chat_id}_video.mp4"
    try:
        ydl_opts = {
            'outtmpl': filename,
            'format': 'best[ext=mp4]/best',
            'quiet': True,
            'noplaylist': True,
            'max_filesize': 50 * 1024 * 1024,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if not os.path.exists(filename):
            send_message(chat_id, "Video yuklab bo'lmadi (fayl hajmi 50 MB dan katta bo'lishi mumkin).")
            return

        with open(filename, 'rb') as video_file:
            requests.post(f"{BOT_URL}/sendVideo",
                data={'chat_id': chat_id},
                files={'video': video_file},
                timeout=120
            )

    except yt_dlp.utils.DownloadError:
        send_message(chat_id, "Bu havoladan video yuklab bo'lmadi. Havolani tekshirib, qayta yuboring.")
    except Exception as e:
        send_message(chat_id, f"Xato yuz berdi: {str(e)}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

def send_message(chat_id, text):
    requests.post(f"{BOT_URL}/sendMessage", json={
        'chat_id': chat_id,
        'text': text
    })

@app.route('/')
def home():
    return "Bot ishlayapti!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
