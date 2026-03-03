import datetime
import logging
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

import matplotlib.pyplot as plt
import speech_recognition as sr
from fpdf import FPDF
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from openai import OpenAI

from entzun.adapters.openai_client import OpenAIMeetingSummarizer, OpenAISentimentAnalyzer
from entzun.adapters.transcription import GoogleTranscriptionAdapter, WhisperTranscriptionAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("copilot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


API_KEY_ENV_VAR = "OPENAI_API_KEY"
API_KEY = os.getenv(API_KEY_ENV_VAR, "")


class EntzunApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Entzun - Meeting Sentiment & Summary")
        self.root.geometry("1100x750")

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        logger.info("=== Starting Entzun application ===")

        if not API_KEY:
            logger.error("OPENAI_API_KEY not configured in environment.")
            messagebox.showerror(
                "Configuration error",
                "OPENAI_API_KEY is not configured.\n"
                "Set the OPENAI_API_KEY environment variable "
                "or use a non-versioned .env file.",
            )
            sys.exit(1)

        try:
            self.client = OpenAI(api_key=API_KEY)
            logger.info("OpenAI client initialised correctly")
        except Exception as exc:
            logger.error("Error initialising OpenAI client: %s", exc)
            messagebox.showerror("Error", f"Error connecting to OpenAI:\n{exc}")
            sys.exit(1)

        self.is_listening = False
        self.transcript_full = ""
        self.summary_text = ""
        self.sentiment_history: list[int] = []
        self.recognizer = sr.Recognizer()
        self.current_language = "es-ES"
        self.recent_context: list[str] = []
        self.max_context_items = 5
        self.final_summary = ""
        self.use_whisper_api = False
        self.audio_queue: queue.Queue[sr.AudioData] = queue.Queue()
        self.processing_thread: threading.Thread | None = None

        self.sentiment_analyzer = OpenAISentimentAnalyzer(
            client=self.client,
            recent_context=self.recent_context,
            max_context_items=self.max_context_items,
        )
        self.meeting_summarizer = OpenAIMeetingSummarizer(client=self.client)
        self.google_transcriber = GoogleTranscriptionAdapter(self.recognizer)
        self.whisper_transcriber = WhisperTranscriptionAdapter(self.client)

        try:
            self.mic = sr.Microphone()
            logger.info("Detected microphone: %s", sr.Microphone.list_microphone_names())
        except Exception as exc:
            logger.error("Error detecting microphone: %s", exc)
            messagebox.showerror(
                "Error",
                f"No microphone detected:\n{exc}\n\nMake sure a microphone is connected.",
            )

        frame_left = tk.Frame(root)
        frame_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        frame_right = tk.Frame(root, width=400)
        frame_right.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

        tk.Label(
            frame_left,
            text="👂 Live Transcription:",
            font=("Arial", 10, "bold"),
        ).pack(anchor="w")
        self.txt_transcript = scrolledtext.ScrolledText(frame_left, height=10)
        self.txt_transcript.pack(fill=tk.BOTH, expand=True, pady=5)

        tk.Label(
            frame_left,
            text="🧠 Smart Summary:",
            font=("Arial", 10, "bold"),
            fg="blue",
        ).pack(anchor="w")
        self.txt_summary = scrolledtext.ScrolledText(frame_left, height=10, bg="#f0f8ff")
        self.txt_summary.pack(fill=tk.BOTH, expand=True, pady=5)

        tk.Label(
            frame_right,
            text="🌡️ Sentiment Thermometer",
            font=("Arial", 10, "bold"),
        ).pack(pady=5)
        self.fig, self.ax = plt.subplots(figsize=(4, 3), dpi=100)
        self.ax.set_ylim(-10, 10)
        self.ax.axhline(y=0, color="gray", linestyle="--")
        (self.line,) = self.ax.plot([], [], "r-")
        self.canvas = FigureCanvasTkAgg(self.fig, master=frame_right)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        tk.Label(
            frame_right,
            text="Transcription Service",
            font=("Arial", 10, "bold"),
        ).pack(pady=5)

        self.transcription_var = tk.StringVar(value="google")

        frame_transcription = tk.Frame(frame_right)
        frame_transcription.pack(fill="x", pady=5)

        rb_google = tk.Radiobutton(
            frame_transcription,
            text="Google (Gratis)",
            variable=self.transcription_var,
            value="google",
            command=self.change_transcription_service,
        )
        rb_google.pack(side=tk.LEFT, padx=5)

        rb_whisper = tk.Radiobutton(
            frame_transcription,
            text="Whisper API (Pago)",
            variable=self.transcription_var,
            value="whisper",
            command=self.change_transcription_service,
        )
        rb_whisper.pack(side=tk.LEFT, padx=5)

        tk.Label(frame_right, text="Language", font=("Arial", 10, "bold")).pack(pady=5)

        frame_lang = tk.Frame(frame_right)
        frame_lang.pack(fill="x", pady=5)

        self.lang_var = tk.StringVar(value="es")

        rb_spanish = tk.Radiobutton(
            frame_lang,
            text="Spanish",
            variable=self.lang_var,
            value="es",
            command=self.change_language,
        )
        rb_spanish.pack(side=tk.LEFT, padx=10)

        rb_english = tk.Radiobutton(
            frame_lang,
            text="English",
            variable=self.lang_var,
            value="en",
            command=self.change_language,
        )
        rb_english.pack(side=tk.LEFT, padx=10)

        rb_auto = tk.Radiobutton(
            frame_lang,
            text="Auto",
            variable=self.lang_var,
            value="auto",
            command=self.change_language,
        )
        rb_auto.pack(side=tk.LEFT, padx=10)

        self.btn_start = tk.Button(
            frame_right,
            text="[PLAY] START",
            command=self.toggle_listening,
            bg="#ccffcc",
            height=2,
        )
        self.btn_start.pack(fill="x", pady=5)

        self.btn_summary = tk.Button(
            frame_right,
            text="[SUMMARY] FINAL SUMMARY",
            command=self.generar_resumen_final,
            bg="#87ceeb",
            height=2,
        )
        self.btn_summary.pack(fill="x", pady=5)

        self.btn_export = tk.Button(
            frame_right,
            text="[PDF] SAVE PDF",
            command=self.generar_reporte,
            bg="#ffd700",
            height=2,
        )
        self.btn_export.pack(fill="x", pady=5)

        tk.Label(
            frame_right,
            text="Estado del Sistema",
            font=("Arial", 10, "bold"),
        ).pack(pady=5)
        self.txt_status = scrolledtext.ScrolledText(
            frame_right,
            height=8,
            bg="#f5f5f5",
            fg="#333",
        )
        self.txt_status.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_status("[OK] System started correctly")
        microphone_names = sr.Microphone.list_microphone_names()
        selected_mic = microphone_names[0] if microphone_names else "Not detected"
        self.log_status(f"[MIC] Microphone: {selected_mic}")
        self.log_status("[WAIT] Press START to begin")

        logger.info("UI initialised")

    def change_transcription_service(self) -> None:
        service = self.transcription_var.get()
        self.use_whisper_api = service == "whisper"

        service_names = {
            "google": "Google Speech (Free)",
            "whisper": "OpenAI Whisper API (Paid, Legal usage)",
        }

        logger.info("Transcription service changed to: %s", service_names[service])
        self.log_status(f"[SERVICE] {service_names[service]}")

        if self.use_whisper_api:
            self.log_status("[INFO] Whisper: ~$0.006/min (~$0.36/hour)")

    def change_language(self) -> None:
        self.current_language = self.lang_var.get()
        lang_names = {
            "es": "Spanish",
            "en": "English",
            "auto": "Automatic detection",
        }
        logger.info(
            "Language changed to: %s",
            lang_names.get(self.current_language, self.current_language),
        )
        self.log_status(
            f"[LANG] Language: {lang_names.get(self.current_language, self.current_language)}",
        )

    def transcribe_with_google(self, audio: sr.AudioData) -> str:
        google_lang = {
            "es": "es-ES",
            "en": "en-US",
            "auto": None,
        }.get(self.current_language, "es-ES")
        return self.google_transcriber.transcribe(audio, google_lang)

    def transcribe_with_whisper(self, audio: sr.AudioData) -> str:
        whisper_lang = self.lang_var.get()
        return self.whisper_transcriber.transcribe(audio, whisper_lang)

    def log_status(self, message: str) -> None:
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.txt_status.insert(tk.END, f"[{timestamp}] {message}\n")
        self.txt_status.see(tk.END)
        message_log = message.encode("ascii", "ignore").decode("ascii")
        logger.info(message_log)

    def analizar_texto(self, texto_nuevo: str) -> tuple[int, str]:
        try:
            logger.info(
                "Analysing text: %s... (context: %s sentences)",
                texto_nuevo[:50],
                len(self.recent_context),
            )
            self.log_status("[AI] Analysing with AI...")
            score, resumen = self.sentiment_analyzer.analyze(texto_nuevo, self.recent_context)
            if resumen:
                self.log_status(f"[OK] Analysis completed (Score: {score})")
            return score, resumen
        except Exception as exc:
            logger.error("AI error: %s", exc)
            self.log_status(f"[ERROR] Error analysing: {str(exc)[:50]}")
            return 0, "Error while analysing."

    def update_graph(self, new_score: int) -> None:
        self.sentiment_history.append(new_score)
        x_data = range(len(self.sentiment_history))

        self.line.set_data(x_data, self.sentiment_history)
        self.ax.set_xlim(0, max(10, len(self.sentiment_history)))

        if len(self.sentiment_history) > 3:
            window = self.sentiment_history[-3:]
            average = sum(window) / len(window)
        else:
            average = float(new_score)
        color = "green" if average > 0 else "red"
        self.line.set_color(color)

        self.canvas.draw()

    def listen_loop(self) -> None:
        logger.info("Iniciando loop de escucha")
        self.log_status("[MIC] Ajustando ruido ambiente...")

        try:
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                self.log_status("[OK] Microfono listo. Habla ahora...")
                logger.info("Microfono configurado, esperando audio")

                while self.is_listening:
                    try:
                        self.log_status("[LISTEN] Escuchando...")

                        self.recognizer.energy_threshold = 300
                        self.recognizer.dynamic_energy_threshold = True

                        audio = self.recognizer.listen(
                            source,
                            phrase_time_limit=10,
                            timeout=5,
                        )

                        audio_data = audio.get_raw_data()
                        if len(audio_data) < 1000:
                            logger.debug("Audio demasiado corto, ignorando")
                            continue

                        logger.info("Audio capturado, transcribiendo...")

                        if self.use_whisper_api:
                            self.log_status("Transcribiendo con Whisper API...")
                            text = self.transcribe_with_whisper(audio)
                        else:
                            self.log_status("Transcribiendo con Google Speech...")
                            text = self.transcribe_with_google(audio)

                        logger.info("Texto transcrito: %s", text)

                        if text and text.strip() and len(text.strip()) > 2:
                            self.transcript_full += text + "\n"

                            def append_transcript(value: str = text) -> None:
                                self.txt_transcript.insert(tk.END, f"- {value}\n")

                            self.root.after(0, append_transcript)
                            self.log_status(f"[OK] Transcrito: {text[:30]}...")

                            score, resumen = self.analizar_texto(text)
                            if resumen and resumen != "Error analizando.":
                                self.summary_text += f"- {resumen}\n"

                                def append_summary(value: str = resumen) -> None:
                                    self.txt_summary.insert(tk.END, f"• {value}\n")

                                def update_graph_callback(value: int = score) -> None:
                                    self.update_graph(value)

                                self.root.after(0, append_summary)
                                self.root.after(0, update_graph_callback)
                        else:
                            logger.debug("Texto vacio o muy corto, ignorando")
                            self.log_status("[SKIP] Texto muy corto, ignorado")

                    except sr.WaitTimeoutError:
                        logger.debug("Timeout esperando audio")
                    except sr.UnknownValueError:
                        logger.debug("No se pudo entender el audio")
                    except sr.RequestError as exc:
                        logger.error("Error de conexion con Google Speech: %s", exc)
                        self.log_status("[ERROR] Error de conexion a Google")
                    except Exception as exc:
                        logger.error("Error en listen_loop: %s", exc)
                        self.log_status(f"[ERROR] Error: {str(exc)[:40]}")

        except Exception as exc:
            logger.error("Error fatal en microfono: %s", exc)
            self.log_status(f"[ERROR] Error de microfono: {str(exc)[:40]}")
            messagebox.showerror("Error", f"Error de microfono:\n{exc}")

    def processing_loop(self) -> None:
        logger.info("Iniciando loop de procesamiento de audio")

        while self.is_listening or not self.audio_queue.empty():
            try:
                audio = self.audio_queue.get(timeout=1)

                logger.info("Procesando audio de la cola...")
                self.log_status("Transcribiendo...")

                if self.use_whisper_api:
                    text = self.transcribe_with_whisper(audio)
                else:
                    text = self.transcribe_with_google(audio)

                logger.info("Texto transcrito: %s", text)

                if text and text.strip() and len(text.strip()) > 2:
                    self.transcript_full += text + "\n"

                    def append_transcript(value: str = text) -> None:
                        self.txt_transcript.insert(tk.END, f"- {value}\n")

                    self.root.after(0, append_transcript)
                    self.log_status(f"[OK] Transcrito: {text[:30]}...")

                    score, resumen = self.analizar_texto(text)
                    if resumen and resumen != "Error analizando.":
                        self.summary_text += f"- {resumen}\n"

                        def append_summary(value: str = resumen) -> None:
                            self.txt_summary.insert(tk.END, f"• {value}\n")

                        def update_graph_callback(value: int = score) -> None:
                            self.update_graph(value)

                        self.root.after(0, append_summary)
                        self.root.after(0, update_graph_callback)
                else:
                    logger.debug("Texto vacio o muy corto, ignorando")
                    self.log_status("[SKIP] Texto muy corto, ignorado")

                self.audio_queue.task_done()

            except queue.Empty:
                continue
            except Exception as exc:
                logger.error("Error en processing_loop: %s", exc)
                self.log_status(f"[ERROR] Error procesando: {str(exc)[:40]}")

        logger.info("Loop de procesamiento finalizado")

    def on_closing(self) -> None:
        logger.info("Cerrando aplicacion...")
        if self.is_listening:
            self.is_listening = False
            logger.info("Deteniendo grabacion...")
            if self.processing_thread and self.processing_thread.is_alive():
                logger.info("Esperando a que termine el procesamiento...")
                self.processing_thread.join(timeout=5)

        self.root.quit()
        self.root.destroy()
        logger.info("Aplicacion cerrada correctamente")

    def toggle_listening(self) -> None:
        if not self.is_listening:
            logger.info("Usuario presiono INICIAR")
            self.is_listening = True
            self.btn_start.config(text="[STOP] DETENER", bg="#ff9999")
            self.log_status("[START] Grabacion iniciada")

            threading.Thread(target=self.listen_loop, daemon=True).start()
            self.processing_thread = threading.Thread(
                target=self.processing_loop,
                daemon=True,
            )
            self.processing_thread.start()
            logger.info("Threads de captura y procesamiento iniciados")
        else:
            logger.info("Usuario presiono DETENER")
            self.is_listening = False
            self.btn_start.config(text="[PLAY] INICIAR", bg="#ccffcc")
            self.log_status("[STOP] Grabacion detenida")
            self.log_status("[WAIT] Procesando audio restante...")

    def generar_resumen_final(self) -> None:
        if not self.transcript_full or not self.transcript_full.strip():
            messagebox.showwarning("Aviso", "No hay transcripción para resumir.")
            return

        logger.info("Generando resumen final de la reunion completa")
        self.log_status("[SUMMARY] Generando resumen final...")

        try:
            num_frases = len(
                [f for f in self.transcript_full.split("\n") if f.strip()],
            )
            sentimiento_promedio = (
                sum(self.sentiment_history) / len(self.sentiment_history)
                if self.sentiment_history
                else 0
            )

            self.final_summary = self.meeting_summarizer.summarize_full(
                transcript=self.transcript_full,
                avg_sentiment=sentimiento_promedio,
                num_utterances=num_frases,
            )
            logger.info("Resumen final generado correctamente")

            ventana_resumen = tk.Toplevel(self.root)
            ventana_resumen.title("Resumen Ejecutivo de la Reunión")
            ventana_resumen.geometry("700x600")

            tk.Label(
                ventana_resumen,
                text="Resumen Ejecutivo",
                font=("Arial", 14, "bold"),
            ).pack(pady=10)

            texto_resumen = scrolledtext.ScrolledText(
                ventana_resumen,
                wrap=tk.WORD,
                font=("Arial", 10),
            )
            texto_resumen.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            texto_resumen.insert(tk.END, self.final_summary)
            texto_resumen.config(state=tk.DISABLED)

            btn_cerrar = tk.Button(
                ventana_resumen,
                text="Cerrar",
                command=ventana_resumen.destroy,
                bg="#cccccc",
            )
            btn_cerrar.pack(pady=10)

            self.log_status("[OK] Resumen final generado")

        except Exception as exc:
            logger.error("Error al generar resumen final: %s", exc)
            self.log_status(
                f"[ERROR] Error al generar resumen: {str(exc)[:40]}",
            )
            messagebox.showerror(
                "Error",
                f"Error al generar resumen:\n{exc}",
            )

    def generar_reporte(self) -> None:
        logger.info("Generando reporte PDF")
        self.log_status("[PDF] Generando reporte...")

        if not self.transcript_full:
            logger.warning("No hay datos para generar reporte")
            messagebox.showwarning("Aviso", "No hay datos para guardar.")
            return

        try:
            self.fig.savefig("temp_graph.png", dpi=150, bbox_inches="tight")
            logger.info("Grafico guardado como temp_graph.png")

            pdf = FPDF()
            pdf.add_page()

            pdf.set_font("Arial", "B", 18)
            pdf.cell(0, 15, txt="Reporte de Reunion", ln=1, align="C")
            pdf.set_font("Arial", "", 12)
            pdf.cell(
                0,
                8,
                txt=datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                ln=1,
                align="C",
            )
            pdf.ln(5)

            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, txt="Grafico de Sentimiento", ln=1)
            pdf.ln(2)

            pdf.image("temp_graph.png", x=30, y=pdf.get_y(), w=150)
            pdf.ln(95)

            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, txt="Resumen Ejecutivo", ln=1)
            pdf.ln(2)

            pdf.set_font("Arial", "", 11)

            if self.final_summary:
                try:
                    resumen_limpio = self.final_summary.encode(
                        "latin-1",
                        "replace",
                    ).decode("latin-1")
                    pdf.multi_cell(0, 6, resumen_limpio)
                except Exception:
                    pdf.multi_cell(0, 6, self.final_summary)
            elif self.summary_text:
                pdf.set_font("Arial", "I", 10)
                pdf.cell(
                    0,
                    6,
                    txt=("(Resumen fragmentado - usa RESUMEN FINAL " "para un analisis completo)"),
                    ln=1,
                )
                pdf.ln(2)
                pdf.set_font("Arial", "", 11)
                try:
                    resumen_limpio = self.summary_text.encode(
                        "latin-1",
                        "replace",
                    ).decode("latin-1")
                    pdf.multi_cell(0, 6, resumen_limpio)
                except Exception:
                    pdf.multi_cell(0, 6, self.summary_text)
            else:
                pdf.cell(0, 6, txt="No hay resumen disponible.", ln=1)

            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, txt="Transcripcion Completa", ln=1)
            pdf.ln(2)

            pdf.set_font("Arial", "", 10)
            if self.transcript_full:
                try:
                    transcript_limpio = self.transcript_full.encode(
                        "latin-1",
                        "replace",
                    ).decode("latin-1")
                    pdf.multi_cell(0, 5, transcript_limpio)
                except Exception:
                    pdf.multi_cell(0, 5, self.transcript_full)

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_pdf = f"Reunion_{timestamp}.pdf"
            filename_txt = f"Transcripcion_{timestamp}.txt"

            pdf.output(filename_pdf)
            logger.info("PDF guardado: %s", filename_pdf)

            with open(filename_txt, "w", encoding="utf-8") as file:
                file.write(self.transcript_full)
            logger.info("Transcripcion guardada: %s", filename_txt)

            self.log_status(f"[OK] Guardado: {filename_pdf}")
            messagebox.showinfo(
                "Exito",
                f"Archivos guardados:\n{filename_pdf}\n{filename_txt}",
            )

        except Exception as exc:
            logger.error("Error al generar reporte: %s", exc)
            self.log_status(f"[ERROR] Error al guardar: {str(exc)[:40]}")
            messagebox.showerror(
                "Error",
                f"Error al generar reporte:\n{exc}",
            )
