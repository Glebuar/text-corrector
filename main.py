import pyperclip
import keyboard
import time
import re
import requests
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from win10toast import ToastNotifier
import tkinter as tk
import webbrowser
from pathlib import Path
import pystray
from PIL import Image, ImageDraw
import threading
from cryptography.fernet import Fernet

CONFIG_FILE = Path.cwd() / ".text_corrector_config"
ENCRYPTION_KEY_FILE = Path.home() / ".text_corrector_encryption"
state_history = {"original": "", "corrected": ""}
notifier = ToastNotifier()

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
    notifier.show_toast(title, message, duration=5, threaded=True)


def is_connected():
    try:
        requests.get('https://api.openai.com', timeout=3)
        return True
    except requests.ConnectionError:
        return False


def correct_text_with_openai(input_text: str, api_key: str) -> str:
    prompt = ChatPromptTemplate.from_template(
        "Correct grammar, spelling, punctuation, and style errors. Provide only corrected text:\n{input_text}"
    )
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, api_key=api_key)
    chain = prompt | llm
    try:
        response = chain.invoke({"input_text": input_text})
        return response.content.strip()
    except Exception as e:
        notify("API Error", str(e))
    return ""


def limit_sentences(text, max_sentences=3):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return ' '.join(sentences[:max_sentences])


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
        notify("Selection Error", "Please select some text first.")
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

    limited_text = limit_sentences(selected_text)
    corrected_text = correct_text_with_openai(limited_text, api_key)

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
        self.title("Text Corrector")
        self.api_key = tk.StringVar()
        self.tray_icon = None
        self.cipher = get_cipher()

        # Hide main window and taskbar icon
        self.withdraw()

        # Create system tray icon
        self.create_tray_icon()

        # GUI components
        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        frame = tk.Frame(self)
        frame.pack(padx=10, pady=10)

        tk.Label(frame, text="Enter OpenAI API Key:").pack(pady=5)
        tk.Entry(frame, textvariable=self.api_key, width=50).pack(pady=5)

        tk.Button(frame, text="Get API Key", command=self.open_api_link).pack(pady=5)
        tk.Button(frame, text="Save API Key", command=self.save_config).pack(pady=5)

        tk.Label(frame, text="Hotkey:\nAlt+Q: Correct selected text\nTo revert changes, use Ctrl+Z").pack(pady=10)
        tk.Label(frame, text="© Gleb Bochkarov").pack(side=tk.BOTTOM, pady=10)

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
        notify("Text Corrector",
               "Version 1.0\nPress Alt+Q to correct text\nCtrl+Z to revert")

    def quit_app(self):
        self.tray_icon.stop()
        self.destroy()
        keyboard.unhook_all()
        self.quit()

    def open_api_link(self):
        webbrowser.open("https://platform.openai.com/api-keys")

    def get_api_key(self):
        return self.api_key.get().strip()

    def load_config(self):
        if CONFIG_FILE.exists():
            try:
                # Read encrypted format
                with open(CONFIG_FILE, 'rb') as f:
                    encrypted_api_key = f.read()

                # Direct decryption attempt
                decrypted_api_key = self.cipher.decrypt(encrypted_api_key).decode()
                self.api_key.set(decrypted_api_key)

            except Exception as e:
                notify("Config Error", "Failed to read encrypted config file")

    def save_config(self):
        api_key = self.api_key.get().strip()
        if not api_key:
            notify("Error", "API key cannot be empty")
            return
        try:
            encrypted_api_key = self.cipher.encrypt(api_key.encode())
            with open(CONFIG_FILE, 'wb') as f:
                f.write(encrypted_api_key)
            notify("Settings Saved", "API key stored successfully")
        except Exception as e:
            notify("Save Error", f"Failed to save API key: {str(e)}")

    def destroy(self):
        self.withdraw()


def handle_key_event(event):
    global alt_pressed, q_pressed, hotkey_active
    suppress = False

    if event.event_type == keyboard.KEY_DOWN:
        if event.name == 'alt' and not alt_pressed:
            alt_pressed = True
            if q_pressed:
                hotkey_active = True
                suppress = True
        elif event.name == 'q' and not q_pressed:
            q_pressed = True
            if alt_pressed:
                hotkey_active = True
                suppress = True

    elif event.event_type == keyboard.KEY_UP:
        if event.name == 'alt':
            alt_pressed = False
            suppress = hotkey_active
        elif event.name == 'q':
            q_pressed = False
            suppress = hotkey_active

    if hotkey_active and not alt_pressed and not q_pressed:
        keyboard.call_later(replace_selected_text, delay=0.1)
        hotkey_active = False

    return False if suppress or hotkey_active else None


if __name__ == "__main__":
    app = AppUI()
    keyboard.hook_key('alt', handle_key_event, suppress=True)
    keyboard.hook_key('q', handle_key_event, suppress=True)
    notify("AI Text Correction Tool",
           "Running in system tray\nPress Alt+Q to correct text\nUse Ctrl+Z to revert")
    app.mainloop()