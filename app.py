from flask import Flask, request
import requests
import yt_dlp
import os

TOKEN = os.environ.get("BOT_TOKEN")
BOT_URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)
url_store = {}
counter = 0

@app.route('/webhook', methods=['POST'])
def webhook():
    global counter
    data = request.get_json()

    if data and 'message' in data:
        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', '')

        if text == '/start':
            send_message(chat_id, "Salom! Menga YouTube, TikTok yoki Instagram havolasini yuboring.")
        elif text.startswith('http'):
            counter += 1
            key = str(counter)
            url_store[key] = text
            send_link_options(chat_id, key)
        else:
            send_message(chat_id, "Menga video havolasini (link) yuboring.")

    elif data and 'callback_query' in data:
        handle_callback(data['callback_query'])

    return {'ok': True}

def send_link_options(chat_id, key):
    requests.post(f"{BOT_URL}/sendMessage", json={
        'chat_id': chat_id,
        'text': "Nima kerak?",
        'reply_markup': {
            'inline_keyboard': [[
                {'text': 'Video', 'callback_data': f'video|{key}'},
                {'text': 'Audio', 'callback_data': f'audio|{key}'},
                {'text': 'Malumot', 'callback_data': f'info|{key}'}
            ]]
        }
    })

def handle_callback(callback):
    chat_id = callback['message']['chat']['id']
    data_str = callback['data']
    action, key = data_str.split('|', 1)
    url = url_store.get(key)

    requests.post(f"{BOT_URL}/answerCallbackQuery", json={
        'callback_query_id': callback['id']
    })

    if not url:
        send_message(chat_id, "Havola muddati tugagan, qaytadan yuboring.")
        return

    if action == 'video':
        send_message(chat_id, "Video yuklanmoqda, biroz kuting...")
        download_and_send(chat_id, url, mode='video')
    elif action == 'audio':
        send_message(chat_id, "Audio ajratilmoqda, biroz kuting...")
        download_and_send(chat_id, url, mode='audio')
    elif action == 'info':
        send_song_info(chat_id, url)

def download_and_send(chat_id, url, mode='video'):
    filename = f"/tmp/{chat_id}_file"
    try:
        if mode == 'video':
            ydl_opts = {
                'outtmpl': filename + '.mp4',
                'format': 'best[ext=mp4]/best',
                'quiet': True,
                'noplaylist': True,
                'max_filesize': 50 * 1024 * 1024,
            }
        else:
            ydl_opts = {
                'outtmpl': filename + '.%(ext)s',
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
                'quiet': True,
                'noplaylist': True,
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        final_file = filename + ('.mp4' if mode == 'video' else '.mp3')

        if not os.path.exists(final_file):
            send_message(chat_id, "Yuklab bolmadi (fayl hajmi katta bolishi mumkin yoki havola qollab-quvvatlanmaydi).")
            return

        endpoint = 'sendVideo' if mode == 'video' else 'sendAudio'
        field = 'video' if mode == 'video' else 'audio'

        with open(final_file, 'rb') as f:
            requests.post(f"{BOT_URL}/{endpoint}",
                data={'chat_id': chat_id},
                files={field: f},
                timeout=180
            )
        os.remove(final_file)

    except yt_dlp.utils.DownloadError:
        send_message(chat_id, "Bu havoladan yuklab bolmadi. Havolani tekshirib, qayta yuboring.")
    except Exception as e:
        send_message(chat_id, f"Xato yuz berdi: {str(e)}")

def send_song_info(chat_id, url):
    try:
        ydl_opts = {'quiet': True, 'noplaylist': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        title = info.get('title', 'Nomalum')
        uploader = info.get('uploader', 'Nomalum')
        duration = info.get('duration', 0)

        minutes = duration // 60
        seconds = duration % 60

        result = f"Nomi: {title}\nMuallif: {uploader}\nDavomiyligi: {minutes}:{seconds:02d}"
        send_message(chat_id, result)

    except Exception as e:
        send_message(chat_id, f"Malumot topilmadi: {str(e)}")

def send_message(chat_id, text):
    requests.post(f"{BOT_URL}/sendMessage", json={
        'chat_id': chat_id,
        'text': text
    })

@app.route('/')
def home():
    token_status = "TOKEN BOR" if TOKEN else "TOKEN YOQ"
    return "Bot ishlayapti! " + token_status

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
