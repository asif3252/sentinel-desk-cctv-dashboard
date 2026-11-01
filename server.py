"""Sentinel Desk: loopback-only CCTV dashboard and optional local inference."""
import csv
import importlib.util
import ipaddress
import json
import mimetypes
import secrets
import socket
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parent
TOKEN = secrets.token_urlsafe(32)
LOCK = threading.RLock()
STATE = {'configured': False, 'status': 'not_configured', 'message': 'Add your recorder to get started.', 'channel': 1, 'fps': 0, 'frames': 0, 'events': [], 'running': False, 'zone': [0.15, 0.15, 0.7, 0.7], 'dwell': 30, 'persistence': 2}
CONFIG = {}
FRAME = None
STOP = threading.Event()
WORKER = None


def validate_config(data):
    host = str(data.get('host', '')).strip()
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        raise ValueError('Enter an IPv4 LAN address, for example 192.168.1.100.')
    if address.version != 4 or address.is_multicast or address.is_unspecified or address.is_loopback or address.is_reserved:
        raise ValueError('Enter the recorder IPv4 address on your LAN.')
    port = int(data.get('port', 554))
    channels = int(data.get('channels', 25))
    if not 1 <= port <= 65535 or not 1 <= channels <= 32:
        raise ValueError('Port must be 1–65535 and channel count 1–32.')
    user = str(data.get('username', '')).strip()
    password = str(data.get('password', ''))
    if not user or not password:
        raise ValueError('Enter both the NVR username and password.')
    return {'host': host, 'port': port, 'channels': channels, 'username': user, 'password': password, 'name': str(data.get('name', 'Main recorder'))[:80] or 'Main recorder', 'subtype': int(data.get('subtype', 1)) if int(data.get('subtype', 1)) in (0, 1) else 1}


def rtsp_url(config, channel):
    return f'rtsp://{quote(config["username"], safe="")}:{quote(config["password"], safe="")}@{config["host"]}:{config["port"]}/cam/realmonitor?channel={channel}&subtype={config["subtype"]}'


class Rules:
    def __init__(self, persistence, dwell):
        self.persistence, self.dwell, self.people = persistence, dwell, {}

    def update(self, now, ids):
        self.people = {k: v for k, v in self.people.items() if k in ids}
        output = []
        for identity in ids:
            state = self.people.setdefault(identity, {'start': now, 'intrusion': -1e9, 'loitering': -1e9})
            elapsed = now - state['start']
            for kind, threshold in [('intrusion', self.persistence), ('loitering', self.dwell)]:
                if elapsed >= threshold and now - state[kind] >= 60:
                    state[kind] = now
                    output.append((identity, kind, elapsed))
        return output


def dependencies():
    return {name: importlib.util.find_spec(name) is not None for name in ['cv2', 'ultralytics']}


def public_state():
    with LOCK:
        result = dict(STATE)
        result['events'] = [dict(e) for e in STATE['events']]
        result['recorder'] = {k: v for k, v in CONFIG.items() if k not in ('username', 'password')}
        result['dependencies'] = dependencies()
        result['has_frame'] = FRAME is not None
        return result


def record_event(cv2, frame, channel, identity, kind, elapsed):
    stamp = datetime.now().astimezone()
    event = {'id': secrets.token_hex(8), 'time': stamp.isoformat(), 'channel': channel, 'track_id': identity, 'type': kind, 'dwell': round(elapsed, 1), 'acknowledged': False}
    folder = ROOT / 'events'
    folder.mkdir(exist_ok=True)
    filename = event['id'] + '.jpg'
    if not cv2.imwrite(str(folder / filename), frame):
        raise OSError('Snapshot could not be saved')
    event['snapshot'] = filename
    with LOCK:
        STATE['events'].insert(0, event)
        STATE['events'] = STATE['events'][:200]
    log = folder / 'events.csv'
    new = not log.exists()
    with log.open('a', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        if new:
            writer.writerow(['time', 'channel', 'event', 'track_id', 'dwell_seconds', 'snapshot'])
        writer.writerow([event['time'], channel, kind, identity, event['dwell'], filename])


def monitor(config, channel, zone, persistence, dwell):
    global FRAME
    cap = None
    try:
        import os
        os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;tcp'
        os.environ['OPENCV_LOG_LEVEL'] = 'SILENT'
        import cv2
        from ultralytics import YOLO
        with LOCK:
            STATE.update(status='loading_model', message='Loading YOLO11n. First use may download model weights.')
        model = YOLO(str(ROOT / 'yolo11n.pt'))
        if STOP.is_set():
            return
        with LOCK:
            STATE.update(status='connecting', message='Opening the selected camera stream…')
        cap = cv2.VideoCapture(rtsp_url(config, channel), cv2.CAP_FFMPEG, [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000])
        rules = Rules(persistence, dwell)
        last = time.monotonic()
        while not STOP.is_set():
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError('stream')
            started = time.monotonic()
            h, w = frame.shape[:2]
            ratio = min(1, 960 / w)
            frame = cv2.resize(frame, (int(w * ratio), int(h * ratio)))
            h, w = frame.shape[:2]
            x, y, zw, zh = zone
            left, top, right, bottom = int(x*w), int(y*h), int((x+zw)*w), int((y+zh)*h)
            result = model.track(frame, persist=True, classes=[0], conf=0.4, imgsz=640, device='cpu', verbose=False, tracker='bytetrack.yaml')[0]
            inside = set()
            cv2.rectangle(frame, (left, top), (right, bottom), (40, 205, 210), 2)
            if result.boxes is not None and result.boxes.id is not None:
                for box, identity in zip(result.boxes.xyxy.cpu().tolist(), result.boxes.id.int().cpu().tolist()):
                    a, b, c, d = map(int, box)
                    if left <= (a+c)/2 <= right and top <= d <= bottom:
                        inside.add(identity)
                    cv2.rectangle(frame, (a,b), (c,d), (85,220,160), 2)
                    cv2.putText(frame, f'Person {identity}', (a,max(20,b)), 0, 0.6, (85,220,160), 2)
            now = time.monotonic()
            if now-last > 5:
                rules.people.clear()
            last = now
            for identity, kind, elapsed in rules.update(now, inside):
                record_event(cv2, frame, channel, identity, kind, elapsed)
            encoded, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if encoded:
                with LOCK:
                    FRAME = jpeg.tobytes()
                    STATE.update(status='monitoring', message='Detection is running on one camera.', fps=round(1/max(.001,now-started),1), frames=STATE['frames']+1)
    except Exception:
        with LOCK:
            STATE.update(status='error', message='Monitoring stopped. Check dependencies, model download, camera login, RTSP port, substream and output permissions.', fps=0)
    finally:
        if cap is not None:
            cap.release()
        with LOCK:
            STATE['running'] = False
            if STOP.is_set():
                STATE.update(status='ready', message='Monitoring stopped.', fps=0)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, code, payload, mime='application/json'):
        data = json.dumps(payload).encode() if mime == 'application/json' else payload
        self.send_response(code)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(data)

    def authorized_host(self):
        return self.headers.get('Host') in ('127.0.0.1:8765', 'localhost:8765')

    def do_GET(self):
        if not self.authorized_host():
            return self.reply(403, {'error': 'Use http://127.0.0.1:8765'})
        path = urlsplit(self.path).path
        if path == '/api/state':
            return self.reply(200, public_state())
        if path == '/api/session':
            return self.reply(200, {'token': TOKEN})
        if path == '/api/frame':
            with LOCK:
                frame = FRAME
            return self.reply(200, frame, 'image/jpeg') if frame else self.reply(404, {'error': 'No camera frame available'})
        if path == '/api/export':
            with LOCK:
                events = list(reversed(STATE['events']))
            import io
            output = io.StringIO(newline='')
            writer = csv.writer(output)
            writer.writerow(['time','channel','type','track_id','dwell_seconds','acknowledged'])
            for e in events:
                writer.writerow([e['time'],e['channel'],e['type'],e['track_id'],e['dwell'],e['acknowledged']])
            return self.reply(200, output.getvalue().encode('utf-8-sig'), 'text/csv; charset=utf-8')
        if path.startswith('/snapshots/'):
            name = path.rsplit('/',1)[-1]
            if len(name) != 20 or not name.endswith('.jpg') or any(c not in '0123456789abcdef' for c in name[:-4]):
                return self.reply(404, {'error':'Not found'})
            file = ROOT / 'events' / name
        else:
            file = ROOT / 'web' / ('index.html' if path == '/' else path.lstrip('/'))
        if not file.resolve().is_relative_to(ROOT.resolve()) or not file.is_file():
            return self.reply(404, {'error':'Not found'})
        if not path.startswith('/snapshots/') and not file.resolve().is_relative_to((ROOT/'web').resolve()):
            return self.reply(404, {'error':'Not found'})
        return self.reply(200, file.read_bytes(), mimetypes.guess_type(file.name)[0] or 'application/octet-stream')

    def do_POST(self):
        global CONFIG, WORKER, FRAME
        if not self.authorized_host() or self.headers.get('X-Session-Token') != TOKEN or self.headers.get('Origin') not in (None, 'http://127.0.0.1:8765', 'http://localhost:8765'):
            return self.reply(403, {'error':'Session check failed. Refresh the dashboard.'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 16384:
                raise ValueError('Invalid request size')
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError('Invalid request')
            path = urlsplit(self.path).path
            if path == '/api/config':
                config = validate_config(data)
                with LOCK:
                    if STATE['running']:
                        raise ValueError('Stop monitoring before changing the recorder.')
                    CONFIG = config
                    FRAME = None
                    STATE.update(configured=True, status='ready', message='Recorder configured. Test its port, then start a camera.', channel=1, frames=0, fps=0)
            elif path == '/api/test':
                with LOCK:
                    config = dict(CONFIG)
                if not config:
                    raise ValueError('Configure your recorder first.')
                try:
                    with socket.create_connection((config['host'], config['port']), timeout=3):
                        pass
                    return self.reply(200, {'message':'RTSP TCP port is reachable. Login and video decoding are verified only when monitoring starts.', 'reachable':True})
                except OSError:
                    return self.reply(200, {'message':'Could not reach the RTSP TCP port. Check IP, port and LAN connectivity.', 'reachable':False})
            elif path == '/api/start':
                with LOCK:
                    if not CONFIG:
                        raise ValueError('Configure your recorder first.')
                    if WORKER and WORKER.is_alive():
                        raise ValueError('A camera is already starting or running. Stop it first.')
                    if not all(dependencies().values()):
                        raise ValueError('Detection packages are missing. Run Install-Detection.ps1, then restart the dashboard.')
                    channel = int(data.get('channel',1))
                    dwell = float(data.get('dwell',30))
                    persistence = float(data.get('persistence',2))
                    zone = [float(x) for x in data.get('zone',STATE['zone'])]
                    if not 1 <= channel <= CONFIG['channels'] or not 3 <= dwell <= 3600 or not .5 <= persistence <= 60:
                        raise ValueError('Invalid channel or detection thresholds.')
                    if len(zone)!=4 or not all(0 <= x <= 1 for x in zone) or zone[2]<.02 or zone[3]<.02 or zone[0]+zone[2]>1.001 or zone[1]+zone[3]>1.001:
                        raise ValueError('Draw a valid detection zone.')
                    STOP.clear()
                    FRAME = None
                    STATE.update(running=True,status='starting',message='Starting local detection…',channel=channel,zone=zone,dwell=dwell,persistence=persistence,frames=0,fps=0)
                    WORKER = threading.Thread(target=monitor,args=(dict(CONFIG),channel,zone,persistence,dwell),daemon=True)
                    WORKER.start()
            elif path == '/api/stop':
                STOP.set()
                with LOCK:
                    if STATE['running']:
                        STATE.update(status='stopping', message='Stopping after the current camera operation…')
            elif path == '/api/ack':
                with LOCK:
                    for event in STATE['events']:
                        if event['id'] == data.get('id'):
                            event['acknowledged'] = True
            elif path == '/api/disconnect':
                with LOCK:
                    if WORKER and WORKER.is_alive():
                        raise ValueError('Stop monitoring and wait for it to finish first.')
                    CONFIG = {}
                    FRAME = None
                    STATE.update(configured=False,status='not_configured',message='Recorder disconnected. Credentials cleared from application configuration.',fps=0,frames=0)
            else:
                return self.reply(404, {'error':'Unknown action'})
            return self.reply(200, {'ok':True})
        except (ValueError,TypeError,KeyError,OverflowError):
            return self.reply(400, {'error': 'Check the recorder settings and channel, stop an active camera before reconfiguring, and install detection packages before starting.'})


if __name__ == '__main__':
    print('Sentinel Desk | http://127.0.0.1:8765 | Ctrl+C to stop', flush=True)
    server = ThreadingHTTPServer(('127.0.0.1',8765),Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        STOP.set()
    finally:
        server.server_close()
