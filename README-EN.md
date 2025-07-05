## PDF Highlighter–AI Translator User Guide

**Author: Teng**

---

### 1. Project Overview

PDF Highlighter–AI Translator is a document reader that combines PDF highlighting, annotation, and AI translation into one tool, designed especially for language learners and professional readers. It leverages a large language model’s capabilities alongside intuitive PDF operations to help you browse, understand, and organize document content efficiently.
| ![](https://github.com/twy2020/PDF_Highlighter-AI_Translator/blob/main/pics/12887b091035f976d8eceaaaf181e243.png) | ![](https://github.com/twy2020/PDF_Highlighter-AI_Translator/blob/main/pics/21800d47bb8fb28f5988d376e76b5ddd.png) | ![](https://github.com/twy2020/PDF_Highlighter-AI_Translator/blob/main/pics/8936fbc4fb94c081a5debade846e3b6f.png) |
| :---: | :---: | :---: |
| ![](https://github.com/twy2020/PDF_Highlighter-AI_Translator/blob/main/pics/a55e09ac693cc017d467b92b386d1b39.png)  | ![](https://github.com/twy2020/PDF_Highlighter-AI_Translator/blob/main/pics/e0b83c24876116560e999ed42a1a80f3.png) | ![](https://github.com/twy2020/PDF_Highlighter-AI_Translator/blob/main/pics/e446d0434d776918ceb5928369326e8a.png) |


---

### 2. Installation & Deployment

#### 2.1 Windows Executable

1. Download **PDF\_Highlighter-AI\_Translator.zip** from the Release page.
2. Extract, and ensure the following files are in the same folder:

   * `PDF_Highlighter-AI_Translator.exe`
   * `ai.cfg`
   * `ui.cfg`

#### 2.2 From Source (Cross-Platform)

```bash
# Clone the repository and enter the project directory
git clone https://github.com/twy2020/PDF_Highlighter-AI_Translator.git
cd PDF_Highlighter-AI_Translator

# (Optional) Use Conda to create a virtual environment
conda create -n pdf_tran python=3.12 -y
conda activate pdf_tran

# Install dependencies
pip install -r requirements.txt
```

---

### 3. Configuration

#### 3.1 AI Translation Settings (`ai.cfg`)

```jsonc
{
  "API_URL":        "https://api.siliconflow.cn/v1/chat/completions",
  "API_KEY":        "Your API Key",
  "MODEL_NAME":     "deepseek-ai/DeepSeek-V3",
  "REQUEST_TIMEOUT": 60,
  "WORD_PROMPT":    "Intermediate or above level, professional terms, difficult or rare vocabulary"
}
```

> **Tip:** Register via the author’s invite link on SiliconFlow ([https://cloud.siliconflow.cn/i/jLLp0NCk](https://cloud.siliconflow.cn/i/jLLp0NCk)) to get free credit.

#### 3.2 UI Preferences (`ui.cfg`)

```jsonc
{
  "DARK_MODE":     true,       // Enable dark mode by default
  "INVERT_PDF":    false,      // Invert PDF background color
  "CONTRAST_LEVEL": 0.85       // Contrast level (range: 0.2–1.0)
}
```

---

### 4. Quick Start

#### 4.1 Launching the App

* **Command Line**

  ```bash
  python main.py                # Opens the main interface
  python main.py path/to/doc.pdf  # Loads the specified PDF directly
  ```

* **Windows**
  Double-click `PDF_Highlighter-AI_Translator.exe`.

#### 4.2 Opening & Navigation

* **Open PDF:** Click **Open PDF** in the toolbar.
* **Page Jump:**

  * Thumbnail panel on the left
  * Page number input at bottom
* **Zoom:** Ctrl + mouse wheel

---

### 5. Core Features Demo

#### 5.1 Smart Text Selection

* Click and drag to select any text area.
* Automatically handles line breaks, superscripts/subscripts, and hyphenation.

#### 5.2 Translation & Vocabulary Extraction

1. After selecting text, choose on the left panel:

   * **Translate Paragraph**
   * **Extract & Translate Vocabulary**
2. View results in the **Translation** or **Vocabulary** tab on the right.

#### 5.3 Highlighting & Annotation

* **Highlight Word/Sentence:** Click the icon in the first column of the table.
* **Custom Colors:** Enter a hex color code or use the color picker.
* **View Translation:** Hover over a highlight to see a tooltip.

#### 5.4 Batch Operations

* **Highlight/Clear This Page**
* **Highlight/Clear Entire Document**

---

### 6. Export Functions

#### 6.1 Export Words & Sentences

* **Current Page:** Click **Export This Page** on the respective tab.
* **Entire Document:** Click **Export All** on the respective tab.

#### 6.2 Export Annotated PDF

Click **Export PDF** in the toolbar to generate a PDF with all highlights and annotations.

---

### 7. UI Customization

* **Dark/Light Mode:** Toggle button in the toolbar.
* **Invert PDF Colors:** **Invert** button in the toolbar.
* **Adjust Contrast:** Slider in the toolbar.
* **Thumbnail Panel:**

  * Click thumbnails to jump pages.
  * See highlight status indicators.

---

### 8. Advanced Tips

#### 8.1 Fine-Tuning Vocabulary Extraction

Adjust the `WORD_PROMPT` in `ai.cfg`. For example:

```jsonc
"WORD_PROMPT": "Technical jargon, specialized terminology, advanced vocabulary"
```

#### 8.2 UI Settings

Edit `ui.cfg` to tweak theme, contrast, and inversion. Restart the app for changes to take effect.

---

### 9. FAQs & Troubleshooting

| Issue                  | Solution                                                                                            |
| ---------------------- | --------------------------------------------------------------------------------------------------- |
| Translation fails      | 1. Verify API settings in `ai.cfg`<br>2. Check network connection<br>3. Reduce selected text length |
| Highlights missing     | 1. Confirm you’re on the correct page<br>2. Zoom view (Ctrl+wheel)<br>3. Change highlight color     |
| Thumbnails out of sync | 1. Thumbnails update automatically on page switch<br>2. Restart the app                             |

---

### 10. Support & Contribution

* **Report Issues & Suggest Features:**
  GitHub Issues → [https://github.com/twy2020/PDF\_Highlighter-AI\_Translator/issues](https://github.com/twy2020/PDF_Highlighter-AI_Translator/issues)
* **Contact:** [tenwonyun@gmail.com](mailto:tenwonyun@gmail.com)
* **Contributing:** Fork & submit a Pull Request. See the project README for details.

---

PDF Highlighter–AI Translator is dedicated to providing an efficient, convenient solution for reading foreign-language documents. Thank you for your support and enjoy your reading!
