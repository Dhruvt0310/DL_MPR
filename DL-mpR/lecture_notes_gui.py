#!/usr/bin/env python3
"""
Lecture Notes Generator GUI
A simple interface for converting YouTube videos to structured lecture notes
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess
import threading
from pathlib import Path
import os
import sys

# Try to import whisper, handle gracefully if not available
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError as e:
    WHISPER_AVAILABLE = False
    WHISPER_ERROR = str(e)

class LectureNotesGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Lecture Notes Generator")
        self.root.geometry("800x700")
        
        # Variables
        self.youtube_url = tk.StringVar()
        self.model_size = tk.StringVar(value="base")
        self.ollama_model = tk.StringVar(value="llama3")
        self.output_folder = tk.StringVar(value="./")
        
        # Whisper model (loaded on demand)
        self.whisper_model = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="🎓 Lecture Notes Generator", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # YouTube URL input
        ttk.Label(main_frame, text="YouTube URL:").grid(row=1, column=0, sticky=tk.W, pady=5)
        url_entry = ttk.Entry(main_frame, textvariable=self.youtube_url, width=50)
        url_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        
        # Model settings frame
        settings_frame = ttk.LabelFrame(main_frame, text="Settings", padding="10")
        settings_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        settings_frame.columnconfigure(1, weight=1)
        
        # Whisper model size
        ttk.Label(settings_frame, text="Whisper Model:").grid(row=0, column=0, sticky=tk.W, pady=2)
        model_combo = ttk.Combobox(settings_frame, textvariable=self.model_size, 
                                  values=["tiny", "base", "small", "medium", "large"], 
                                  state="readonly", width=15)
        model_combo.grid(row=0, column=1, sticky=tk.W, pady=2, padx=(5, 0))
        
        # Ollama model
        ttk.Label(settings_frame, text="Ollama Model:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ollama_entry = ttk.Entry(settings_frame, textvariable=self.ollama_model, width=20)
        ollama_entry.grid(row=1, column=1, sticky=tk.W, pady=2, padx=(5, 0))
        
        # Output folder
        ttk.Label(settings_frame, text="Output Folder:").grid(row=2, column=0, sticky=tk.W, pady=2)
        folder_frame = ttk.Frame(settings_frame)
        folder_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0))
        folder_frame.columnconfigure(0, weight=1)
        
        folder_entry = ttk.Entry(folder_frame, textvariable=self.output_folder)
        folder_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(folder_frame, text="Browse", command=self.browse_folder, width=8).grid(row=0, column=1, padx=(5, 0))
        
        # Process button
        self.process_btn = ttk.Button(main_frame, text="🚀 Generate Lecture Notes", 
                                     command=self.start_processing, style="Accent.TButton")
        self.process_btn.grid(row=3, column=0, columnspan=3, pady=20)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready to process", foreground="green")
        self.status_label.grid(row=5, column=0, columnspan=3, pady=5)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        main_frame.rowconfigure(6, weight=1)
        
        # Log tab
        log_frame = ttk.Frame(notebook, padding="5")
        notebook.add(log_frame, text="Process Log")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Clear log button
        ttk.Button(log_frame, text="Clear Log", command=self.clear_log).grid(row=1, column=0, pady=(5, 0))
        
        # Notes tab
        notes_frame = ttk.Frame(notebook, padding="5")
        notebook.add(notes_frame, text="Generated Notes")
        notes_frame.columnconfigure(0, weight=1)
        notes_frame.rowconfigure(0, weight=1)
        
        self.notes_text = scrolledtext.ScrolledText(notes_frame, height=15, wrap=tk.WORD, 
                                                   font=("Consolas", 10))
        self.notes_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Notes buttons frame
        notes_buttons = ttk.Frame(notes_frame)
        notes_buttons.grid(row=1, column=0, pady=(5, 0), sticky=tk.W)
        
        ttk.Button(notes_buttons, text="Clear Notes", command=self.clear_notes).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(notes_buttons, text="Save Notes", command=self.save_notes).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(notes_buttons, text="Copy to Clipboard", command=self.copy_notes).grid(row=0, column=2)
        
    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_folder.get())
        if folder:
            self.output_folder.set(folder)
    
    def log_message(self, message):
        """Add message to log with timestamp"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
    
    def clear_notes(self):
        self.notes_text.delete(1.0, tk.END)
    
    def save_notes(self):
        """Save the notes to a file"""
        notes_content = self.notes_text.get(1.0, tk.END).strip()
        if not notes_content:
            messagebox.showwarning("Warning", "No notes to save")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("Markdown files", "*.md"), ("All files", "*.*")],
            initialdir=self.output_folder.get(),
            initialfilename="lecture_notes.txt"
        )
        
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(notes_content)
                messagebox.showinfo("Success", f"Notes saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save notes: {str(e)}")
    
    def copy_notes(self):
        """Copy notes to clipboard"""
        notes_content = self.notes_text.get(1.0, tk.END).strip()
        if not notes_content:
            messagebox.showwarning("Warning", "No notes to copy")
            return
        
        self.root.clipboard_clear()
        self.root.clipboard_append(notes_content)
        messagebox.showinfo("Success", "Notes copied to clipboard!")
    
    def update_status(self, message, color="black"):
        self.status_label.config(text=message, foreground=color)
        self.root.update_idletasks()
    
    def start_processing(self):
        """Start the processing in a separate thread"""
        if not self.youtube_url.get().strip():
            messagebox.showerror("Error", "Please enter a YouTube URL")
            return
            
        # Disable button and start progress
        self.process_btn.config(state="disabled")
        self.progress.start()
        
        # Start processing thread
        thread = threading.Thread(target=self.process_pipeline, daemon=True)
        thread.start()
    
    def process_pipeline(self):
        """Main processing pipeline"""
        try:
            output_dir = Path(self.output_folder.get())
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Step 1: Download audio
            self.update_status("Downloading audio...", "blue")
            audio_file = self.download_audio()
            
            # Step 2: Transcribe
            self.update_status("Transcribing audio...", "blue")
            transcript_file = self.transcribe_audio(audio_file)
            
            # Step 3: Generate notes
            self.update_status("Generating lecture notes...", "blue")
            notes_file = self.generate_notes(transcript_file)
            
            self.update_status("✅ Process completed successfully!", "green")
            self.log_message(f"✅ All files saved to: {output_dir}")
            self.log_message("📝 Notes are now displayed in the 'Generated Notes' tab")
            
            # Show success message and switch to notes tab
            messagebox.showinfo("Success", "Lecture notes generated successfully!\n\nCheck the 'Generated Notes' tab to view your notes.")
                
        except Exception as e:
            self.update_status(f"❌ Error: {str(e)}", "red")
            self.log_message(f"❌ Error: {str(e)}")
            messagebox.showerror("Error", f"Process failed: {str(e)}")
        
        finally:
            # Re-enable button and stop progress
            self.progress.stop()
            self.process_btn.config(state="normal")
    
    def download_audio(self):
        """Download audio from YouTube URL"""
        output_dir = Path(self.output_folder.get())
        audio_file = output_dir / "lecture_audio1.mp3"
        
        self.log_message("🎧 Starting audio download...")
        
        cmd = [
            "yt-dlp",
            "-f", "bestaudio",
            "--extract-audio",
            "--audio-format", "mp3",
            "-o", str(audio_file),
            self.youtube_url.get()
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.log_message("✅ Audio downloaded successfully")
            return audio_file
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to download audio: {e.stderr}")
        except FileNotFoundError:
            raise Exception("yt-dlp not found. Please install it: pip install yt-dlp")
    
    def transcribe_audio(self, audio_file):
        """Transcribe audio using Whisper"""
        output_dir = Path(self.output_folder.get())
        transcript_file = output_dir / "transcript.txt"
        
        if not WHISPER_AVAILABLE:
            raise Exception(f"Whisper not available: {WHISPER_ERROR}")
        
        self.log_message(f"🎤 Loading Whisper model ({self.model_size.get()})...")
        
        try:
            # Load model if not already loaded or if size changed
            if self.whisper_model is None:
                self.whisper_model = whisper.load_model(self.model_size.get())
            
            self.log_message("🎤 Transcribing audio...")
            result = self.whisper_model.transcribe(str(audio_file))
            
            # Save transcript
            with open(transcript_file, "w", encoding="utf-8") as f:
                f.write(result["text"])
            
            self.log_message("✅ Transcription completed")
            return transcript_file
            
        except Exception as e:
            raise Exception(f"Transcription failed: {str(e)}")
    
    def generate_notes(self, transcript_file):
        """Generate lecture notes using Ollama"""
        output_dir = Path(self.output_folder.get())
        notes_file = output_dir / "lecture_notes.txt"
        
        self.log_message("📝 Generating lecture notes with Ollama...")
        
        # Read transcript
        with open(transcript_file, "r", encoding="utf-8") as f:
            transcript = f.read()
        
        # Prepare prompt
        prompt = f"""You are an expert lecture note-taker.
Take the following transcript and convert it into structured lecture notes with clear sections, headings, and bullet points.
Make it well-organized and easy to study from.

Transcript:
{transcript}"""
        
        try:
            # Call Ollama
            process = subprocess.Popen(
                ["ollama", "run", self.ollama_model.get()],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            lecture_notes, errors = process.communicate(prompt)
            
            if process.returncode != 0:
                raise Exception(f"Ollama error: {errors}")
            
            # Save notes to file
            with open(notes_file, "w", encoding="utf-8") as f:
                f.write(lecture_notes)
            
            # Display notes in the GUI
            self.notes_text.delete(1.0, tk.END)
            self.notes_text.insert(1.0, lecture_notes)
            
            self.log_message("✅ Lecture notes generated and displayed")
            return notes_file
            
        except FileNotFoundError:
            raise Exception("Ollama not found. Please install Ollama and ensure it's in your PATH")
        except Exception as e:
            raise Exception(f"Note generation failed: {str(e)}")

def main():
    root = tk.Tk()
    app = LectureNotesGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()