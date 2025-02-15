import pandas as pd
import time
import json
import os
from flask import Flask, render_template, request, jsonify, Response, send_file
import speech_recognition as sr
import threading
import queue
from datetime import datetime
import io

app = Flask(__name__)

# Configuration
EEG_CSV_PATH = os.path.join('static', 'eeg_data.csv')

# Global variables
recognizer = sr.Recognizer()
is_listening = False
latest_eeg_data = {"time": None, "value": None}
recorded_transcripts = []
speech_queue = queue.Queue()
recording_lock = threading.Lock()
eeg_lock = threading.Lock()

# EEG Data Generator
def generate_eeg_data():
    global latest_eeg_data
    eeg_df = pd.read_csv(EEG_CSV_PATH)
    for _, row in eeg_df.iterrows():
        timestamp = row['timestamp']
        eeg_value = row['value']
        with eeg_lock:
            latest_eeg_data = {"time": timestamp, "value": eeg_value}
        yield f"data: {json.dumps({'time': timestamp, 'value': eeg_value})}\n\n"
        time.sleep(1)

# Live Transcription Handler
def listen_and_transcribe():
    global is_listening
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source)
        while is_listening:
            try:
                audio = recognizer.listen(source, timeout=1)
                text = recognizer.recognize_google(audio)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                with eeg_lock:
                    current_eeg = latest_eeg_data.copy()
                
                entry = {
                    "timestamp": timestamp,
                    "text": text,
                    "eeg_timestamp": current_eeg["time"],
                    "eeg_value": current_eeg["value"]
                }
                
                with recording_lock:
                    recorded_transcripts.append(entry)
                
                speech_queue.put({
                    "time": timestamp,
                    "text": text
                })
                    
            except (sr.WaitTimeoutError, sr.UnknownValueError):
                pass
            except sr.RequestError as e:
                print(f"Speech recognition error: {e}")

# SSE Generator for Live Transcripts
def generate_live_transcripts():
    while True:
        entry = speech_queue.get()
        yield f"data: {json.dumps(entry)}\n\n"

# Flask Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/eeg_stream')
def eeg_stream():
    return Response(generate_eeg_data(), mimetype='text/event-stream')

@app.route('/live_transcripts')
def live_transcripts():
    return Response(generate_live_transcripts(), mimetype='text/event-stream')

@app.route('/start_listening', methods=['POST'])
def start_listening():
    global is_listening
    if not is_listening:
        is_listening = True
        threading.Thread(target=listen_and_transcribe).start()
    return jsonify({"status": "Listening started"})

@app.route('/stop_listening', methods=['POST'])
def stop_listening():
    global is_listening
    is_listening = False
    return jsonify({"status": "Listening stopped"})

@app.route('/save_transcription')
def save_transcription():
    with recording_lock:
        data = recorded_transcripts.copy()
    
    if not data:
        return jsonify({"error": "No data to save"}), 400
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

if __name__ == '__main__':
    app.run(debug=True, threaded=True)