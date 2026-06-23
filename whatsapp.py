import re
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
import threading
import time

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import scrolledtext
from tkinter import messagebox

# Dynamically import Selenium drivers
SELENIUM_AVAILABLE = False
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    pass

# =====================================================================
# STEP 1: DEFINE LEXICONS AND CUSTOM SENTIMENT ENGINE
# =====================================================================
POSITIVE_WORDS = {
    "good", "great", "awesome", "love", "happy", "beautiful", "sweet", "nice", "fine", "thanks", "thank",
    "amazing", "haha", "lol", "perfect", "cool", "agree", "yes", "interesting", "fun", "cute", "best",
    "enjoy", "enjoyed", "glad", "wonderful", "excellent", "excited", "heyy", "hey", "hello", "hi", "yess",
    "superb", "brilliant", "delighted", "pleased", "fantastic", "yay", "yippee", "cheers", "care", "warm",
    "wow", "lovely", "agree", "absolutely", "haha", "hahaha", "gorgeous", "sweetheart", "babe", "dear"
}

NEGATIVE_WORDS = {
    "bad", "sad", "angry", "hate", "sorry", "worst", "boring", "dislike", "no", "fake", "wrong", "annoyed",
    "difficult", "stupid", "dumb", "hurt", "broke", "lazy", "ugly", "mad", "crying", "upset", "hate",
    "disappointed", "annoying", "fear", "scared", "pain", "suffer", "problem", "traffic", "late", "ruin",
    "ruined", "fail", "failed", "terrible", "horrible", "awful", "dreadful", "depressed", "lonely", "exhausted",
    "tired", "frustrated", "sick", "stupid", "annoy", "bother", "ignore", "jealous"
}

BOOSTER_WORDS = {"very", "really", "so", "extremely", "super", "highly", "absolutely", "totally", "completely", "much"}

NEGATION_WORDS = {
    "not", "no", "never", "dont", "cant", "wont", "didnt", "isnt", "arent", "wasnt", "werent", "havent",
    "hasnt", "hadnt", "shouldnt", "wouldnt", "couldnt", "neither", "nor"
}

EMOJI_SENTIMENT = {
    "❤️": 1.5, "💖": 1.5, "😍": 1.5, "😘": 1.5, "🥰": 1.5, "💕": 1.4,
    "😊": 1.0, "😃": 1.0, "😄": 1.0, "😁": 1.0, "🙂": 0.8,
    "😂": 1.0, "🤣": 1.2, "👍": 1.0, "🎉": 1.5, "✨": 1.2,
    "⭐": 1.0, "🌟": 1.2, "☕": 0.8, "🍕": 0.8, "🍻": 1.0,
    "😭": -1.5, "😢": -1.2, "🥺": -0.5, "😞": -1.0, "😔": -0.8,
    "😡": -1.5, "😠": -1.2, "🤬": -1.8, "👿": -1.2, "👎": -1.0,
    "😱": -0.8, "😨": -0.8, "😰": -0.8, "💔": -1.5, "🙄": -0.5,
    "😴": -0.5, "😷": -0.8, "☠️": -1.0
}

def analyze_sentiment(text):
    """
    Custom rule-based sentiment engine.
    Tokenizes text, looks up lexicons, adjusts for boosters and negations, and adds emoji weights.
    """
    text_lower = text.lower()
    words = re.findall(r'[a-zA-Z]+', text_lower)
    
    score = 0.0
    negation_timer = 0
    booster_active = False
    
    for word in words:
        is_negated = (negation_timer > 0)
        
        if word in NEGATION_WORDS:
            negation_timer = 3
            continue
            
        if word in BOOSTER_WORDS:
            booster_active = True
            continue
            
        word_score = 0.0
        if word in POSITIVE_WORDS:
            word_score = 1.0
        elif word in NEGATIVE_WORDS:
            word_score = -1.0
            
        if word_score != 0.0:
            if booster_active:
                word_score *= 1.5
                booster_active = False
            if is_negated:
                word_score *= -1.0
                
            score += word_score
            
        if negation_timer > 0:
            negation_timer -= 1
            
    emoji_score = 0.0
    emojis_found = []
    for char in text:
        if char in EMOJI_SENTIMENT:
            emoji_score += EMOJI_SENTIMENT[char]
            emojis_found.append(char)
            
    total_score = score + emoji_score
    
    if total_score > 0.2:
        sentiment = "Positive"
    elif total_score < -0.2:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"
        
    return total_score, sentiment, emojis_found

# =====================================================================
# STEP 2: CHAT TEXT FORMAT ROBUST PARSER
# =====================================================================
def parse_datetime(date_str, time_str):
    date_str = date_str.strip()
    time_str = time_str.strip()
    dt_str = f"{date_str} {time_str}"
    
    formats = [
        "%d/%m/%y %H:%M",
        "%d/%m/%Y %H:%M",
        "%d/%m/%y %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%y %I:%M %p",
        "%d/%m/%Y %I:%M %p",
        "%d/%m/%y %I:%M:%S %p",
        "%d/%m/%Y %I:%M:%S %p",
        "%m/%d/%y %I:%M %p",
        "%m/%d/%Y %I:%M %p"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            pass
    return None

def parse_whatsapp_chat(text_content):
    """
    Parses WhatsApp exported chats using regular expressions.
    """
    re_bracket = re.compile(r'^\[(\d{1,2}/\d{1,2}/\d{2,4}),\s+(\d{1,2}:\d{2}(?::\d{2})?\s*(?:[aApP][mM])?)\]\s+([^:]+):\s+(.*)$')
    re_dash = re.compile(r'^(\d{1,2}/\d{1,2}/\d{2,4}),\s+(\d{1,2}:\d{2}(?::\d{2})?\s*(?:[aApP][mM])?)\s+-\s+([^:]+):\s+(.*)$')
    
    lines = text_content.split('\n')
    parsed_messages = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        match = re_bracket.match(line)
        if not match:
            match = re_dash.match(line)
            
        if match:
            date_str, time_str, sender, msg = match.groups()
            
            if "joined using this group's invite link" in msg or "Messages and calls are end-to-end encrypted" in msg:
                continue
                
            dt = parse_datetime(date_str, time_str)
            if dt is None:
                dt = datetime.now()
                
            parsed_messages.append({
                'datetime': dt,
                'sender': sender.strip(),
                'message': msg.strip()
            })
        else:
            if parsed_messages:
                parsed_messages[-1]['message'] += " " + line
                
    return parsed_messages

# =====================================================================
# STEP 3: CONVERSE METRICS & ANALYSIS PIPELINE
# =====================================================================
def analyze_chat_metrics(messages):
    """
    Compiles individual metrics for each sender in the parsed chat list.
    """
    if not messages:
        return {}
        
    df = pd.DataFrame(messages)
    df = df.sort_values(by='datetime').reset_index(drop=True)
    
    senders = df['sender'].unique()
    metrics = {sender: {
        'messages': [],
        'word_count_total': 0,
        'emojis_list': [],
        'sentiment_scores': [],
        'sentiments_class': {'Positive': 0, 'Neutral': 0, 'Negative': 0},
        'response_times_sec': []
    } for sender in senders}
    
    for idx, row in df.iterrows():
        sender = row['sender']
        text = str(row['message'])
        
        words_count = len(re.findall(r'[a-zA-Z]+', text))
        metrics[sender]['word_count_total'] += words_count
        
        score, sentiment_class, emojis = analyze_sentiment(text)
        metrics[sender]['sentiment_scores'].append(score)
        metrics[sender]['sentiments_class'][sentiment_class] += 1
        metrics[sender]['emojis_list'].extend(emojis)
        metrics[sender]['messages'].append(row)
        
    for idx in range(1, len(df)):
        prev_msg = df.iloc[idx - 1]
        curr_msg = df.iloc[idx]
        
        if prev_msg['sender'] != curr_msg['sender']:
            delta = (curr_msg['datetime'] - prev_msg['datetime']).total_seconds()
            if delta < 8 * 3600:
                metrics[curr_msg['sender']]['response_times_sec'].append(delta)
                
    summarized_metrics = {}
    for sender, data in metrics.items():
        total_msgs = len(data['messages'])
        if total_msgs == 0:
            continue
            
        avg_words = data['word_count_total'] / total_msgs
        avg_sentiment = np.mean(data['sentiment_scores'])
        
        avg_resp_min = np.nan
        if len(data['response_times_sec']) > 0:
            avg_resp_min = np.mean(data['response_times_sec']) / 60.0
            
        emoji_series = pd.Series(data['emojis_list'])
        top_emojis = emoji_series.value_counts().head(6).to_dict() if not emoji_series.empty else {}
        
        resp_score = 5
        if not np.isnan(avg_resp_min):
            if avg_resp_min <= 1.0: resp_score = 30
            elif avg_resp_min <= 5.0: resp_score = 26
            elif avg_resp_min <= 15.0: resp_score = 22
            elif avg_resp_min <= 45.0: resp_score = 18
            elif avg_resp_min <= 120.0: resp_score = 14
            else: resp_score = 8
            
        vol_score = 5
        if avg_words >= 25.0: vol_score = 25
        elif avg_words >= 15.0: vol_score = 21
        elif avg_words >= 8.0: vol_score = 16
        elif avg_words >= 4.0: vol_score = 12
        else: vol_score = 8
        
        s_score = 5
        if avg_sentiment >= 0.5: s_score = 25
        elif avg_sentiment >= 0.2: s_score = 21
        elif avg_sentiment >= 0.0: s_score = 16
        elif avg_sentiment >= -0.2: s_score = 10
        else: s_score = 5
        
        emoji_frequency = len(data['emojis_list']) / total_msgs
        emo_score = 5
        if emoji_frequency >= 0.6: emo_score = 20
        elif emoji_frequency >= 0.3: emo_score = 16
        elif emoji_frequency >= 0.1: emo_score = 12
        elif emoji_frequency >= 0.02: emo_score = 8
        else: emo_score = 4
        
        interest_score = resp_score + vol_score + s_score + emo_score
        
        if interest_score >= 75:
            interest_level = "High Interest"
            badge_color = "#50fa7b"
        elif interest_score >= 50:
            interest_level = "Casual / Friendly"
            badge_color = "#8be9fd"
        else:
            interest_level = "Low Interest / Polite"
            badge_color = "#ff5555"
            
        summarized_metrics[sender] = {
            'total_messages': total_msgs,
            'avg_words_per_message': avg_words,
            'avg_response_time_min': avg_resp_min,
            'avg_sentiment': avg_sentiment,
            'sentiment_classes': data['sentiments_class'],
            'top_emojis': top_emojis,
            'emojis_count': len(data['emojis_list']),
            'interest_score': interest_score,
            'interest_level': interest_level,
            'interest_badge_color': badge_color,
            'messages_raw': data['messages']
        }
        
    return summarized_metrics

# =====================================================================
# STEP 4: INTERACTIVE TKINTER UI DASHBOARD
# =====================================================================
class WhatsAppAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("💬 WhatsApp Sentimental & Interest Analyzer")
        self.root.configure(bg="#121212")
        
        width, height = 1350, 800
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(1150, 720)
        
        # Global states
        self.parsed_messages = []
        self.analyzed_metrics = {}
        self.sync_active = False
        self.driver = None
        
        # Apply TTK styles
        self.style = ttk.Style()
        self.style.theme_use('default')
        self.style.configure('TNotebook', background='#121212', borderwidth=0)
        self.style.configure('TNotebook.Tab', background='#1e1e1e', foreground='#888888', font=('Segoe UI', 10, 'bold'), padding=[18, 8], borderwidth=0)
        self.style.map('TNotebook.Tab', background=[('selected', '#1d9bf0'), ('active', '#2d2d2d')], foreground=[('selected', '#ffffff'), ('active', '#ffffff')])
        
        self.style.configure('TCombobox', fieldbackground='#1e1e1e', background='#2c2c2c', foreground='#ffffff', arrowcolor='#ffffff', font=('Segoe UI', 10))
        self.style.map('TCombobox', fieldbackground=[('readonly', '#1e1e1e')], foreground=[('readonly', '#ffffff')])
        
        # Tab notebook container
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)
        
        # Main tabs
        self.tab_dashboard = tk.Frame(self.notebook, bg="#121212")
        self.tab_guide = tk.Frame(self.notebook, bg="#121212")
        
        self.notebook.add(self.tab_dashboard, text="📊 Conversation Analytics")
        self.notebook.add(self.tab_guide, text="📖 Learning Center")
        
        self.setup_dashboard_tab()
        self.setup_guide_tab()
        
        # Load sample chat at startup
        self.load_sample_data_on_startup()
        
    def setup_dashboard_tab(self):
        self.tab_dashboard.columnconfigure(0, weight=3)
        self.tab_dashboard.columnconfigure(1, weight=7)
        self.tab_dashboard.rowconfigure(0, weight=1)
        
        # -------------------------------------------------------------
        # LEFT CONTROLS & METRICS PANEL
        # -------------------------------------------------------------
        self.left_pane = tk.Frame(
            self.tab_dashboard, bg="#1e1e1e", padx=20, pady=20,
            highlightthickness=1, highlightbackground="#2d2d2d", bd=0
        )
        self.left_pane.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)
        
        title_lbl = tk.Label(
            self.left_pane, text="💬 WhatsApp Analyzer",
            font=("Segoe UI", 18, "bold"), fg="#ffffff", bg="#1e1e1e"
        )
        title_lbl.pack(anchor="w", pady=(0, 2))
        
        subtitle_lbl = tk.Label(
            self.left_pane, text="Sentimental & Interest Profiler",
            font=("Segoe UI", 9), fg="#888888", bg="#1e1e1e"
        )
        subtitle_lbl.pack(anchor="w", pady=(0, 15))
        
        # 1. LIVE SYNC SECTION
        live_sync_frame = tk.Frame(self.left_pane, bg="#262626", padx=12, pady=12, highlightthickness=1, highlightbackground="#3d3d3d")
        live_sync_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(live_sync_frame, text="LIVE WHATSAPP WEB SYNC", font=("Segoe UI", 8, "bold"), fg="#1d9bf0", bg="#262626").pack(anchor="w", pady=(0, 4))
        
        self.btn_live_sync = tk.Button(
            live_sync_frame, text="⚡ Sync with WhatsApp Web", font=("Segoe UI", 9, "bold"),
            bg="#1d9bf0", fg="#ffffff", activebackground="#0c85d0", activeforeground="#ffffff",
            relief="flat", cursor="hand2", pady=6, bd=0, command=self.toggle_live_sync
        )
        self.btn_live_sync.pack(fill="x", pady=(2, 6))
        
        self.lbl_sync_status = tk.Label(
            live_sync_frame, text="● Status: Disconnected", font=("Segoe UI", 9, "bold"),
            fg="#888888", bg="#262626"
        )
        self.lbl_sync_status.pack(anchor="w")
        
        # 2. Chat Import Section (Static)
        import_frame = tk.Frame(self.left_pane, bg="#1e1e1e")
        import_frame.pack(fill="x", pady=10)
        
        tk.Label(import_frame, text="Import File or Paste Text", font=("Segoe UI", 9, "bold"), fg="#aaaaaa", bg="#1e1e1e").pack(anchor="w", pady=(0, 4))
        
        btn_browse = tk.Button(
            import_frame, text="📁 Import Chat File (.txt)", font=("Segoe UI", 9, "bold"),
            bg="#2c2c2c", fg="#ffffff", activebackground="#1d9bf0", activeforeground="#ffffff",
            relief="flat", cursor="hand2", padx=10, pady=5, bd=0, command=self.import_chat_file
        )
        btn_browse.pack(fill="x", pady=2)
        
        self.btn_toggle_paste = tk.Button(
            import_frame, text="✏️ Paste Chat Text Instead", font=("Segoe UI", 9),
            bg="#262626", fg="#1d9bf0", activebackground="#1e1e1e", activeforeground="#1d9bf0",
            relief="flat", cursor="hand2", bd=0, pady=2, command=self.toggle_paste_input
        )
        self.btn_toggle_paste.pack(anchor="w", pady=(4, 0))
        
        self.paste_container = tk.Frame(self.left_pane, bg="#1e1e1e")
        self.paste_text = scrolledtext.ScrolledText(
            self.paste_container, wrap=tk.WORD, height=6, bg="#121212", fg="#eeeeee",
            insertbackground="white", font=("Consolas", 8), bd=0, highlightthickness=1, highlightbackground="#2d2d2d"
        )
        self.paste_text.pack(fill="both", expand=True, pady=(2, 4))
        
        btn_parse_pasted = tk.Button(
            self.paste_container, text="Analyze Pasted Chat", font=("Segoe UI", 9, "bold"),
            bg="#2c2c2c", fg="#ffffff", activebackground="#1d9bf0", activeforeground="#ffffff",
            relief="flat", cursor="hand2", pady=5, bd=0, command=self.analyze_pasted_chat
        )
        btn_parse_pasted.pack(fill="x")
        
        # Divider line
        self.div2 = tk.Frame(self.left_pane, height=1, bg="#2d2d2d")
        self.div2.pack(fill="x", pady=10)
        
        # 3. Selected Sender Profile Selection
        self.sender_select_frame = tk.Frame(self.left_pane, bg="#1e1e1e")
        self.sender_select_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(self.sender_select_frame, text="Focus Analysis on Participant", font=("Segoe UI", 9, "bold"), fg="#aaaaaa", bg="#1e1e1e").pack(anchor="w", pady=(0, 4))
        self.combo_sender = ttk.Combobox(self.sender_select_frame, state="readonly", values=[])
        self.combo_sender.pack(fill="x")
        self.combo_sender.bind("<<ComboboxSelected>>", self.on_sender_change)
        
        # Divider line
        self.div3 = tk.Frame(self.left_pane, height=1, bg="#2d2d2d")
        self.div3.pack(fill="x", pady=10)
        
        # 4. Sentiment & Interest Cards
        self.metrics_container = tk.Frame(self.left_pane, bg="#1e1e1e")
        self.metrics_container.pack(fill="both", expand=True)
        
        self.interest_card = tk.Frame(
            self.metrics_container, bg="#241a3a", padx=15, pady=10,
            highlightthickness=1, highlightbackground="#bd93f9", bd=0
        )
        self.interest_card.pack(fill="x", pady=(0, 8))
        
        self.lbl_int_title = tk.Label(self.interest_card, text="PROFILED INTEREST LEVEL", font=("Segoe UI", 8, "bold"), fg="#bd93f9", bg="#241a3a")
        self.lbl_int_title.pack(anchor="w")
        self.lbl_int_badge = tk.Label(self.interest_card, text="Waiting for Chat...", font=("Segoe UI", 16, "bold"), fg="#ffffff", bg="#241a3a")
        self.lbl_int_badge.pack(anchor="w", pady=(2, 0))
        
        stats_frame = tk.Frame(self.metrics_container, bg="#1e1e1e")
        stats_frame.pack(fill="x", pady=(5, 5))
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        
        c_msg = tk.Frame(stats_frame, bg="#262626", padx=8, pady=8, highlightthickness=1, highlightbackground="#3d3d3d")
        c_msg.grid(row=0, column=0, padx=(0, 4), pady=4, sticky="nsew")
        tk.Label(c_msg, text="TOTAL MESSAGES", font=("Segoe UI", 7, "bold"), fg="#888888", bg="#262626").pack(anchor="w")
        self.lbl_stat_msgs = tk.Label(c_msg, text="-", font=("Segoe UI", 12, "bold"), fg="#ffffff", bg="#262626")
        self.lbl_stat_msgs.pack(anchor="w")
        
        c_resp = tk.Frame(stats_frame, bg="#262626", padx=8, pady=8, highlightthickness=1, highlightbackground="#3d3d3d")
        c_resp.grid(row=0, column=1, padx=(4, 0), pady=4, sticky="nsew")
        tk.Label(c_resp, text="AVG RESPONSE SPEED", font=("Segoe UI", 7, "bold"), fg="#888888", bg="#262626").pack(anchor="w")
        self.lbl_stat_resp = tk.Label(c_resp, text="-", font=("Segoe UI", 12, "bold"), fg="#ffffff", bg="#262626")
        self.lbl_stat_resp.pack(anchor="w")
        
        c_words = tk.Frame(stats_frame, bg="#262626", padx=8, pady=8, highlightthickness=1, highlightbackground="#3d3d3d")
        c_words.grid(row=1, column=0, padx=(0, 4), pady=4, sticky="nsew")
        tk.Label(c_words, text="WORDS / MSG", font=("Segoe UI", 7, "bold"), fg="#888888", bg="#262626").pack(anchor="w")
        self.lbl_stat_words = tk.Label(c_words, text="-", font=("Segoe UI", 12, "bold"), fg="#ffffff", bg="#262626")
        self.lbl_stat_words.pack(anchor="w")
        
        c_emo = tk.Frame(stats_frame, bg="#262626", padx=8, pady=8, highlightthickness=1, highlightbackground="#3d3d3d")
        c_emo.grid(row=1, column=1, padx=(4, 0), pady=4, sticky="nsew")
        tk.Label(c_emo, text="EMOJIS SENT", font=("Segoe UI", 7, "bold"), fg="#888888", bg="#262626").pack(anchor="w")
        self.lbl_stat_emojis = tk.Label(c_emo, text="-", font=("Segoe UI", 12, "bold"), fg="#ffffff", bg="#262626")
        self.lbl_stat_emojis.pack(anchor="w")
        
        self.sent_card = tk.Frame(self.metrics_container, bg="#262626", padx=10, pady=10, highlightthickness=1, highlightbackground="#3d3d3d")
        self.sent_card.pack(fill="x", pady=(5, 0))
        
        tk.Label(self.sent_card, text="SENTIMENT BREAKDOWN", font=("Segoe UI", 8, "bold"), fg="#aaaaaa", bg="#262626").pack(anchor="w", pady=(0, 4))
        self.lbl_sentiment_details = tk.Label(self.sent_card, text="Pos: - | Neu: - | Neg: -", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#262626")
        self.lbl_sentiment_details.pack(anchor="w")
        
        # -------------------------------------------------------------
        # RIGHT PLOTS PANEL
        # -------------------------------------------------------------
        self.right_pane = tk.Frame(self.tab_dashboard, bg="#121212")
        self.right_pane.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        self.right_pane.columnconfigure(0, weight=1)
        self.right_pane.rowconfigure(0, weight=1)
        self.right_pane.rowconfigure(1, weight=1)
        
        plt.style.use('dark_background')
        self.fig = plt.Figure(figsize=(10, 6.5))
        self.fig.patch.set_facecolor('#121212')
        
        self.ax_trend = self.fig.add_subplot(2, 2, (1, 3))
        self.ax_trend.set_facecolor('#1e1e1e')
        
        self.ax_response = self.fig.add_subplot(2, 2, 2)
        self.ax_response.set_facecolor('#1e1e1e')
        
        self.ax_emoji = self.fig.add_subplot(2, 2, 4)
        self.ax_emoji.set_facecolor('#1e1e1e')
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_pane)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.canvas_widget.configure(bg="#121212")
        
        self.fig.tight_layout()

    # Toggles Paste Box input
    def toggle_paste_input(self):
        if self.paste_container.winfo_viewable():
            self.paste_container.pack_forget()
            self.btn_toggle_paste.configure(text="✏️ Paste Chat Text Instead")
        else:
            self.paste_container.pack(fill="x", after=self.btn_toggle_paste, pady=5)
            self.btn_toggle_paste.configure(text="❌ Hide Paste Area")
            
    # Load raw file
    def import_chat_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not file_path:
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            self.parse_and_analyze_raw_text(content)
            messagebox.showinfo("Success", f"Successfully loaded and parsed {len(self.parsed_messages)} chat messages!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read file: {e}")
            
    # Analyze pasted content
    def analyze_pasted_chat(self):
        content = self.paste_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("Warning", "Please paste chat text before analyzing.")
            return
            
        self.parse_and_analyze_raw_text(content)
        
    def parse_and_analyze_raw_text(self, raw_text):
        self.parsed_messages = parse_whatsapp_chat(raw_text)
        if not self.parsed_messages:
            messagebox.showerror("Parsing Error", "Could not find any message matching WhatsApp time format export rules. Verify text matches.")
            return
            
        self.analyzed_metrics = analyze_chat_metrics(self.parsed_messages)
        
        senders = list(self.analyzed_metrics.keys())
        self.combo_sender.configure(values=senders)
        if senders:
            self.combo_sender.set(senders[0])
            self.on_sender_change(None)
            
    def on_sender_change(self, event):
        sender = self.combo_sender.get()
        if not sender or sender not in self.analyzed_metrics:
            return
            
        data = self.analyzed_metrics[sender]
        
        self.lbl_int_badge.configure(
            text=data['interest_level'],
            fg=data['interest_badge_color']
        )
        self.interest_card.configure(
            highlightbackground=data['interest_badge_color'],
            bg=self.species_bg_colors_lookup(data['interest_level'])
        )
        self.lbl_int_title.configure(
            fg=data['interest_badge_color'],
            bg=self.species_bg_colors_lookup(data['interest_level'])
        )
        self.lbl_int_badge.configure(
            bg=self.species_bg_colors_lookup(data['interest_level'])
        )
        
        self.lbl_stat_msgs.configure(text=f"{data['total_messages']}")
        
        if np.isnan(data['avg_response_time_min']):
            self.lbl_stat_resp.configure(text="N/A")
        else:
            time_val = data['avg_response_time_min']
            if time_val < 1.0:
                self.lbl_stat_resp.configure(text=f"{time_val*60:.0f} secs")
            else:
                self.lbl_stat_resp.configure(text=f"{time_val:.1f} mins")
                
        self.lbl_stat_words.configure(text=f"{data['avg_words_per_message']:.1f}")
        self.lbl_stat_emojis.configure(text=f"{data['emojis_count']}")
        
        classes = data['sentiment_classes']
        total_class = sum(classes.values())
        pos_pct = classes['Positive'] / total_class if total_class else 0
        neu_pct = classes['Neutral'] / total_class if total_class else 0
        neg_pct = classes['Negative'] / total_class if total_class else 0
        
        self.lbl_sentiment_details.configure(
            text=f"😊 Positive: {pos_pct:.0%} | 😐 Neutral: {neu_pct:.0%} | 😭 Negative: {neg_pct:.0%}"
        )
        
        self.redraw_plots(sender)
        
    def species_bg_colors_lookup(self, level):
        if "High" in level:
            return "#132b2a"
        elif "Casual" in level:
            return "#241a3a"
        else:
            return "#341529"
            
    def redraw_plots(self, active_sender):
        self.ax_trend.clear()
        
        sender_data = self.analyzed_metrics[active_sender]
        messages_raw = sender_data['messages_raw']
        
        scores = [analyze_sentiment(str(m['message']))[0] for m in messages_raw]
        indices = np.arange(len(scores))
        
        self.ax_trend.plot(indices, scores, color='#aaaaaa', alpha=0.3, linewidth=1, label='Message Score')
        
        window_size = max(3, len(scores) // 5)
        if len(scores) >= 3:
            rolling_avg = pd.Series(scores).rolling(window=window_size, min_periods=1).mean()
            self.ax_trend.plot(indices, rolling_avg, color='#1d9bf0', linewidth=2.5, label=f'Rolling Avg (w={window_size})')
            
        self.ax_trend.axhline(0, color='#3d3d3d', linestyle='--', linewidth=1)
        self.ax_trend.set_title("Sentiment Path over Conversation", fontsize=11, fontweight="bold", color="#ffffff", pad=10)
        self.ax_trend.set_xlabel("Message Chronological Order", fontsize=9, color="#888888")
        self.ax_trend.set_ylabel("Sentiment Score", fontsize=9, color="#888888")
        self.ax_trend.grid(True, linestyle="--", color="#2d2d2d", alpha=0.4)
        self.ax_trend.legend(facecolor='#1e1e1e', edgecolor='#2d2d2d', fontsize=8, loc='upper left')
        
        self.ax_response.clear()
        senders = list(self.analyzed_metrics.keys())
        avg_times = []
        colors = []
        
        for s in senders:
            t = self.analyzed_metrics[s]['avg_response_time_min']
            avg_times.append(0.0 if np.isnan(t) else t)
            colors.append('#1d9bf0' if s == active_sender else '#555555')
            
        x_indices = np.arange(len(senders))
        bars = self.ax_response.bar(x_indices, avg_times, color=colors, width=0.4, edgecolor='black', linewidth=0.5)
        
        self.ax_response.set_xticks(x_indices)
        self.ax_response.set_xticklabels([s[:8] + '..' if len(s) > 8 else s for s in senders], fontsize=8, color='#888888')
        
        for bar in bars:
            height = bar.get_height()
            self.ax_response.text(
                bar.get_x() + bar.get_width()/2.0, height + (max(avg_times)*0.02 if max(avg_times) > 0 else 0.1),
                f"{height:.1f}m" if height > 0 else "N/A",
                ha='center', va='bottom', fontsize=8, color='#ffffff', fontweight='bold'
            )
            
        self.ax_response.set_title("Average Response Speed", fontsize=11, fontweight="bold", color="#ffffff", pad=10)
        self.ax_response.set_ylabel("Time (minutes)", fontsize=9, color="#888888")
        self.ax_response.grid(True, axis='y', linestyle="--", color="#2d2d2d", alpha=0.4)
        
        self.ax_emoji.clear()
        top_emojis = sender_data['top_emojis']
        if top_emojis:
            emojis = list(top_emojis.keys())
            counts = list(top_emojis.values())
            
            y_indices = np.arange(len(emojis))
            self.ax_emoji.barh(y_indices, counts, color='#bd93f9', height=0.4, edgecolor='black', linewidth=0.5)
            self.ax_emoji.set_yticks(y_indices)
            self.ax_emoji.set_yticklabels(emojis, fontsize=12, color='#ffffff')
            self.ax_emoji.invert_yaxis()
            self.ax_emoji.set_xlabel("Usage Counts", fontsize=9, color="#888888")
        else:
            self.ax_emoji.text(0.5, 0.5, "No Emojis Detected", ha='center', va='center', color='#888888', fontsize=10)
            
        self.ax_emoji.set_title("Top Favorite Emojis", fontsize=11, fontweight="bold", color="#ffffff", pad=10)
        self.ax_emoji.grid(True, axis='x', linestyle="--", color="#2d2d2d", alpha=0.4)
        
        self.fig.tight_layout()
        self.canvas.draw_idle()
        
    def load_sample_data_on_startup(self):
        sample_path = "sample_chat.txt"
        if os.path.exists(sample_path):
            try:
                with open(sample_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.parse_and_analyze_raw_text(content)
            except Exception:
                pass

    # =====================================================================
    # LIVE SYNC CONTROL LOGIC (SELENIUM CORE)
    # =====================================================================
    def toggle_live_sync(self):
        if not SELENIUM_AVAILABLE:
            messagebox.showerror("Dependencies Missing", "Selenium libraries are missing. Please run:\npip install selenium webdriver-manager")
            return
            
        if self.sync_active:
            self.stop_live_sync()
        else:
            self.start_live_sync()
            
    def start_live_sync(self):
        self.sync_active = True
        self.btn_live_sync.configure(text="🛑 Stop Syncing", bg="#ff5555", activebackground="#ff3333")
        
        # Launch driver in background thread
        self.sync_thread = threading.Thread(target=self.live_sync_loop, daemon=True)
        self.sync_thread.start()
        
    def stop_live_sync(self):
        self.sync_active = False
        self.btn_live_sync.configure(text="⚡ Sync with WhatsApp Web", bg="#1d9bf0", activebackground="#0c85d0")
        self.update_sync_status("Disconnected", "#888888")
        
    def update_sync_status(self, text, color):
        # Update thread-safe status label
        self.root.after(0, lambda: self.lbl_sync_status.configure(text=f"● Status: {text}", fg=color))
        
    def live_sync_loop(self):
        try:
            self.update_sync_status("Launching Chrome...", "#ffb86c")
            
            chrome_options = webdriver.ChromeOptions()
            profile_dir = os.path.abspath(os.path.join(os.getcwd(), '.whatsapp_profile'))
            chrome_options.add_argument(f"user-data-dir={profile_dir}")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--log-level=3")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.get("https://web.whatsapp.com")
            
            self.update_sync_status("Scan QR Code...", "#ff5555")
            
            # Wait for main page to load
            wait = WebDriverWait(self.driver, 90)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div#pane-side, div[role='textbox']")))
            
            self.update_sync_status("Connected!", "#50fa7b")
            
            while self.sync_active:
                time.sleep(2.5)
                
                if not self.sync_active:
                    break
                    
                # 1. Grab chat header name
                try:
                    chat_header = self.driver.find_element(By.CSS_SELECTOR, "div#main header")
                    name_element = chat_header.find_element(By.CSS_SELECTOR, "span[title]")
                    chat_name = name_element.get_attribute("title")
                except Exception:
                    chat_name = None
                    
                if not chat_name:
                    self.update_sync_status("Open a Chat...", "#ffb86c")
                    continue
                    
                self.update_sync_status(f"Syncing: {chat_name}", "#50fa7b")
                
                # 2. Extract DOM messages inside .copyable-text
                try:
                    message_elements = self.driver.find_elements(By.CSS_SELECTOR, "div#main .copyable-text")
                    live_messages = []
                    
                    for elem in message_elements:
                        pre_text = elem.get_attribute("data-pre-plain-text")
                        if not pre_text:
                            continue
                            
                        # Parse time/sender
                        match = re.match(r'^\[(.*)\]\s*([^:]+):\s*$', pre_text)
                        if not match:
                            continue
                            
                        dt_part, sender = match.groups()
                        parts = dt_part.split(',')
                        date_str, time_str = None, None
                        for p in parts:
                            p = p.strip()
                            if '/' in p or '-' in p:
                                date_str = p
                            elif ':' in p:
                                time_str = p
                                
                        if not date_str or not time_str:
                            continue
                            
                        dt = parse_datetime(date_str, time_str)
                        if not dt:
                            dt = datetime.now()
                            
                        # Clean text body
                        full_text = elem.text.strip()
                        lines = full_text.split('\n')
                        cleaned_lines = []
                        for line in lines:
                            line_s = line.strip()
                            if re.match(r'^\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?$', line_s):
                                continue
                            if line_s in {"Read", "Delivered", "Sent", "Pending"}:
                                continue
                            cleaned_lines.append(line)
                            
                        msg_text = "\n".join(cleaned_lines).strip()
                        
                        live_messages.append({
                            'datetime': dt,
                            'sender': sender.strip(),
                            'message': msg_text
                        })
                        
                    if live_messages:
                        self.root.after(0, self.update_live_data, live_messages, chat_name)
                        
                except Exception:
                    pass
                    
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Automation Error", f"Live Sync encountered an error:\n{e}"))
            self.root.after(0, self.stop_live_sync)
        finally:
            self.root.after(0, self.cleanup_driver)
            
    def update_live_data(self, live_messages, chat_name):
        self.parsed_messages = live_messages
        self.analyzed_metrics = analyze_chat_metrics(self.parsed_messages)
        
        senders = list(self.analyzed_metrics.keys())
        current_selection = self.combo_sender.get()
        
        self.combo_sender.configure(values=senders)
        
        # Auto-focus on header chat sender
        if senders:
            if chat_name in senders:
                self.combo_sender.set(chat_name)
            elif current_selection not in senders:
                self.combo_sender.set(senders[0])
                
            self.on_sender_change(None)
            
    def cleanup_driver(self):
        self.sync_active = False
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    # =====================================================================
    # TAB 2: GUIDE REFERENCE POPULATION
    # =====================================================================
    def setup_guide_tab(self):
        self.tab_guide.rowconfigure(0, weight=1)
        self.tab_guide.columnconfigure(0, weight=1)
        
        self.txt = scrolledtext.ScrolledText(
            self.tab_guide, wrap=tk.WORD, bg="#1e1e1e", fg="#eeeeee",
            insertbackground="white", highlightthickness=0, bd=0,
            padx=30, pady=25, font=("Segoe UI", 10)
        )
        self.txt.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        self.populate_guide_content()
        
    def populate_guide_content(self):
        self.txt.configure(state='normal')
        self.txt.delete('1.0', tk.END)
        
        self.txt.tag_configure("title", font=("Segoe UI", 18, "bold"), foreground="#1d9bf0", spacing1=15, spacing3=12)
        self.txt.tag_configure("h1", font=("Segoe UI", 13, "bold"), foreground="#50fa7b", spacing1=20, spacing3=8)
        self.txt.tag_configure("h2", font=("Segoe UI", 11, "bold"), foreground="#bd93f9", spacing1=12, spacing3=6)
        self.txt.tag_configure("body", font=("Segoe UI", 10), foreground="#cccccc", spacing1=4, spacing2=4)
        self.txt.tag_configure("code_block", font=("Consolas", 9), foreground="#f1fa8c", background="#121212", lmargin1=20, lmargin2=20, spacing1=6, spacing3=6)
        self.txt.tag_configure("bullet", font=("Segoe UI", 10), foreground="#dddddd", lmargin1=20, lmargin2=30, spacing1=3, spacing2=3)
        
        self.txt.insert(tk.END, "🎓 WhatsApp NLP Sentiment & Interest Analyzer Study Guide\n", "title")
        self.txt.insert(tk.END, "Welcome to the WhatsApp NLP Learning Center. This dashboard parses messaging logs, applies customized text analysis pipelines, and classifies engagement profiles.\n\n", "body")
        
        self.txt.insert(tk.END, "1. NLP & Regex Tokenization\n", "h1")
        self.txt.insert(tk.END, "Before analyzing sentiment, raw conversational text exports must be parsed. The script extracts metadata using regular expressions (Regex):\n", "body")
        self.txt.insert(tk.END, " • iOS Pattern: matches bracketed timestamps, e.g. [18/06/2026, 10:15:30] Sender: Message\n", "bullet")
        self.txt.insert(tk.END, " • Android Pattern: matches dashed timestamps, e.g. 18/06/2026, 10:15 - Sender: Message\n", "bullet")
        self.txt.insert(tk.END, "The tokenizer separates timestamps, sender tags, and body texts. It filters group invitations and system encryption logs. For multi-line entries, it detects lines without a time-header and appends them to the preceding entry.\n\n", "body")
        
        self.txt.insert(tk.END, "2. Selenium Live Scraper Loop\n", "h1")
        self.txt.insert(tk.END, "To sync messages directly from your live WhatsApp account, we introduce Selenium browser automation:\n", "body")
        self.txt.insert(tk.END, " • Profile Directory Preservation: The browser saves authentication cache details (cookies/session data) in the local folder '.whatsapp_profile'. Scanning the QR code once is sufficient to stay logged in across subsequent sessions.\n", "bullet")
        self.txt.insert(tk.END, " • Active Chat Monitor: The background loop locates the contact title by searching for 'span[title]' inside the right-hand 'header' block. If the contact name changes, the dashboard repoints the graphs automatically.\n", "bullet")
        self.txt.insert(tk.END, " • copyable-text Scraping: The scraper loop fetches visible messages by searching for '.copyable-text' nodes. It extracts metadata attributes from 'data-pre-plain-text' and strips out timing tags (e.g. '10:15', 'Read') from the element text.\n\n", "body")
        
        self.txt.insert(tk.END, "3. Lexicon-Based Sentiment Engine\n", "h1")
        self.txt.insert(tk.END, "Since standard libraries like NLTK or transformers might not be installed, we implement a custom Rule-Based Lexicon Sentiment Engine. Words are parsed and scored using dictionaries:\n", "body")
        
        self.txt.insert(tk.END, "Positive & Negative Dictionaries\n", "h2")
        self.txt.insert(tk.END, "Words are scanned and lookups apply scores: +1.0 for words like 'awesome' and 'love'; -1.0 for words like 'worst' and 'late'.\n\n", "body")
        
        self.txt.insert(tk.END, "Negation Handlers\n", "h2")
        self.txt.insert(tk.END, "Negation words ('not', 'dont', 'never') toggle a temporary timer. For the next two scanned words, their lookup scores are multiplied by -1.0. For example, 'not good' results in a negative score (-1.0) rather than positive (+1.0).\n\n", "body")
        
        self.txt.insert(tk.END, "Booster Word Intensity\n", "h2")
        self.txt.insert(tk.END, "Booster words ('very', 'so', 'extremely') raise the emotional intensity of the succeeding word. Scoring multiplies the target word's score by 1.5. For example, 'so happy' yields +1.5.\n\n", "body")
        
        self.txt.insert(tk.END, "Emoji Emotional Weights\n", "h2")
        self.txt.insert(tk.END, "Emojis carry huge emotional intent in chats. The engine maps key emojis to weights (e.g. ❤️ gives +1.5, 😊 gives +1.0, while 😭 and 😡 subtract -1.5). These scores are summed directly.\n\n", "body")
        
        self.txt.insert(tk.END, "4. Profiling Conversational Interest\n", "h1")
        self.txt.insert(tk.END, "To calculate the sentimental interest of a participant, the algorithm builds a composite Interest Score (0 to 100) based on four metrics:\n\n", "body")
        
        self.txt.insert(tk.END, "a) Response Speed (Max 30 Points)\n", "h2")
        self.txt.insert(tk.END, "Measures the time elapsed between one participant's message and the target user's reply. To avoid counting overnight breaks, response durations exceeding 8 hours are ignored. A fast response speed (< 5 minutes) yields higher points.\n\n", "body")
        
        self.txt.insert(tk.END, "b) Word Count Volume (Max 25 Points)\n", "h2")
        self.txt.insert(tk.END, "Reflects the depth of interest. Longer, detailed answers indicate a higher level of conversational commitment than short, brief responses (e.g., 'Ok', 'Yeah').\n\n", "body")
        
        self.txt.insert(tk.END, "c) Sentiment Average (Max 25 Points)\n", "h2")
        self.txt.insert(tk.END, "An average positive sentiment indicates warmth, joy, and emotional connection, whereas negative scores can reveal stress, lack of alignment, or coldness.\n\n", "body")
        
        self.txt.insert(tk.END, "d) Emoji Frequency (Max 20 Points)\n", "h2")
        self.txt.insert(tk.END, "High emoji density indicates highly expressive, enthusiastic communication.\n\n", "body")
        
        self.txt.insert(tk.END, "Classification Scale:\n", "body")
        self.txt.insert(tk.END, " • High Interest (Score >= 75): Very enthusiastic, fast replies, positive, expressive.\n", "bullet")
        self.txt.insert(tk.END, " • Casual / Friendly (Score 50-74): Engaged, standard reply times, friendly.\n", "bullet")
        self.txt.insert(tk.END, " • Low Interest / Polite (Score < 50): Slow, brief, or formal replies.\n\n", "bullet")
        
        self.txt.insert(tk.END, "5. Key Python Custom Algorithms\n", "h1")
        self.txt.insert(tk.END, "Below are structural snippets of the calculations used:\n\n", "body")
        
        self.txt.insert(tk.END, "Tokenization & Lexicons Processing:\n", "h2")
        self.txt.insert(tk.END, " words = re.findall(r'[a-zA-Z]+', message.lower())\n for word in words:\n     if word in NEGATION_WORDS: is_negated = True\n     # ... apply weight adjustments and accumulate scores\n", "code_block")
        
        self.txt.insert(tk.END, "Response Velocity Calculator:\n", "h2")
        self.txt.insert(tk.END, " for idx in range(1, len(chat_df)):\n     if chat_df.sender[idx-1] != chat_df.sender[idx]:\n         time_delta = chat_df.time[idx] - chat_df.time[idx-1]\n         if time_delta < 8 hours: response_times.append(time_delta)\n", "code_block")
        
        self.txt.configure(state='disabled')

# =====================================================================
# STEP 5: APPLICATION ENTRY POINT
# =====================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = WhatsAppAnalyzerApp(root)
    
    def on_closing():
        app.cleanup_driver()
        plt.close('all')
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
