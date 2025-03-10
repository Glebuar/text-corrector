# Text Corrector

**AI-Powered Writing Assistant at Your Fingertips**  

This program eliminates writing friction by bringing GPT-3.5's correction capabilities directly into your workflow. Simply press `Alt+Q` to:  
✓ Fix grammar/spelling in any application  
✓ Perfect punctuation & style instantly  
✓ Preserve technical content (code/symbols)  
✓ Maintain original text length  

**Why it's essential:**  
- 💰 **Extremely Affordable** - ~1,000 corrections per $1[^1] Check [OpenAI Model Pricing](https://platform.openai.com/docs/pricing)
- 🚀 **Zero Context Switching** - Fix text directly in your email client, document editor, or coding IDE without copying to web interfaces  
- ⚡ **Instant Results** - 1.5s average correction time vs manual proofreading  
- 🔒 **Privacy First** - Local encryption for API keys, no text storage  
- 🖱️ **Undo-Friendly** - `Ctrl+Z` reverts changes if needed  

[^1]: Based on average 500-character texts. Actual count may vary slightly depending on text complexity.

Perfect for professionals, students, and non-native speakers who need polished writing without interrupting their workflow. The tool pays for itself after avoiding just one embarrassing typo in important communications.

---

## Installation

### 1. Download the Latest Release
1. Go to the [Releases page](https://github.com/Glebuar/text-corrector/releases)
2. Download the `TextCorrector.zip` file
3. Unzip the package to any folder on your computer

### 2. First-Time Setup
1. Create OpenAI [API key](https://platform.openai.com/settings/organization/api-keys)
2. Ensure account has [active credits](https://platform.openai.com/settings/organization/billing/overview)
3. Launch `TextCorrector.exe` (app minimizes to system tray)
4. **Right-click** the tray icon → **Show Settings**
5. In the settings window, click **Manage API Keys**
6. Paste your API key → **Save**

The program runs in background. Access settings anytime via tray icon.

---

## Development

### 1. Clone the repository

```sh
git clone https://github.com/Glebuar/text-corrector.git
cd text-corrector
```

### 2. Set up the Python environment

Ensure you have Python 3.x installed on your system. You can download it from the official [Python website](https://www.python.org/downloads/).

### 3. Install dependencies

```sh
pip install -r requirements.txt
```

### 4 Building the Executable

```sh
pip install cx_Freeze
python setup.py build
```
