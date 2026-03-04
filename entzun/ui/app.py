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
from dotenv import load_dotenv
from fpdf import FPDF
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from openai import OpenAI

from entzun.adapters.openai_client import OpenAIMeetingSummarizer, OpenAISentimentAnalyzer
from entzun.adapters.transcription import GoogleTranscriptionAdapter, WhisperTranscriptionAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("entzun.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


load_dotenv()
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
            command=self.generate_final_summary,
            bg="#87ceeb",
            height=2,
        )
        self.btn_summary.pack(fill="x", pady=5)

        self.btn_export = tk.Button(
            frame_right,
            text="[PDF] SAVE PDF",
            command=self.generate_report,
            bg="#ffd700",
            height=2,
        )
        self.btn_export.pack(fill="x", pady=5)

        tk.Label(
            frame_right,
            text="System Status",
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

    def analyze_text(self, new_text: str) -> tuple[int, str]:
        try:
            logger.info(
                "Analysing text: %s... (context: %s sentences)",
                new_text[:50],
                len(self.recent_context),
            )
            self.log_status("[AI] Analysing with AI...")
            score, summary = self.sentiment_analyzer.analyze(new_text, self.recent_context)
            if summary:
                self.log_status(f"[OK] Analysis completed (Score: {score})")
            return score, summary
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
        logger.info("Starting listening loop")
        self.log_status("[MIC] Adjusting ambient noise...")

        try:
            with self.mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                self.log_status("[OK] Microphone ready. You can speak now...")
                logger.info("Microphone configured, waiting for audio")

                while self.is_listening:
                    try:
                        self.log_status("[LISTEN] Listening...")

                        self.recognizer.energy_threshold = 300
                        self.recognizer.dynamic_energy_threshold = True

                        audio = self.recognizer.listen(
                            source,
                            phrase_time_limit=10,
                            timeout=5,
                        )

                        audio_data = audio.get_raw_data()
                        if len(audio_data) < 1000:
                            logger.debug("Audio too short, ignoring")
                            continue

                        logger.info("Audio captured, transcribing...")

                        if self.use_whisper_api:
                            self.log_status("Transcribing with Whisper API...")
                            text = self.transcribe_with_whisper(audio)
                        else:
                            self.log_status("Transcribing with Google Speech...")
                            text = self.transcribe_with_google(audio)

                        logger.info("Texto transcrito: %s", text)

                        if text and text.strip() and len(text.strip()) > 2:
                            self.transcript_full += text + "\n"

                            def append_transcript(value: str = text) -> None:
                                self.txt_transcript.insert(tk.END, f"- {value}\n")

                            self.root.after(0, append_transcript)
                            self.log_status(f"[OK] Transcribed: {text[:30]}...")

                            score, summary = self.analyze_text(text)
                            if summary and summary != "Error analizando.":
                                self.summary_text += f"- {summary}\n"

                                def append_summary(value: str = summary) -> None:
                                    self.txt_summary.insert(tk.END, f"• {value}\n")

                                def update_graph_callback(value: int = score) -> None:
                                    self.update_graph(value)

                                self.root.after(0, append_summary)
                                self.root.after(0, update_graph_callback)
                        else:
                            logger.debug("Empty or very short text, ignoring")
                            self.log_status("[SKIP] Very short text, skipped")

                    except sr.WaitTimeoutError:
                        logger.debug("Timeout waiting for audio")
                    except sr.UnknownValueError:
                        logger.debug("Audio could not be understood")
                    except sr.RequestError as exc:
                        logger.error("Connection error with Google Speech: %s", exc)
                        self.log_status("[ERROR] Connection error to Google")
                    except Exception as exc:
                        logger.error("Error in listen_loop: %s", exc)
                        self.log_status(f"[ERROR] Error: {str(exc)[:40]}")

        except Exception as exc:
            logger.error("Fatal microphone error: %s", exc)
            self.log_status(f"[ERROR] Microphone error: {str(exc)[:40]}")
            messagebox.showerror("Error", f"Microphone error:\n{exc}")

    def processing_loop(self) -> None:
        logger.info("Starting audio processing loop")

        while self.is_listening or not self.audio_queue.empty():
            try:
                audio = self.audio_queue.get(timeout=1)

                logger.info("Processing audio from queue...")
                self.log_status("Transcribing...")

                if self.use_whisper_api:
                    text = self.transcribe_with_whisper(audio)
                else:
                    text = self.transcribe_with_google(audio)

                logger.info("Transcribed text: %s", text)

                if text and text.strip() and len(text.strip()) > 2:
                    self.transcript_full += text + "\n"

                    def append_transcript(value: str = text) -> None:
                        self.txt_transcript.insert(tk.END, f"- {value}\n")

                    self.root.after(0, append_transcript)
                    self.log_status(f"[OK] Transcribed: {text[:30]}...")

                    score, summary = self.analyze_text(text)
                    if summary and summary != "Error analizando.":
                        self.summary_text += f"- {summary}\n"

                        def append_summary(value: str = summary) -> None:
                            self.txt_summary.insert(tk.END, f"• {value}\n")

                        def update_graph_callback(value: int = score) -> None:
                            self.update_graph(value)

                        self.root.after(0, append_summary)
                        self.root.after(0, update_graph_callback)
                else:
                    logger.debug("Empty or very short text, ignoring")
                    self.log_status("[SKIP] Very short text, skipped")

                self.audio_queue.task_done()

            except queue.Empty:
                continue
            except Exception as exc:
                logger.error("Error in processing_loop: %s", exc)
                self.log_status(f"[ERROR] Error processing: {str(exc)[:40]}")

        logger.info("Audio processing loop finished")

    def on_closing(self) -> None:
        logger.info("Closing application...")
        if self.is_listening:
            self.is_listening = False
            logger.info("Stopping recording...")
            if self.processing_thread and self.processing_thread.is_alive():
                logger.info("Waiting for processing to finish...")
                self.processing_thread.join(timeout=5)

        self.root.quit()
        self.root.destroy()
        logger.info("Application closed correctly")

    def toggle_listening(self) -> None:
        if not self.is_listening:
            logger.info("User pressed START")
            self.is_listening = True
            self.btn_start.config(text="[STOP] STOP", bg="#ff9999")
            self.log_status("[START] Recording started")

            threading.Thread(target=self.listen_loop, daemon=True).start()
            self.processing_thread = threading.Thread(
                target=self.processing_loop,
                daemon=True,
            )
            self.processing_thread.start()
            logger.info("Capture and processing threads started")
        else:
            logger.info("User pressed STOP")
            self.is_listening = False
            self.btn_start.config(text="[PLAY] START", bg="#ccffcc")
            self.log_status("[STOP] Recording stopped")
            self.log_status("[WAIT] Processing remaining audio...")

    def generate_final_summary(self) -> None:
        if not self.transcript_full or not self.transcript_full.strip():
            messagebox.showwarning("Warning", "There is no transcription to summarize.")
            return

        lang_value = self.lang_var.get()
        summary_language = lang_value if lang_value in {"es", "en"} else None

        logger.info("Generating final summary of the full meeting")
        self.log_status("[SUMMARY] Generating final summary...")

        try:
            num_utterances = len(
                [f for f in self.transcript_full.split("\n") if f.strip()],
            )
            avg_sentiment = (
                sum(self.sentiment_history) / len(self.sentiment_history)
                if self.sentiment_history
                else 0
            )

            self.final_summary = self.meeting_summarizer.summarize_full(
                transcript=self.transcript_full,
                avg_sentiment=avg_sentiment,
                num_utterances=num_utterances,
                language=summary_language,
            )
            logger.info("Final summary generated correctly")

            summary_window = tk.Toplevel(self.root)
            if summary_language == "es":
                window_title = "Resumen ejecutivo de la reunión"
                header_text = "Resumen ejecutivo"
            else:
                window_title = "Executive Meeting Summary"
                header_text = "Executive Summary"

            summary_window.title(window_title)
            summary_window.geometry("700x600")

            tk.Label(
                summary_window,
                text=header_text,
                font=("Arial", 14, "bold"),
            ).pack(pady=10)

            summary_text_widget = scrolledtext.ScrolledText(
                summary_window,
                wrap=tk.WORD,
                font=("Arial", 10),
            )
            summary_text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            summary_text_widget.insert(tk.END, self.final_summary)
            summary_text_widget.config(state=tk.DISABLED)

            close_button = tk.Button(
                summary_window,
                text="Close",
                command=summary_window.destroy,
                bg="#cccccc",
            )
            close_button.pack(pady=10)

            self.log_status("[OK] Final summary generated")

        except Exception as exc:
            logger.error("Error generating final summary: %s", exc)
            self.log_status(
                f"[ERROR] Error generating summary: {str(exc)[:40]}",
            )
            messagebox.showerror(
                "Error",
                f"Error generating summary:\n{exc}",
            )

    def generate_report(self) -> None:
        logger.info("Generating PDF report")
        self.log_status("[PDF] Generating report...")

        if not self.transcript_full:
            logger.warning("No data available to generate report")
            messagebox.showwarning("Warning", "There is no data to save.")
            return

        try:
            self.fig.savefig("temp_graph.png", dpi=150, bbox_inches="tight")
            logger.info("Graph saved as temp_graph.png")

            lang_value = self.lang_var.get()
            summary_language = lang_value if lang_value in {"es", "en"} else None

            if summary_language == "es":
                title_report = "Informe de reunión"
                title_chart = "Gráfico de sentimiento"
                title_exec_summary = "Resumen ejecutivo"
                title_full_transcription = "Transcripción completa"
                no_summary_text = "No hay resumen disponible."
                fragmented_note = (
                    "(Resumen fragmentado - use FINAL SUMMARY para un análisis completo)"
                )
            else:
                title_report = "Meeting Report"
                title_chart = "Sentiment Chart"
                title_exec_summary = "Executive Summary"
                title_full_transcription = "Full Transcription"
                no_summary_text = "No summary available."
                fragmented_note = "(Fragmented summary - use FINAL SUMMARY for a complete analysis)"

            pdf = FPDF()
            pdf.add_page()

            pdf.set_font("Arial", "B", 18)
            pdf.cell(0, 15, txt=title_report, ln=1, align="C")
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
            pdf.cell(0, 10, txt=title_chart, ln=1)
            pdf.ln(2)

            pdf.image("temp_graph.png", x=30, y=pdf.get_y(), w=150)
            pdf.ln(95)

            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, txt=title_exec_summary, ln=1)
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
                    txt=fragmented_note,
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
                pdf.cell(0, 6, txt=no_summary_text, ln=1)

            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, txt=title_full_transcription, ln=1)
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
            filename_pdf = f"Meeting_{timestamp}.pdf"
            filename_txt = f"Transcription_{timestamp}.txt"

            pdf.output(filename_pdf)
            logger.info("PDF saved: %s", filename_pdf)

            with open(filename_txt, "w", encoding="utf-8") as file:
                file.write(self.transcript_full)
            logger.info("Transcription saved: %s", filename_txt)

            self.log_status(f"[OK] Saved: {filename_pdf}")
            messagebox.showinfo(
                "Success",
                f"Files saved:\n{filename_pdf}\n{filename_txt}",
            )

        except Exception as exc:
            logger.error("Error generating report: %s", exc)
            self.log_status(f"[ERROR] Error saving: {str(exc)[:40]}")
            messagebox.showerror(
                "Error",
                f"Error generating report:\n{exc}",
            )
