import pyperclip
import keyboard
import time
import requests
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import tkinter as tk
from tkinter import messagebox
import webbrowser
from pathlib import Path
import pystray
from PIL import Image, ImageDraw
import threading
from cryptography.fernet import Fernet

CONFIG_FILE = Path.cwd() / ".text_corrector_config"
ENCRYPTION_KEY_FILE = Path.home() / ".text_corrector_encryption"
state_history = {"original": "", "corrected": ""}

# State tracking variables
alt_pressed = False
q_pressed = False
hotkey_active = False

def generate_key():
    """Silently generate and save encryption key if missing"""
    if not ENCRYPTION_KEY_FILE.exists():
        key = Fernet.generate_key()
        with open(ENCRYPTION_KEY_FILE, 'wb') as key_file:
            key_file.write(key)

def get_cipher():
    """Get Fernet cipher instance with stored key"""
    generate_key()  # Ensure key exists
    with open(ENCRYPTION_KEY_FILE, 'rb') as key_file:
        return Fernet(key_file.read())

def notify(title, message):
    """Show Tkinter message dialog"""

    def show_dialog():
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(title, message)
        root.destroy()

    # Handle threading for keyboard events
    if app and app.winfo_exists():
        app.after(0, show_dialog)
    else:
        show_dialog()

def is_connected():
    try:
        requests.get('https://api.openai.com', timeout=3)
        return True
    except requests.ConnectionError:
        return False

def correct_text_with_openai(input_text: str, api_key: str) -> str:
    prompt = ChatPromptTemplate.from_template(
        "Correct grammar, spelling, punctuation, and style errors; ensure each corrected sentence closely matches the original length; if the text contains nonsensical or repetitive content (e.g., random characters, code snippets, variable names, symbols, quotes) or has no errors, return the original text exactly as provided; do not comment or provide explanations about corrections; provide only the corrected text:\n{input_text}"
    )
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, api_key=api_key)
    chain = prompt | llm
    try:
        response = chain.invoke({"input_text": input_text})
        return response.content.strip()
    except Exception as e:
        notify("API Error", str(e))
    return ""

def safe_hotkey(func):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            notify("Hotkey Error", str(e))
        return True
    return wrapper

@safe_hotkey
def replace_selected_text():
    original_clipboard = pyperclip.paste()
    pyperclip.copy('')
    keyboard.send('ctrl+c')
    time.sleep(0.3)
    selected_text = pyperclip.paste().strip()

    if not selected_text:
        notify("Nothing Selected", "Please select some text first.")
        pyperclip.copy(original_clipboard)
        return

    # Add character length check
    if len(selected_text) > 1000:
        notify("Limit Exceeded", "Maximum 1000 characters allowed for correction.")
        pyperclip.copy(original_clipboard)
        return

    api_key = app.get_api_key()
    if not api_key:
        notify("API Key Error", "Please enter your OpenAI API key.")
        pyperclip.copy(original_clipboard)
        return

    if not is_connected():
        notify("No Internet", "Check your connection.")
        pyperclip.copy(original_clipboard)
        return

    # Use full selected text (under 1000 chars)
    corrected_text = correct_text_with_openai(selected_text, api_key)

    if corrected_text:
        state_history["original"] = selected_text
        state_history["corrected"] = corrected_text

        keyboard.send('backspace')
        time.sleep(0.05)
        keyboard.write(corrected_text, delay=0.02)

    pyperclip.copy(original_clipboard)
    keyboard.release('alt')

class AppUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.iconbitmap('icon.ico')
        self.title("Text Corrector")
        self.api_key = ""
        self.tray_icon = None
        self.cipher = get_cipher()

        # Window configuration
        self.geometry("250x210")
        self.resizable(False, False)
        self.minsize(250, 210)
        self.maxsize(250, 210)
        self.withdraw()
        self.create_tray_icon()
        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        frame = tk.Frame(self)
        frame.pack(padx=10, pady=10)

        # API Key status display
        self.api_status_label = tk.Label(frame, text="API Key: None")
        self.api_status_label.pack(pady=5)

        link_label = tk.Label(frame, text="Get your API key here", fg="blue", cursor="hand2")
        link_label.pack(pady=5)
        link_label.bind("<Button-1>", lambda e: self.open_api_link())

        tk.Button(frame, text="Manage API Keys", command=self.open_api_key_manager).pack(pady=5)
        tk.Label(frame, text="Hotkeys:").pack(pady=5)
        hotkey_frame = tk.Frame(frame)
        hotkey_frame.pack(pady=5)
        tk.Label(hotkey_frame, text="Alt+Q:", font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky='w')
        tk.Label(hotkey_frame, text="Correct selected text", font=('Arial', 10)).grid(row=1, column=1, sticky='w')
        tk.Label(hotkey_frame, text="Ctrl+Z:", font=('Arial', 10, 'bold')).grid(row=2, column=0, sticky='w')
        tk.Label(hotkey_frame, text="Revert changes", font=('Arial', 10)).grid(row=2, column=1, sticky='w')

    def create_tray_icon(self):
        # Create simple tray icon
        image = Image.open("icon.ico")
        ImageDraw.Draw(image).text((24, 24), "T", fill='black')

        # Tray menu
        menu = pystray.Menu(
            pystray.MenuItem('Show Settings', self.show_window),
            pystray.MenuItem('About', self.show_about),
            pystray.MenuItem('Exit', self.quit_app)
        )

        # Create system tray icon in separate thread
        self.tray_icon = pystray.Icon("text_corrector", image, "Text Corrector", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self):
        self.deiconify()
        self.attributes('-topmost', 1)
        self.attributes('-topmost', 0)

    def show_about(self):
        about_window = tk.Toplevel(self)
        about_window.iconbitmap('icon.ico')
        about_window.title("About Text Corrector")
        about_window.geometry("300x150")
        about_window.resizable(False, False)

        tk.Label(about_window, text="Text Corrector v1.0.0", font=('Arial', 12, 'bold')).pack(pady=5)
        tk.Label(about_window, text="AI Model: gpt-3.5-turbo").pack(pady=5)
        tk.Label(about_window, text="Author: Gleb Bochkarov").pack(pady=5)

        close_btn = tk.Button(about_window, text="Close", command=about_window.destroy)
        close_btn.pack(pady=5)
        about_window.grab_set()

    def quit_app(self):
        self.tray_icon.stop()
        self.destroy()
        keyboard.unhook_all()
        self.quit()

    def open_api_link(self):
        webbrowser.open("https://platform.openai.com/api-keys")

    def mask_api_key(self, key):
        if not key:
            return "None"
        if len(key) <= 6:
            return "***"
        return f"{key[:2]}...{key[-4:]}" if len(key) > 6 else key

    def open_api_key_manager(self):
        manager = tk.Toplevel(self)
        manager.iconbitmap('icon.ico')
        manager.title("API Key Management")
        manager.geometry("320x80")
        manager.resizable(False, False)

        tk.Label(manager, text="API Key:").grid(row=0, column=0, padx=5, pady=5)
        key_entry = tk.Entry(manager, width=40)
        key_entry.grid(row=0, column=1, padx=5, pady=5)

        # Buttons
        btn_frame = tk.Frame(manager)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=10)

        tk.Button(btn_frame, text="Save", command=lambda: self.save_api_key(
            key_entry.get().strip(),
            manager
        )).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="Cancel", command=manager.destroy).pack(side=tk.LEFT, padx=5)

    def save_api_key(self, key, window):
        if not key:
            notify("Error", "API key cannot be empty")
            return

        self.api_key = key
        masked = self.mask_api_key(key)
        self.api_status_label.config(text=f"API Key: {masked}")
        self.save_config()
        window.destroy()
        notify("Success", "API key saved successfully")

    def get_api_key(self):
        return self.api_key

    def load_config(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'rb') as f:
                    encrypted_data = f.read()

                decrypted_data = self.cipher.decrypt(encrypted_data).decode()
                self.api_key = decrypted_data
                masked = self.mask_api_key(decrypted_data)
                self.api_status_label.config(text=f"API Key: {masked}")

            except Exception as e:
                notify("Config Error", "Failed to load configuration")

    def save_config(self):
        try:
            encrypted_data = self.cipher.encrypt(self.api_key.encode())
            with open(CONFIG_FILE, 'wb') as f:
                f.write(encrypted_data)

        except Exception as e:
            notify("Save Error", f"Failed to save configuration: {str(e)}")

    def destroy(self):
        self.withdraw()

def handle_key_event(event):
    global alt_pressed, q_pressed, hotkey_active
    
    if event.event_type == keyboard.KEY_DOWN:
        if event.name == 'alt':
            alt_pressed = True
        elif event.name == 'q':
            q_pressed = True
            
        if alt_pressed and q_pressed and not hotkey_active:
            hotkey_active = True
            keyboard.call_later(replace_selected_text, delay=0.1)
            return True
            
    elif event.event_type == keyboard.KEY_UP:
        if event.name == 'alt':
            alt_pressed = False
            hotkey_active = False
        elif event.name == 'q':
            q_pressed = False
            hotkey_active = False
            
    # Only suppress when hotkey is active
    return True if hotkey_active else False

if __name__ == "__main__":
    app = AppUI()
    keyboard.hook(handle_key_event)  # Use a single hook for all keys
    notify("AI Text Correction Tool",
           "Running in system tray\nPress Alt+Q to correct text\nUse Ctrl+Z to revert")
    app.mainloop()