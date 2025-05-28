from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

viewers = []

@app.get("/")
async def index():
    html = """
    <html>
    <head><title>📡 بث مباشر (صوت + صورة)</title></head>
    <body>
      <h2>📸 بث مباشر</h2>
      <video id="video" autoplay playsinline muted></video>
      <br/>
      <button id="btnMute">كتم الصوت</button>
      <button id="btnPause">إيقاف مؤقت</button>

      <script>
        const video = document.getElementById("video");
        const btnMute = document.getElementById("btnMute");
        const btnPause = document.getElementById("btnPause");

        let isMuted = true;
        let isPaused = false;

        // افتح اتصال ويب سوكت مع السيرفر
        const ws = new WebSocket("ws://localhost:8000/ws/stream");

        navigator.mediaDevices.getUserMedia({ video: true, audio: true }).then(stream => {
          video.srcObject = stream;
          video.muted = isMuted;

          // تحكم بالكتم
          btnMute.onclick = () => {
            isMuted = !isMuted;
            video.muted = isMuted;
            btnMute.textContent = isMuted ? "تشغيل الصوت" : "كتم الصوت";
          };

          // تحكم بالإيقاف المؤقت
          btnPause.onclick = () => {
            isPaused = !isPaused;
            if (isPaused) {
              btnPause.textContent = "استئناف البث";
            } else {
              btnPause.textContent = "إيقاف مؤقت";
            }
          };

          // ارسال الصور والفيديو
          const canvas = document.createElement("canvas");
          const ctx = canvas.getContext("2d");

          setInterval(() => {
            if (isPaused) return; // إذا الإيقاف مؤقت لا ترسل فريمات
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            ctx.drawImage(video, 0, 0);
            const imgData = canvas.toDataURL("image/jpeg");
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ type: "video", data: imgData }));
            }
          }, 100);  // 10 فريم/ثانية

          // إرسال الصوت مباشرة - تبسيط: يبقى الصوت من المصدر نفسه (muted أو unmuted)
          // ** لإرسال الصوت عبر WebSocket تعقيد أكثر ويتطلب ترميز ومعالجة، عادة WebRTC هو الأفضل.
          // هنا نكتفي بالصوت من الميكروفون في البث، والمشاهدين يسمعون الصوت بشكل مباشر من صفحة المشاهدة.

        });

        ws.onclose = () => {
          alert("تم قطع الاتصال بالسيرفر.");
        };
      </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


@app.get("/viewer")
async def viewer():
    html = """
    <html>
    <head><title>👀 مشاهدة</title></head>
    <body>
      <h2>👀 المشاهدة</h2>
      <img id="video" width="640" />
      <br/>
      <audio id="audio" autoplay controls></audio>
      <br/>
      <label>🎚️ مستوى الصوت:</label>
      <input type="range" id="volume" min="0" max="1" step="0.01" value="1" />
      <br/>
      <button id="btnAudio">🔇 إيقاف الصوت</button>
      <button id="btnPauseLive">⏸️ إيقاف البث المباشر</button>

      <script>
        const video = document.getElementById("video");
        const audio = document.getElementById("audio");
        const volumeSlider = document.getElementById("volume");
        const btnAudio = document.getElementById("btnAudio");
        const btnPauseLive = document.getElementById("btnPauseLive");

        let isMuted = false;
        let isPausedLive = false;

        const ws = new WebSocket("ws://localhost:8000/ws/viewer");

        ws.onmessage = event => {
          if (isPausedLive) return;  // لا تُحدث شيء إذا البث متوقف مؤقتًا

          const msg = JSON.parse(event.data);
          if (msg.type === "video") {
            video.src = msg.data;
          } else if (msg.type === "audio") {
            fetch(msg.data)
              .then(res => res.blob())
              .then(blob => {
                const url = URL.createObjectURL(blob);
                audio.src = url;
                if (!audio.paused) audio.play();
              });
          }
        };

        // تحكم بالصوت
        volumeSlider.oninput = () => {
          audio.volume = volumeSlider.value;
        };

        btnAudio.onclick = () => {
          isMuted = !isMuted;
          audio.muted = isMuted;
          btnAudio.textContent = isMuted ? "🔊 تشغيل الصوت" : "🔇 إيقاف الصوت";
        };

        btnPauseLive.onclick = () => {
          isPausedLive = !isPausedLive;
          btnPauseLive.textContent = isPausedLive ? "▶️ استئناف البث" : "⏸️ إيقاف البث المباشر";
        };

        // إعادة الاتصال تلقائيًا
        ws.onclose = () => {
          console.log("📡 إعادة الاتصال...");
          setTimeout(() => location.reload(), 2000);
        };
      </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


@app.websocket("/ws/stream")
async def stream_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            # إعادة الإرسال لكل المشاهدين
            for viewer in viewers:
                try:
                    await viewer.send_text(message)
                except:
                    pass
    except:
        await websocket.close()


@app.websocket("/ws/viewer")
async def viewer_ws(websocket: WebSocket):
    viewers.append(websocket)
    await websocket.accept()
    try:
        while True:
            await asyncio.sleep(1)
    except:
        viewers.remove(websocket)
        await websocket.close()
