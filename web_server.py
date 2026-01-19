"""
Echo V3 - Web Interface
Premium Dark UI with Glassmorphism
Tabs: Chat, Tasks, Memory
"""

import os
import uuid
import datetime
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

import database
import llm_client
import httpx
import bettershift_proxy
import bettershift_client

# Initialize DB
database.init_db()

from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse, FileResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

# Global State
SESSIONS = {}
CONFIG_FILE = "user_config.json"
import json
import mlx_embeddings

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except: pass
    return {}

def save_config_val(key, val):
    cfg = load_config()
    cfg[key] = val
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)

def startup():
    # Load config on startup
    cfg = load_config()
    if "embed_model" in cfg:
        print(f"⚙️ Restoring embed model: {cfg['embed_model']}")
        mlx_embeddings.set_model_path(cfg['embed_model'])
    else:
        # Save default if not exists
        save_config_val("embed_model", mlx_embeddings._current_model_path)
    


# ============ CSS & ASSETS ============
CSS = """
/* New Cyberpunk Design */
:root {
    --bg-deep: #050510;
    --bg-sidebar: #0a0a1f;
    --neon-purple: #bc13fe;
    --neon-blue: #00f3ff;
    --neon-pink: #ff0055;
    --neon-green: #39ff14;
    --glass: rgba(255, 255, 255, 0.02);
    --glass-border: rgba(255, 255, 255, 0.08);
    --text-main: #ffffff;
    --text-dim: #8888aa;
    --message-user: rgba(0, 243, 255, 0.1);
    --message-ai: rgba(188, 19, 254, 0.1);
}

* { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }

body {
    background: var(--bg-deep);
    color: var(--text-main);
    font-family: 'Rajdhani', sans-serif;
    overflow: hidden;
    height: 100vh;
}

/* Animated Background */
.cyber-grid {
    position: fixed;
    top: 0; left: 0; width: 100%; height: 100%;
    background-image: 
        repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0, 243, 255, 0.02) 2px, rgba(0, 243, 255, 0.02) 4px),
        repeating-linear-gradient(90deg, transparent, transparent 2px, rgba(188, 19, 254, 0.02) 2px, rgba(188, 19, 254, 0.02) 4px);
    background-size: 60px 60px;
    animation: gridScroll 20s linear infinite;
    z-index: 0; pointer-events: none;
}
@keyframes gridScroll {
    0% { transform: translateY(0); }
    100% { transform: translateY(60px); }
}

.orb {
    position: fixed;
    border-radius: 50%;
    filter: blur(80px);
    opacity: 0.15;
    pointer-events: none;
    z-index: 0;
    animation: float 15s ease-in-out infinite;
}
.orb-1 {
    width: 400px; height: 400px;
    background: radial-gradient(circle, var(--neon-purple), transparent);
    top: -100px; right: -100px;
}
.orb-2 {
    width: 500px; height: 500px;
    background: radial-gradient(circle, var(--neon-blue), transparent);
    bottom: -150px; left: -150px;
    animation-delay: 7s;
}
@keyframes float {
    0%, 100% { transform: translate(0, 0) scale(1); }
    50% { transform: translate(30px, -30px) scale(1.1); }
}

/* Main Layout */
.app-container {
    display: flex;
    height: 100vh;
    position: relative;
    z-index: 1;
}

/* Sidebar */
.sidebar {
    width: 280px;
    background: var(--bg-sidebar);
    border-right: 1px solid var(--glass-border);
    display: flex;
    flex-direction: column;
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    transition: transform 0.3s ease;
    z-index: 100;
}

.sidebar-header {
    padding: 1.5rem;
    border-bottom: 1px solid var(--glass-border);
}

.logo {
    font-family: 'Orbitron', sans-serif;
    font-size: 2rem;
    font-weight: 900;
    letter-spacing: 0.15em;
    background: linear-gradient(135deg, #fff 0%, var(--neon-blue) 50%, var(--neon-purple) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.5rem;
}

.version {
    font-size: 0.75rem;
    color: var(--text-dim);
    letter-spacing: 0.2em;
}

.status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.8rem;
    font-size: 0.85rem;
    color: var(--neon-blue);
}

.pulse-dot {
    width: 8px; height: 8px;
    background: var(--neon-blue);
    border-radius: 50%;
    box-shadow: 0 0 10px var(--neon-blue);
    animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

/* Model Section in Sidebar */
.model-section {
    padding: 1rem 1.5rem;
    border-bottom: 1px solid var(--glass-border);
}

.model-section select {
    width: 100%;
    background: var(--glass);
    border: 1px solid var(--glass-border);
    color: var(--text-main);
    padding: 0.6rem;
    border-radius: 8px;
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.3s ease;
    margin-top: 0.5rem;
}

.model-section select:hover {
    border-color: var(--neon-blue);
    box-shadow: 0 0 10px rgba(0, 243, 255, 0.2);
}

.model-section label {
    font-size: 0.75rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

/* Navigation */
.nav {
    padding: 1rem;
    flex: 1;
    overflow-y: auto;
}

.nav-item {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    margin-bottom: 0.5rem;
    border-radius: 12px;
    background: var(--glass);
    border: 1px solid transparent;
    cursor: pointer;
    transition: all 0.3s ease;
    text-decoration: none;
    color: var(--text-main);
    position: relative;
    overflow: hidden;
}

.nav-item::before {
    content: '';
    position: absolute;
    left: 0; top: 0;
    height: 100%; width: 3px;
    background: var(--item-color);
    transform: scaleY(0);
    transition: transform 0.3s ease;
}

.nav-item:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: var(--item-color);
    box-shadow: 0 0 20px var(--item-glow);
}
.nav-item:hover::before { transform: scaleY(1); }

.nav-item.active {
    background: rgba(255, 255, 255, 0.08);
    border-color: var(--item-color);
}
.nav-item.active::before { transform: scaleY(1); }

.nav-icon {
    font-size: 1.5rem;
    filter: drop-shadow(0 0 8px rgba(255, 255, 255, 0.3));
}

.nav-text { flex: 1; }

.nav-title {
    font-weight: 700;
    font-size: 1rem;
    margin-bottom: 0.2rem;
}

.nav-desc {
    font-size: 0.75rem;
    color: var(--text-dim);
}

/* Nav Item Colors */
.nav-item:nth-child(1) { --item-color: var(--neon-blue); --item-glow: rgba(0, 243, 255, 0.2); }
.nav-item:nth-child(2) { --item-color: var(--neon-pink); --item-glow: rgba(255, 0, 85, 0.2); }
.nav-item:nth-child(3) { --item-color: var(--neon-purple); --item-glow: rgba(188, 19, 254, 0.2); }
.nav-item:nth-child(4) { --item-color: var(--neon-green); --item-glow: rgba(57, 255, 20, 0.2); }
.nav-item:nth-child(5) { --item-color: #ff9500; --item-glow: rgba(255, 149, 0, 0.2); }

/* Main Content */
.main-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    position: relative;
}

.chat-header {
    padding: 1.5rem;
    border-bottom: 1px solid var(--glass-border);
    background: rgba(10, 10, 31, 0.5);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.chat-title {
    font-family: 'Orbitron', sans-serif;
    font-size: 1.3rem;
    font-weight: 700;
    color: var(--neon-blue);
}

.chat-subtitle {
    font-size: 0.85rem;
    color: var(--text-dim);
    margin-top: 0.3rem;
}

/* Messages */
.messages {
    flex: 1;
    overflow-y: auto;
    padding: 2rem;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    scroll-behavior: smooth;
}

.message {
    display: flex;
    gap: 1rem;
    animation: messageSlide 0.3s ease;
}
@keyframes messageSlide {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.message.user { flex-direction: row-reverse; }

.message-avatar {
    width: 40px; height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
    flex-shrink: 0;
    border: 2px solid;
}

.message.user .message-avatar {
    background: var(--message-user);
    border-color: var(--neon-blue);
    box-shadow: 0 0 15px rgba(0, 243, 255, 0.3);
}

.message.ai .message-avatar {
    background: var(--message-ai);
    border-color: var(--neon-purple);
    box-shadow: 0 0 15px rgba(188, 19, 254, 0.3);
}

.message-content {
    max-width: 70%;
    background: var(--glass);
    border: 1px solid var(--glass-border);
    border-radius: 16px;
    padding: 1rem 1.2rem;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
}

.message.user .message-content {
    background: var(--message-user);
    border-color: rgba(0, 243, 255, 0.2);
}

.message.ai .message-content {
    background: var(--message-ai);
    border-color: rgba(188, 19, 254, 0.2);
}

.message-text { line-height: 1.6; }

.message-time {
    font-size: 0.7rem;
    color: var(--text-dim);
    margin-top: 0.5rem;
}

/* Input Area */
.input-area {
    padding: 1.5rem;
    border-top: 1px solid var(--glass-border);
    background: rgba(10, 10, 31, 0.5);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
}

.input-container {
    display: flex;
    gap: 1rem;
    align-items: center; /* Changed from flex-end for better alignment */
    max-width: 900px;
    margin: 0 auto;
}

.input-wrapper {
    flex: 1;
    position: relative;
}

.message-input {
    width: 100%;
    background: var(--glass);
    border: 2px solid var(--glass-border);
    border-radius: 16px;
    padding: 1rem 1.2rem;
    color: var(--text-main);
    font-family: 'Rajdhani', sans-serif;
    font-size: 1rem;
    resize: none;
    min-height: 50px;
    max-height: 150px;
    transition: all 0.3s ease;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
}

.message-input:focus {
    outline: none;
    border-color: var(--neon-blue);
    box-shadow: 0 0 20px rgba(0, 243, 255, 0.2);
}

.message-input::placeholder {
    color: var(--text-dim);
}

#mic-btn {
    width: 50px; height: 50px;
    border-radius: 12px;
    border: none;
    background: var(--glass);
    border: 1px solid var(--glass-border);
    color: var(--text-dim);
    font-size: 1.3rem;
    cursor: pointer;
    transition: all 0.3s ease;
    flex-shrink: 0;
}
#mic-btn:hover { 
    color: var(--neon-blue); 
    border-color: var(--neon-blue);
    box-shadow: 0 0 15px rgba(0, 243, 255, 0.3);
}
#mic-btn.recording { 
    color: var(--neon-pink); 
    border-color: var(--neon-pink);
    box-shadow: 0 0 15px rgba(255, 0, 85, 0.5);
    animation: pulse 1s infinite; 
}

.send-btn {
    width: 50px; height: 50px;
    border-radius: 12px;
    border: none;
    background: linear-gradient(135deg, var(--neon-blue), var(--neon-purple));
    color: #fff;
    font-size: 1.5rem;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 4px 15px rgba(0, 243, 255, 0.3);
    flex-shrink: 0;
}
.send-btn:hover { 
    transform: translateY(-2px); 
    box-shadow: 0 6px 25px rgba(0, 243, 255, 0.5); 
}
.send-btn:active { transform: translateY(0); }

/* Common Pages */
.page-container {
    padding: 2rem;
    max-width: 900px;
    margin: 0 auto;
    width: 100%;
    overflow-y: auto;
    flex: 1;
}

.page-header {
    margin-bottom: 2rem;
}

h2 {
    font-family: 'Orbitron', sans-serif;
    font-size: 1.8rem;
    color: var(--neon-blue);
    margin-bottom: 0.5rem;
    text-transform: uppercase;
    letter-spacing: 2px;
}

.subtitle {
    color: var(--text-dim);
    font-size: 0.9rem;
    letter-spacing: 1px;
}

/* Tasks & Memory Cards */
.task-card, .info-card {
    background: var(--glass);
    border: 1px solid var(--glass-border);
    padding: 1.2rem;
    margin-bottom: 0.8rem;
    border-radius: 12px;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    gap: 1rem;
}

.task-card:hover, .info-card:hover {
    border-color: var(--neon-purple);
    box-shadow: 0 0 20px rgba(188, 19, 254, 0.2);
    background: rgba(255, 255, 255, 0.04);
}

.task-text {
    flex: 1;
    line-height: 1.5;
}

.checkbox {
    width: 22px; height: 22px;
    border: 2px solid var(--text-dim);
    border-radius: 6px;
    cursor: pointer;
    position: relative;
    appearance: none;
    -webkit-appearance: none;
    transition: all 0.3s ease;
    flex-shrink: 0;
}

.checkbox:hover {
    border-color: var(--neon-purple);
    box-shadow: 0 0 10px rgba(188, 19, 254, 0.3);
}

.checkbox:checked {
    background: var(--neon-purple);
    border-color: var(--neon-purple);
    box-shadow: 0 0 10px rgba(188, 19, 254, 0.5);
}

.checkbox:checked::after {
    content: '✓';
    position: absolute;
    left: 4px;
    top: 0px;
    color: #fff;
    font-size: 14px;
    font-weight: bold;
}

.task-card.completed .task-text {
    opacity: 0.5;
    text-decoration: line-through;
}

/* Form inputs for pages */
.page-container input[type="text"] {
    width: 100%;
    background: var(--glass);
    border: 2px solid var(--glass-border);
    border-radius: 12px;
    padding: 1rem;
    color: var(--text-main);
    font-family: 'Rajdhani', sans-serif;
    font-size: 1rem;
    transition: all 0.3s ease;
}

.page-container input[type="text"]:focus {
    outline: none;
    border-color: var(--neon-blue);
    box-shadow: 0 0 15px rgba(0, 243, 255, 0.2);
}

/* Mobile Menu Toggle */
.menu-toggle {
    display: none;
    position: fixed;
    top: 1rem;
    left: 1rem;
    width: 50px;
    height: 50px;
    border-radius: 12px;
    background: var(--bg-sidebar);
    border: 1px solid var(--glass-border);
    color: var(--neon-blue);
    font-size: 1.5rem;
    cursor: pointer;
    z-index: 1000;
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    align-items: center;
    justify-content: center;
}

/* Mobile Styles */
@media (max-width: 768px) {
    .sidebar {
        position: fixed;
        left: 0;
        top: 0;
        height: 100vh;
        width: 85vw;
        max-width: 320px;
        z-index: 999;
        transform: translateX(-100%);
        box-shadow: 2px 0 20px rgba(0, 0, 0, 0.5);
    }
    
    .sidebar.open { transform: translateX(0); }
    
    .menu-toggle { display: flex; }
    
    /* Messages optimization */
    .message-content { max-width: 90%; }
    
    .messages { 
        padding: 1rem 0.8rem; 
        gap: 1rem;
    }
    
    .message { 
        margin-bottom: 1rem; 
    }
    
    .bubble {
        font-size: 0.95rem;
        padding: 0.9rem 1rem;
    }
    
    /* Input area optimization - CRITICAL iOS FIX */
    .input-area { 
        padding: 0.8rem;
        gap: 0.5rem;
    }
    
    .message-input {
        font-size: 16px !important; /* Prevents iOS zoom-in */
        padding: 0.9rem 1rem;
        min-height: 44px; /* iOS recommended touch target */
    }
    
    #mic-btn, .send-btn {
        width: 44px;
        height: 44px; /* iOS minimum touch target */
        flex-shrink: 0;
    }
    
    /* Page content */
    .page-container { 
        padding: 1rem 0.8rem; 
    }
    
    h2 { 
        font-size: 1.4rem;
        margin-bottom: 0.8rem;
    }
    
    /* Header optimization - HIDE MODEL SELECTORS ON MOBILE */
    .chat-header {
        padding: 0.8rem !important;
        flex-direction: column;
        align-items: flex-start !important;
        gap: 0;
    }
    
    /* Hide model selection dropdowns on mobile */
    .header-model-selector {
        display: none !important;
    }
    
    .chat-info {
        width: 100%;
        margin-bottom: 0.5rem;
    }
    
    .chat-controls {
        width: 100%;
        justify-content: flex-start;
        flex-wrap: wrap;
    }
    
    .chat-title { 
        font-size: 1rem;
    }
    
    .chat-subtitle {
        font-size: 0.75rem;
        display: none; /* Hide subtitle on mobile to save space */
    }
    
    .date-time {
        font-size: 0.7rem;
        display: none; /* Hide on mobile */
    }
    
    /* Sidebar improvements - FIX LOGO OVERLAP */
    .sidebar-header {
        padding: 1.2rem;
        padding-left: 4.5rem; /* More space from hamburger menu */
    }
    
    .logo {
        font-size: 1.6rem;
    }
    
    .nav {
        padding: 0.8rem;
    }
    
    .nav-item {
        padding: 0.9rem;
        margin-bottom: 0.4rem;
    }
    
    .nav-title {
        font-size: 0.95rem;
    }
    
    .nav-desc {
        font-size: 0.7rem;
    }
    
    /* Task cards */
    .task-card, .info-card {
        padding: 1rem;
    }
    
    /* Better scrolling on mobile */
    .messages, .page-container {
        -webkit-overflow-scrolling: touch;
    }
}

/* Scrollbar */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--glass-border); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.2); }
"""

# ============ RENDERERS ============

def get_base_html(active_tab, content, session_id):
    def nav_link(name, desc, icon, endpoint, tab_key):
        active = 'active' if active_tab == tab_key else ''
        return f'''
                <a href="{endpoint}" class="nav-item {active}">
                    <div class="nav-icon">{icon}</div>
                    <div class="nav-text">
                        <div class="nav-title">{name}</div>
                        <div class="nav-desc">{desc}</div>
                    </div>
                </a>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#050510">
    <title>ECHO V3 // Neural Interface</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;500;700&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <style>{CSS}</style>
</head>
<body>
    <div class="cyber-grid"></div>
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    
    <button class="menu-toggle" onclick="toggleSidebar()">☰</button>
    
    <div class="app-container">
        <!-- Sidebar -->
        <div class="sidebar" id="sidebar">
            <div class="sidebar-header">
                <div class="logo">ECHO</div>
                <div class="version">V3.0 // NEURAL INTERFACE</div>
                <div class="status">
                    <div class="pulse-dot"></div>
                    <span>ONLINE</span>
                </div>
            </div>
            
            <!-- Model Selection -->
            <div class="model-section">
                <!-- Active Model Badge (Auto-refresh every 10s) -->
                <div hx-get="/models/active" hx-trigger="load" style="margin-bottom: 0.5rem;">
                    <span style="color:var(--text-dim); font-size:0.7rem">Checking...</span>
                </div>
                
                <!-- Model Selector -->
                <div hx-get="/models" hx-trigger="load">
                    <span style="color:var(--text-dim); font-size:0.8rem">Loading models...</span>
                </div>
            </div>
            
            <!-- Coverage Widget (The "Now" HUD) -->
            <div style="margin: 1rem 0.5rem; padding: 0.75rem; background: rgba(0, 243, 255, 0.05); border: 1px solid rgba(0, 243, 255, 0.2); border-radius: 8px;">
                <div style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; color: var(--neon-blue); margin-bottom: 0.5rem; font-weight: 600;">
                    ⚡ COVERAGE
                </div>
                <div id="presence-widget" 
                     hx-get="/status/presence" 
                     hx-trigger="load"
                     style="min-height: 40px;">
                    <div style="color:var(--text-dim); font-size:0.8rem; text-align:center;">Click to update</div>
                    <button 
                        hx-get="/status/presence"
                        hx-target="#presence-widget"
                        style="width:100%; margin-top:0.3rem; background:rgba(0,243,255,0.1); border:1px solid var(--neon-blue); color:var(--neon-blue); padding:0.3rem; border-radius:6px; cursor:pointer; font-size:0.65rem;"
                        title="Refresh coverage">
                        🔄 Update
                    </button>
                </div>
            </div>
            
            <nav class="nav">
                {nav_link("Neural Link", "AI Chat Interface", "💬", "/", "chat")}
                {nav_link("Mission Control", "Task Management", "✅", "/tasks", "tasks")}
                {nav_link("Core Memory", "Data Logs", "🧠", "/memory", "memory")}
                {nav_link("Chrono Sync", "BetterShift Protocol", "📆", "/schedule", "schedule")}
                {nav_link("Archives", "Historical Records", "🗄️", "/archives", "archives")}
            </nav>
        </div>
        
        <!-- Main Content -->
        <div class="main-content">
            {content}
        </div>
    </div>
    
    <script>
        function toggleSidebar() {{
            document.getElementById('sidebar').classList.toggle('open');
        }}
        
        // Close sidebar on mobile when clicking outside
        document.addEventListener('click', function(e) {{
            const sidebar = document.getElementById('sidebar');
            const menuToggle = document.querySelector('.menu-toggle');
            
            if (window.innerWidth <= 768 && 
                sidebar.classList.contains('open') && 
                !sidebar.contains(e.target) && 
                !menuToggle.contains(e.target)) {{
                sidebar.classList.remove('open');
            }}
        }});
        
        // Global Model Sync - Ensures all dropdowns match the active badge
        // DEBOUNCED to prevent infinite loops
        let syncTimeout = null;
        document.body.addEventListener('htmx:afterSettle', function(evt) {{
            // Only sync if it's a model-related update
            if (evt.detail.target && (
                evt.detail.target.id === 'model-sidebar' || 
                evt.detail.xhr.responseURL.includes('/models')
            )) {{
                clearTimeout(syncTimeout);
                syncTimeout = setTimeout(syncDropdownsWithReality, 500);
            }}
        }});
        
        window.addEventListener('load', syncDropdownsWithReality);
        
        function syncDropdownsWithReality() {{
            // Find the active badge showing the currently loaded model
            let activeBadge = Array.from(document.querySelectorAll('span, div')).find(el => 
                (el.textContent.includes('ACTIVE:') || el.textContent.includes('LOADED:')) && 
                (el.textContent.includes('Falcon') || el.textContent.includes('Llama') || 
                 el.textContent.includes('Qwen') || el.textContent.includes('Phi'))
            );
            
            if (activeBadge) {{
                // Extract model name from badge text
                let fullText = activeBadge.textContent;
                let modelName = fullText.split(/ACTIVE:|LOADED:/)[1].trim().split(' ')[0].split('•')[0].trim();
                
                // Force all model dropdowns to select this value
                let allDropdowns = document.querySelectorAll('select[name="model_path"], select.model-selector');
                
                allDropdowns.forEach(dropdown => {{
                    for (let i = 0; i < dropdown.options.length; i++) {{
                        if (dropdown.options[i].text.includes(modelName) || 
                            dropdown.options[i].value.includes(modelName)) {{
                            dropdown.selectedIndex = i;
                            break;
                        }}
                    }}
                }});
            }}
        }}
    </script>
</body>
</html>'''

def render_chat_view(history):
    messages_html = ""
    for m in history:
        role = m["role"]
        cls = "user" if role == "user" else "ai"
        avatar = "⚛" if role == "user" else "⚡"
        messages_html += f'''
            <div class="message {cls}">
                <div class="message-avatar">{avatar}</div>
                <div class="message-content">
                    <div class="message-text">{m["content"]}</div>
                </div>
            </div>'''
    
    if not history:
        messages_html = '''
            <div class="message ai">
                <div class="message-avatar">⚡</div>
                <div class="message-content">
                    <div class="message-text">Hello! I'm Echo V3, your local AI assistant. How can I help you today?</div>
                </div>
            </div>'''
        
    return f'''
            <div class="chat-header">
                <div class="chat-info">
                    <div class="chat-title">Neural Link Active</div>
                    <div class="chat-subtitle">Direct interface with Echo V3 AI</div>
                </div>
                <div class="chat-controls" style="display: flex; gap: 0.5rem; align-items: center;">
                    <button 
                        hx-post="/wake" 
                        hx-target="#messages" 
                        hx-swap="beforeend"
                        style="background: rgba(0, 243, 255, 0.1); border: 1px solid var(--neon-blue); color: var(--neon-blue); padding: 0.4rem 0.8rem; border-radius: 8px; cursor: pointer; font-family: 'Rajdhani', sans-serif; font-size: 0.85rem; font-weight: 500; transition: all 0.3s;"
                        onmouseover="this.style.background='rgba(0, 243, 255, 0.2)'; this.style.boxShadow='0 0 10px rgba(0, 243, 255, 0.3)'"
                        onmouseout="this.style.background='rgba(0, 243, 255, 0.1)'; this.style.boxShadow='none'"
                        title="Wake up the AI server">
                        🌅 WAKE
                    </button>
                    <button 
                        hx-post="/sleep" 
                        hx-target="#messages" 
                        hx-swap="beforeend"
                        style="background: rgba(188, 19, 254, 0.1); border: 1px solid var(--neon-purple); color: var(--neon-purple); padding: 0.4rem 0.8rem; border-radius: 8px; cursor: pointer; font-family: 'Rajdhani', sans-serif; font-size: 0.85rem; font-weight: 500; transition: all 0.3s;"
                        onmouseover="this.style.background='rgba(188, 19, 254, 0.2)'; this.style.boxShadow='0 0 10px rgba(188, 19, 254, 0.3)'"
                        onmouseout="this.style.background='rgba(188, 19, 254, 0.1)'; this.style.boxShadow='none'"
                        title="Put the AI server to sleep">
                        😴 SLEEP
                    </button>
                    <button 
                        hx-post="/chat/archive" 
                        hx-target="#messages" 
                        hx-swap="innerHTML"
                        style="background: rgba(255, 0, 85, 0.1); border: 1px solid var(--neon-pink); color: var(--neon-pink); padding: 0.4rem 0.8rem; border-radius: 8px; cursor: pointer; font-family: 'Rajdhani', sans-serif; font-size: 0.85rem; font-weight: 500; transition: all 0.3s;"
                        onmouseover="this.style.background='rgba(255, 0, 85, 0.2)'; this.style.boxShadow='0 0 10px rgba(255, 0, 85, 0.3)'"
                        onmouseout="this.style.background='rgba(255, 0, 85, 0.1)'; this.style.boxShadow='none'"
                        title="Archive current chat and start fresh">
                        🗄️ ARCHIVE
                    </button>
                    <!-- Model indicator - removed to reduce API calls -->
                    <span style="color:var(--neon-blue); font-size:0.8rem" title="Check sidebar for model info">⚡</span>
                </div>
            </div>
            
            <div class="messages" id="messages">
                {messages_html}
            </div>
            
            <div class="input-area">
                <div class="input-container">
                    <button type="button" id="mic-btn" onclick="toggleRecording()" title="Voice input">🎤</button>
                    <div class="input-wrapper">
                        <textarea class="message-input" id="messageInput" name="msg" placeholder="Enter your message..." rows="1"></textarea>
                    </div>
                    <button class="send-btn" onclick="sendMsg()">➤</button>
                </div>
            </div>
    
    <script>
    const messagesContainer = document.getElementById('messages');
    const messageInput = document.getElementById('messageInput');
    
    // Auto-resize textarea
    messageInput.addEventListener('input', function() {{
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 150) + 'px';
    }});
    
    // Send on Enter (Shift+Enter for new line)
    messageInput.addEventListener('keydown', function(e) {{
        if (e.key === 'Enter' && !e.shiftKey) {{
            e.preventDefault();
            sendMsg();
        }}
    }});
    
    function sendMsg() {{
        let msg = messageInput.value.trim();
        if(!msg) return;
        
        // 1. Add User Message
        let userDiv = document.createElement('div');
        userDiv.className = 'message user';
        userDiv.innerHTML = '<div class="message-avatar">⚛</div><div class="message-content"><div class="message-text">' + 
            msg.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;") + '</div></div>';
        messagesContainer.appendChild(userDiv);
        
        // 2. Add Thinking Indicator
        let thinkDiv = document.createElement('div');
        thinkDiv.id = 'thinking-bubble';
        thinkDiv.className = 'message ai';
        thinkDiv.innerHTML = '<div class="message-avatar">⚡</div><div class="message-content"><div class="message-text" style="color:var(--text-dim); font-style:italic">Thinking...</div></div>';
        messagesContainer.appendChild(thinkDiv);
        
        // 3. Clear & Scroll
        messageInput.value = '';
        messageInput.style.height = 'auto';
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // 4. Send via HTMX
        htmx.ajax('POST', '/send', {{target: '#thinking-bubble', swap: 'outerHTML', values: {{msg: msg}}}});
    }}

    // Voice Recording
    let mediaRecorder = null;
    let audioChunks = [];
    let isRecording = false;

    async function toggleRecording() {{
        const btn = document.getElementById('mic-btn');
        
        if (isRecording) {{
            // Stop recording
            mediaRecorder.stop();
            btn.classList.remove('recording');
            btn.textContent = '🎤';
            isRecording = false;
        }} else {{
            // Start recording
            try {{
                const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                
                mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
                mediaRecorder.onstop = async () => {{
                    const audioBlob = new Blob(audioChunks, {{ type: 'audio/webm' }});
                    stream.getTracks().forEach(t => t.stop());
                    
                    // Show transcribing indicator
                    btn.textContent = '⏳';
                    
                    // Send to server for transcription
                    const formData = new FormData();
                    formData.append('audio', audioBlob, 'recording.webm');
                    
                    try {{
                        const resp = await fetch('/voice/transcribe', {{ method: 'POST', body: formData }});
                        const data = await resp.json();
                        
                        if (data.text) {{
                            // Put transcribed text in input and send
                            messageInput.value = data.text;
                            sendMsg();
                        }}
                    }} catch (err) {{
                        console.error('Transcription error:', err);
                    }}
                    
                    btn.textContent = '🎤';
                }};
                
                mediaRecorder.start();
                btn.classList.add('recording');
                btn.textContent = '⏹️';
                isRecording = true;
            }} catch (err) {{
                console.error('Mic access error:', err);
                alert('Could not access microphone');
            }}
        }}
    }}

    // Register service worker for PWA
    if ('serviceWorker' in navigator) {{
        navigator.serviceWorker.register('/static/service-worker.js').catch(console.error);
    }}
    
    // Scroll to bottom on load
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    </script>
    '''

def render_tasks_view():
    tasks = [t for t in database.get_tasks() if t['status'] != 'archived']
    list_html = ""
    if not tasks:
        list_html = '<div style="text-align:center; color:var(--text-dim); margin-top:4rem">All caught up! 🎉</div>'
    
    for t in tasks:
        status = "completed" if t['status'] == 'completed' else ""
        checked = "checked" if t['status'] == 'completed' else ""
        list_html += f'''
            <div class="task-card {status}" id="task-{t['id']}">
                <input type="checkbox" class="checkbox" 
                       hx-post="/tasks/toggle/{t['id']}" 
                       hx-target="#task-{t['id']}" 
                       hx-swap="outerHTML"
                       {checked}>
                <div class="task-text">{t['description']}</div>
            </div>'''
        
    return f'''
            <div class="chat-header">
                <div>
                    <div class="chat-title">Mission Control</div>
                    <div class="chat-subtitle">Task Management System</div>
                </div>
                <span hx-get="/tasks" hx-select=".main-content" hx-target=".main-content" 
                      style="cursor:pointer; font-size:1.2rem; opacity:0.7" title="Refresh">🔄</span>
            </div>
            
            <div class="page-container">
                <form hx-post="/tasks/add" hx-target="#task-list" hx-swap="afterbegin" onsubmit="setTimeout(()=>this.reset(), 10)">
                    <input type="text" name="desc" placeholder="+ Add a new task..." style="margin-bottom: 2rem;">
                </form>
                
                <div id="task-list">{list_html}</div>
            </div>
    '''


def render_schedule_view(calendars=None, error=None):
    calendars = calendars or []
    cal_list = ""
    if error:
        cal_list = f'<div style="color:var(--neon-pink); padding:1rem;">{error}</div>'
    elif not calendars:
        cal_list = '<div style="color:var(--text-dim); text-align:center; margin-top:2rem;">No calendars found.</div>'
    else:
        # Ensure calendars is a list of dicts, not strings or other types
        if isinstance(calendars, str):
            cal_list = f'<div style="color:var(--neon-pink); padding:1rem;">Error: {calendars}</div>'
        else:
            cal_items = []
            for c in calendars:
                # Handle both dict and non-dict items
                if isinstance(c, dict):
                    name = c.get('name', 'Unknown')
                    cal_id = c.get('id', 'Unknown')
                else:
                    name = str(c)
                    cal_id = ''
                    
                cal_items.append(f'''<div class="info-card">
                    <div class="nav-icon">📅</div>
                    <div class="nav-text">
                        <div class="nav-title">{name}</div>
                        <div class="nav-desc">{cal_id}</div>
                    </div>
                </div>''')
            cal_list = f"<div style='display:grid; gap:0.75rem'>{''.join(cal_items)}</div>"

    return f'''
            <div class="chat-header">
                <div>
                    <div class="chat-title">Chrono Sync</div>
                    <div class="chat-subtitle">BetterShift Protocol</div>
                </div>
            </div>
            
            <div class="page-container">
                <p style="color:var(--text-dim); margin-bottom:2rem;">Use the Neural Link to create shifts, presets, and notes.</p>
                {cal_list}
            </div>
    '''

def render_memory_view():
    import sqlite3
    try:
        conn = sqlite3.connect(database.DB_NAME)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM notes ORDER BY created_at DESC LIMIT 30")
        notes = c.fetchall()
        conn.close()
    except Exception as e:
        return f'''
            <div class="chat-header">
                <div>
                    <div class="chat-title">Core Memory</div>
                    <div class="chat-subtitle">Data Logs</div>
                </div>
            </div>
            <div class="page-container">
                <div style="text-align:center; color:var(--neon-pink); margin-top:2rem">DB Error: {e}</div>
            </div>'''
    
    notes_html = ''
    if not notes:
        notes_html = '<div style="text-align:center; color:var(--text-dim); margin-top:2rem;">No memories stored yet.</div>'
    else:
        for n in notes:
            notes_html += f'''
                <div class="info-card" id="note-{n['id']}" style="position:relative;">
                    <div class="nav-icon">💭</div>
                    <div class="nav-text" style="flex:1;">
                        <div style="font-size:0.95rem; line-height:1.5;">{n['content']}</div>
                        <div class="nav-desc" style="margin-top:0.5rem;">{n['created_at'][:10]}</div>
                    </div>
                    <button 
                        hx-delete="/memory/delete/{n['id']}" 
                        hx-target="#note-{n['id']}" 
                        hx-swap="outerHTML"
                        style="background:rgba(255,0,85,0.1); border:1px solid var(--neon-pink); color:var(--neon-pink); padding:0.4rem 0.8rem; border-radius:8px; cursor:pointer; font-size:0.8rem; transition:all 0.3s; flex-shrink:0;"
                        onmouseover="this.style.background='rgba(255,0,85,0.2)'"
                        onmouseout="this.style.background='rgba(255,0,85,0.1)'">
                        🗑️
                    </button>
                </div>'''
    
    return f'''
            <div class="chat-header">
                <div>
                    <div class="chat-title">Core Memory</div>
                    <div class="chat-subtitle">Data Logs & Stored Thoughts</div>
                </div>
            </div>
            
            <div class="page-container">
                {notes_html}
            </div>
    '''

def get_session_id(request):
    # Single global session - all devices share the same chat
    return "echo-main"

# ============ ENDPOINTS ============

async def get_active_model_badge(request):
    """Return the currently active model from MLX server (fresh from /health)."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("http://127.0.0.1:1234/health")
            if resp.status_code == 200:
                data = resp.json()
                chat_model_path = data.get("chat_model", "Unknown")
                memory_mb = data.get("memory_mb", 0)
                
                # Extract model name from path
                model_name = chat_model_path.split("/")[-1] if "/" in chat_model_path else chat_model_path
                
                return HTMLResponse(f'''
                    <div style="padding: 0.5rem 0; border-bottom: 1px solid var(--glass-border); margin-bottom: 0.5rem;">
                        <div style="font-size: 0.7rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.3rem;">Active Model</div>
                        <div style="font-size: 0.85rem; color: var(--neon-blue); font-weight: 600; word-break: break-word;">
                            🤖 {model_name}
                        </div>
                        <div style="font-size: 0.7rem; color: var(--text-dim); margin-top: 0.2rem;">
                            💾 {memory_mb} MB
                        </div>
                    </div>
                ''')
    except Exception as e:
        return HTMLResponse(f'<div style="color: var(--neon-pink); font-size: 0.8rem;">❌ Error: {str(e)[:50]}</div>')


async def get_model_selector(request):
    """Return the model selector dropdown (fresh from MLX /v1/models)."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("http://127.0.0.1:1234/v1/models")
            if resp.status_code == 200:
                data = resp.json()
                chat_models = data.get("data", {}).get("chat", [])
                
                # Build select HTML
                options_html = ""
                for m in chat_models:
                    model_id = m.get("id", "")
                    model_name = m.get("name", "Unknown")
                    is_selected = m.get("selected", False)
                    selected_attr = "selected" if is_selected else ""
                    
                    options_html += f'<option value="{model_id}" {selected_attr}>{model_name}</option>\n'
                
                return HTMLResponse(f'''
                    <label style="display: block; font-size: 0.75rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.3rem;">
                        Model Selection
                    </label>
                    <select name="model_path" onchange="swapModel(this.value)" style="width: 100%; background: var(--glass); border: 1px solid var(--glass-border); color: var(--text-main); padding: 0.6rem; border-radius: 8px; font-family: 'Rajdhani', sans-serif; font-size: 0.85rem; cursor: pointer; transition: all 0.3s ease;">
                        {options_html}
                    </select>
                    <script>
                    async function swapModel(modelPath) {{
                        if (!modelPath) return;
                        try {{
                            const resp = await fetch('http://127.0.0.1:1234/v1/models/swap', {{
                                method: 'POST',
                                headers: {{'Content-Type': 'application/json'}},
                                body: JSON.stringify({{model_path: modelPath, type: 'chat'}})
                            }});
                            const data = await resp.json();
                            if (data.status === 'ok') {{
                                // Refresh active badge immediately
                                htmx.ajax('GET', '/models/active-badge', {{target: '#model-active-badge', swap: 'innerHTML'}});
                                // Refresh selector after 2s
                                setTimeout(() => {{
                                    htmx.ajax('GET', '/models/selector', {{target: '#model-selector', swap: 'innerHTML'}});
                                }}, 2000);
                            }} else {{
                                alert('Swap failed: ' + data.message);
                            }}
                        }} catch (e) {{
                            alert('Error swapping model: ' + e);
                        }}
                    }}
                    </script>
                ''')
    except Exception as e:
        return HTMLResponse(f'<div style="color: var(--neon-pink); font-size: 0.8rem;">❌ Error loading models: {str(e)[:50]}</div>')


async def chat_page(request):
    sid = get_session_id(request)
    # Load history from DB
    history = database.get_chat_history(sid)
    SESSIONS[sid] = history
    return HTMLResponse(get_base_html("chat", render_chat_view(history), sid))

async def tasks_page(request):
    return HTMLResponse(get_base_html("tasks", render_tasks_view(), ""))

async def memory_page(request):
    return HTMLResponse(get_base_html("memory", render_memory_view(), ""))

async def schedule_page(request):
    try:
        calendars = await bettershift_client.list_calendars()
        return HTMLResponse(get_base_html("schedule", render_schedule_view(calendars), ""))
    except Exception as e:
        return HTMLResponse(get_base_html("schedule", render_schedule_view(error=str(e)), ""))

# --- Archives View ---

def render_archives_view(query=""):
    # 1. Fetch Archives Files
    import glob
    files = sorted(glob.glob("archives/*.txt"), reverse=True)
    
    # 2. Fetch Archived Tasks
    archived_tasks = database.get_archived_tasks()
    
    # Filter if query
    if query:
        query = query.lower()
        files = [f for f in files if query in f.lower() or query in open(f).read().lower()]
        archived_tasks = [t for t in archived_tasks if query in t['description'].lower()]
        
    # Render File List
    file_html = ""
    for f in files:
        name = os.path.basename(f)
        file_html += f'''
            <div id="archive-file-{name}">
                <div class="info-card" onclick="toggleFile('{name}')" style="cursor:pointer; position:relative;">
                    <div class="nav-icon">📄</div>
                    <div class="nav-text" style="flex:1;">
                        <div class="nav-title">{name}</div>
                        <div class="nav-desc">Click to expand</div>
                    </div>
                    <button 
                        hx-delete="/archives/delete/file/{name}" 
                        hx-target="#archive-file-{name}" 
                        hx-swap="outerHTML"
                        onclick="event.stopPropagation()"
                        style="background:rgba(255,0,85,0.1); border:1px solid var(--neon-pink); color:var(--neon-pink); padding:0.4rem 0.8rem; border-radius:8px; cursor:pointer; font-size:0.8rem; transition:all 0.3s; flex-shrink:0;"
                        onmouseover="this.style.background='rgba(255,0,85,0.2)'"
                        onmouseout="this.style.background='rgba(255,0,85,0.1)'">
                        🗑️
                    </button>
                </div>
                <div id="file-{name}" style="display:none; background:var(--glass); padding:1rem; margin-bottom:0.8rem; border-radius:12px; font-family:monospace; font-size:0.8rem; white-space:pre-wrap; color:var(--text-dim); border:1px solid var(--glass-border);">
                    {open(f).read()}
                </div>
            </div>'''
        
    # Render Task List definition
    task_html = ""
    for t in archived_tasks:
        task_html += f'''
            <div class="task-card completed" id="archived-task-{t['id']}" style="opacity:0.6">
                <div class="checkbox" style="background:var(--neon-purple); border-color:var(--neon-purple);">✓</div>
                <div class="task-text" style="flex:1;">
                    {t['description']} 
                    <span style="font-size:0.75em; color:var(--text-dim);">({t.get('completed_at', 'unknown')})</span>
                </div>
                <button 
                    hx-delete="/archives/delete/task/{t['id']}" 
                    hx-target="#archived-task-{t['id']}" 
                    hx-swap="outerHTML"
                    style="background:rgba(255,0,85,0.1); border:1px solid var(--neon-pink); color:var(--neon-pink); padding:0.4rem 0.8rem; border-radius:8px; cursor:pointer; font-size:0.8rem; transition:all 0.3s; flex-shrink:0;"
                    onmouseover="this.style.background='rgba(255,0,85,0.2)'"
                    onmouseout="this.style.background='rgba(255,0,85,0.1)'">
                    🗑️
                </button>
            </div>'''
        
    return f'''
            <div class="chat-header">
                <div>
                    <div class="chat-title">Archives</div>
                    <div class="chat-subtitle">Historical Records</div>
                </div>
            </div>
            
            <div class="page-container">
                <input type="text" name="q" placeholder="🔍 Search archives..." 
                       hx-get="/archives/search" hx-trigger="keyup changed delay:500ms" hx-target="#archive-content"
                       style="margin-bottom: 2rem;">
                       
                <div id="archive-content">
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:2rem;">
                        <div>
                            <h3 style="margin-bottom:1rem; color:var(--neon-blue); font-family:'Orbitron',sans-serif; font-size:1rem;">📂 Chat Logs</h3>
                            {file_html if file_html else '<div style="color:var(--text-dim);">No files found.</div>'}
                        </div>
                        <div>
                            <h3 style="margin-bottom:1rem; color:var(--neon-pink); font-family:'Orbitron',sans-serif; font-size:1rem;">✅ Completed Tasks</h3>
                            {task_html if task_html else '<div style="color:var(--text-dim);">No archived tasks.</div>'}
                        </div>
                    </div>
                </div>
                
                <script>
                function toggleFile(name) {{
                    let el = document.getElementById('file-' + name);
                    el.style.display = el.style.display === 'none' ? 'block' : 'none';
                }}
                </script>
            </div>
    '''

async def archives_page(request):
    return HTMLResponse(get_base_html("archives", render_archives_view(), ""))

async def search_archives(request):
    q = request.query_params.get("q", "")
    # Return just the inner content for HTMX replacement
    # We call render_archives_view but extract just the content div ? 
    # Actually render_archives_view returns full page container usually.
    # Let's simple refactor:
    
    # We'll just return the INNER part of the #archive-content div for simplicity
    # Duplicate logic slightly for speed (or refactor render to be cleaner)
    # Let's trust render_archives_view returns the big block, we will just return that block 
    # wait, render_archives_view returns the whole page.
    
    # Quick fix: Just return the whole view again, HTMX will swap the target properly if we target 'body' or...
    # The user asked for clean impl.
    # Let's adjust render_archives_view to support partial return?
    
    return HTMLResponse(render_archives_view(q)) 
    # Note: This returns the full page container including header. 
    # HTMX hx-target="#archive-content" means we need to return just that content.
    # I'll fix render_archives_view in the actual code to be smarter or parsing.
    
    # Actually, let's just make search_archives return the inner HTML manually for now to be safe.
    
    view = render_archives_view(q)
    # Extract the inner content part (hacky but reliable without refactoring everything)
    start_marker = '<div id="archive-content">'
    if start_marker in view:
        return HTMLResponse(view.split(start_marker)[1].split('<script>')[0]) # Get content before script
    return HTMLResponse("Error parsing view")


# --- Actions ---

async def send_message(request):
    form = await request.form()
    msg = form.get("msg", "").strip()
    sid = get_session_id(request)
    if not msg: return HTMLResponse("")
    
    # Save User Message
    database.save_chat_message(sid, "user", msg)
    
    try:
        # Load fresh history from DB to ensure context is correct
        history = database.get_chat_history(sid)
        
        # Pass history to allow context recall
        response_text = await llm_client.process_input(msg, user_id=sid, history=history)
    except Exception as e:
        response_text = f"Error: {e}"
        
    # Save Assistant Response
    database.save_chat_message(sid, "assistant", response_text)
    
    return HTMLResponse(f'''
    <div class="message ai"><div class="message-avatar">⚡</div><div class="message-content"><div class="message-text">{response_text}</div></div></div>
    ''') 

async def toggle_task(request):
    tid = request.path_params['tid']
    import sqlite3
    conn = sqlite3.connect(database.DB_NAME)
    c = conn.cursor()
    c.execute("SELECT status, description FROM tasks WHERE id=?", (tid,))
    row = c.fetchone()
    if row:
        new_status = 'pending' if row[0] == 'completed' else 'completed'
        c.execute("UPDATE tasks SET status=? WHERE id=?", (new_status, tid))
        conn.commit()
        status = "completed" if new_status == 'completed' else ""
        checked = "checked" if new_status == 'completed' else ""
        return HTMLResponse(f'''
        <div class="task-card {status}" id="task-{tid}">
            <input type="checkbox" class="checkbox" hx-post="/tasks/toggle/{tid}" hx-target="#task-{tid}" hx-swap="outerHTML" {checked}>
            <div class="task-text">{row[1]}</div>
        </div>''')
    return HTMLResponse("")

async def add_task_ui(request):
    form = await request.form()
    desc = form.get("desc", "").strip()
    if desc:
        tid = database.add_task(desc)
        return HTMLResponse(f'''
        <div class="task-card" id="task-{tid}">
            <input type="checkbox" class="checkbox" hx-post="/tasks/toggle/{tid}" hx-target="#task-{tid}" hx-swap="outerHTML">
            <div class="task-text">{desc}</div>
        </div>''')
    return HTMLResponse("")

async def get_actual_loaded_model():
    """Query MLX server directly to get the ACTUAL loaded model (source of truth)"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://127.0.0.1:1234/v1/models", timeout=30.0)
            if resp.status_code == 200:
                data = resp.json()["data"]
                return data
    except Exception:
        pass
    return None


async def get_active_model_badge(request):
    """Returns a badge showing the currently active model with auto-refresh"""
    # Single combined call - get models endpoint already has all info
    try:
        async with httpx.AsyncClient() as client:
            # Get health first (has RAM + model info)
            health_resp = await client.get("http://127.0.0.1:1234/health", timeout=5.0)
            if health_resp.status_code != 200:
                raise Exception("Health check failed")
            
            health = health_resp.json()
            chat_model = health.get("chat_model", "")
            mem_gb = health.get("memory_gb", 0)
            
            model_name = chat_model.split("/")[-1] if chat_model else "Unknown"
            if len(model_name) > 25:
                model_name = model_name[:22] + "..."
            
            ram_info = f' • {mem_gb}GB'
            
            return HTMLResponse(f'''
                <div style="background:rgba(0,243,255,0.1); border:1px solid var(--neon-blue); border-radius:8px; padding:0.5rem; font-size:0.7rem;">
                    <div style="color:var(--neon-blue); font-weight:600;">🟢 ACTIVE:</div>
                    <div style="color:var(--text); font-size:0.75rem; margin-top:0.2rem; font-family:'Rajdhani',monospace;">{model_name}{ram_info}</div>
                </div>
            ''')
    except:
        pass
    
    # Fallback to old method if health fails
    data = await get_actual_loaded_model()
    ram_info = ""
    
    if not data:
        return HTMLResponse('''
            <div style="background:rgba(255,0,85,0.1); border:1px solid var(--neon-pink); border-radius:8px; padding:0.5rem; font-size:0.7rem;">
                <div style="color:var(--neon-pink); font-weight:600;">🔴 SYSTEM ASLEEP</div>
                <div style="font-size:0.6rem; color:var(--text-dim); margin-top:0.2rem;">MLX Server offline</div>
            </div>
        ''')
    
    # Handle both formats
    if isinstance(data, dict) and "chat" in data:
        chat_models = data.get("chat", [])
        loaded = next((m for m in chat_models if m.get("selected")), None)
    else:
        chat_models = [m for m in data if "embed" not in m["id"].lower()]
        loaded = chat_models[0] if chat_models else None
    
    if loaded:
        model_name = loaded.get("name", loaded.get("id", "Unknown"))
        # Shorten long names
        if len(model_name) > 25:
            model_name = model_name[:22] + "..."
        
        return HTMLResponse(f'''
            <div style="background:rgba(0,243,255,0.1); border:1px solid var(--neon-blue); border-radius:8px; padding:0.5rem; font-size:0.7rem;">
                <div style="color:var(--neon-blue); font-weight:600;">🟢 ACTIVE:</div>
                <div style="color:var(--text); font-size:0.75rem; margin-top:0.2rem; font-family:'Rajdhani',monospace;">{model_name}{ram_info}</div>
            </div>
        ''')
    
    return HTMLResponse('<div style="color:var(--text-dim); font-size:0.7rem;">No model loaded</div>')


async def list_models(request):
    try:
        # Get actual loaded models from MLX server (source of truth)
        data = await get_actual_loaded_model()
        
        if not data:
            raise Exception("MLX server not responding")
        
        # Handle both formats: nested (data.chat/data.embed) or flat (data[])
        if isinstance(data, dict) and "chat" in data:
            # Nested format
            chat_models = data.get("chat", [])
            embed_models = data.get("embed", [])
        else:
            # Flat format - separate by name
            chat_models = [m for m in data if "embed" not in m["id"].lower()]
            embed_models = [m for m in data if "embed" in m["id"].lower()]
        
        # Build chat options
        chat_ops = ""
        for m in chat_models:
            # Use "name" field if available, otherwise extract from path
            display_name = m.get("name", m["id"].split("/")[-1])
            # Truncate if too long
            disp = display_name[:35] + ".." if len(display_name) > 35 else display_name
            # Add checkmark if selected
            selected = "✓ " if m.get("selected", False) else ""
            chat_ops += f'<option value="{m["id"]}">{selected}{disp}</option>'
        
        # Build embed options
        embed_ops = ""
        for m in embed_models:
            display_name = m.get("name", m["id"].split("/")[-1])
            disp = display_name[:35] + ".." if len(display_name) > 35 else display_name
            selected = "✓ " if m.get("selected", False) else ""
            embed_ops += f'<option value="{m["id"]}">{selected}{disp}</option>'
        
        # If no models, show placeholder
        if not chat_ops:
            chat_ops = '<option value="">No chat models</option>'
        if not embed_ops:
            embed_ops = '<option value="">No embed models</option>'
            
        # Find currently loaded models
        loaded_chat = next((m for m in chat_models if m.get("selected")), None)
        loaded_embed = next((m for m in embed_models if m.get("selected")), None)
        
        chat_name = loaded_chat["name"] if loaded_chat else "Unknown"
        embed_name = loaded_embed["name"] if loaded_embed else "Unknown"
        
        return HTMLResponse(f'''
            <div style="display:flex; gap:8px; flex-direction:column;">
                <div style="font-size:0.65rem; color:var(--text-dim); text-transform:uppercase; letter-spacing:1px;">Models</div>
                
                <!-- Currently Loaded Indicator -->
                <div style="background:rgba(0,243,255,0.1); border:1px solid var(--neon-blue); border-radius:8px; padding:0.5rem; font-size:0.7rem;">
                    <div style="color:var(--neon-blue); margin-bottom:0.3rem; font-weight:600;">🔵 LOADED:</div>
                    <div style="color:var(--text); font-size:0.65rem; margin-left:0.5rem;">
                        💬 {chat_name}<br>
                        📊 {embed_name}
                    </div>
                </div>
                
                <!-- Model Selector -->
                <div style="display:flex; gap:6px; align-items:center;">
                    <select 
                        style="flex:1; background:var(--glass); border:1px solid var(--glass-border); border-radius:8px; padding:0.4rem 0.6rem; color:var(--text-main); font-size:0.75rem; font-family:'Rajdhani',sans-serif;" 
                        hx-post="/models/swap?type=chat" 
                        hx-swap="none"
                        hx-on::after-request="setTimeout(() => htmx.trigger(this.closest('div').parentElement, 'htmx:trigger'), 1000)"
                        name="model_path" 
                        title="Select Chat Model">
                        {chat_ops}
                    </select>
                    <button 
                        hx-get="/models" 
                        hx-target="closest div.parentElement" 
                        hx-swap="outerHTML"
                        style="background:rgba(0,243,255,0.1); border:1px solid var(--neon-blue); color:var(--neon-blue); padding:0.4rem 0.6rem; border-radius:8px; cursor:pointer; font-size:0.7rem;"
                        title="Refresh models">
                        🔄
                    </button>
                </div>
                <select 
                    style="background:var(--glass); border:1px solid var(--glass-border); border-radius:8px; padding:0.4rem 0.6rem; color:var(--text-main); font-size:0.75rem; font-family:'Rajdhani',sans-serif;" 
                    hx-post="/models/swap?type=embed" 
                    hx-swap="none"
                    hx-on::after-request="setTimeout(() => htmx.trigger(this.closest('div').parentElement, 'htmx:trigger'), 1000)"
                    name="model_path" 
                    title="Select Embed Model">
                    {embed_ops}
                </select>
            </div>
        ''')
    except Exception as e:
        # Show a loading message with auto-retry (polls every 5 seconds until MLX is ready)
        return HTMLResponse(f'''
            <div style="display:flex; gap:8px; flex-direction:column;"
                 hx-get="/models" 
                 hx-trigger="load delay:5s"
                 hx-swap="outerHTML">
                <div style="font-size:0.65rem; color:var(--text-dim); text-transform:uppercase; letter-spacing:1px;">Models</div>
                <div style="display:flex; gap:6px; align-items:center;">
                    <span style="color:var(--neon-pink); font-size:0.75rem; flex:1;">⚡ MLX Loading...</span>
                    <button 
                        hx-get="/models" 
                        hx-target="closest div"
                        hx-swap="outerHTML"
                        style="background:rgba(0,243,255,0.1); border:1px solid var(--neon-blue); color:var(--neon-blue); padding:0.4rem 0.6rem; border-radius:8px; cursor:pointer; font-size:0.7rem;"
                        title="Retry now">
                        🔄
                    </button>
                </div>
                <div style="font-size:0.6rem; color:var(--text-dim);">Auto-retrying in 5s...</div>
            </div>
        ''')

async def swap_model(request):
    form = await request.form()
    path = form.get("model_path")
    type_ = request.query_params.get("type", "chat")
    
    success = False
    error_msg = None
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://127.0.0.1:1234/v1/models/swap", 
                json={"model_path": path, "type": type_}, 
                timeout=120.0  # Longer timeout for model loading
            )
            if resp.status_code == 200:
                success = True
            else:
                error_msg = f"Server returned {resp.status_code}"
    except Exception as e:
        error_msg = str(e)
    
    if success:
        # Save selection to config only on success
        if type_ == "chat":
            save_config_val("chat_model", path)
        else:
            save_config_val("embed_model", path)
            mlx_embeddings.set_model_path(path)
        
        # Return success - will trigger UI refresh via HTMX
        return HTMLResponse("", status_code=204, headers={
            "HX-Trigger": "modelSwapped"  # Custom event to refresh active badge
        })
    else:
        # Return error - UI will show toast
        return HTMLResponse(
            f'<div style="color:var(--neon-pink); font-size:0.7rem; padding:0.5rem;">❌ Swap failed: {error_msg}</div>',
            status_code=500
        )

async def check_wakeup(request):
    """
    Polls the MLX server health.
    Called by HTMX from the chat bubble during waking.
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://127.0.0.1:1234/health", timeout=1.0)
            if resp.status_code == 200:
                # Success! Stop polling and show success message
                return HTMLResponse('<div class="message ai"><div class="message-avatar">⚡</div><div class="message-content"><div class="message-text">⚡ <strong>I\'m Awake!</strong> Ready for vision & chat.</div></div></div>')
    except: 
        pass
    
    # Still waiting, return same polling element (recursive poll)
    return HTMLResponse('<div class="message ai"><div class="message-avatar">⚡</div><div class="message-content"><div class="message-text">🌅 Waking up... <span hx-get="/check_wakeup" hx-trigger="load delay:2s" hx-swap="outerHTML">models loading...</span></div></div></div>')


async def wake_server(request):
    """
    Direct endpoint to wake all AI services without going through chat.
    Starts: MLX server + BetterShift
    This bypasses the LLM which can't process when it's down.
    """
    import subprocess
    import os
    
    # Check if MLX already running
    mlx_running = False
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://127.0.0.1:1234/health", timeout=1.0)
            if resp.status_code == 200:
                mlx_running = True
    except:
        pass
    
    # Check if BetterShift already running
    bettershift_running = False
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://127.0.0.1:3000", timeout=1.0)
            if resp.status_code == 200:
                bettershift_running = True
    except:
        pass
    
    if mlx_running and bettershift_running:
        return HTMLResponse('<div class="message ai"><div class="message-avatar">⚡</div><div class="message-content"><div class="message-text">⚡ Already awake! All services running.</div></div></div>')
    
    started = []
    
    pid_dir = os.path.join(os.getcwd(), ".run_all_pids")
    log_dir = os.path.join(os.getcwd(), ".run_all_logs")
    os.makedirs(pid_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    
    # Start MLX server if not running
    if not mlx_running:
        import sys
        with open(os.path.join(log_dir, "mlx_server.log"), "a") as log_file:
            proc = subprocess.Popen(
                [sys.executable, "mlx_server.py"],
                cwd=os.getcwd(),
                stdout=log_file,
                stderr=log_file
            )
            with open(os.path.join(pid_dir, "mlx.pid"), "w") as f:
                f.write(str(proc.pid))
        started.append("MLX")
    
    # Start BetterShift if not running
    if not bettershift_running:
        bettershift_dir = os.path.join(os.getcwd(), "bettershift", "BetterShift")
        if os.path.isdir(bettershift_dir):
            # Use bash to source NVM and run npm, ensuring correct node environment
            with open(os.path.join(log_dir, "bettershift.log"), "a") as log_file:
                proc = subprocess.Popen(
                    ["/bin/bash", "-c", "source ~/.nvm/nvm.sh && npm run dev"],
                    cwd=bettershift_dir,
                    stdout=log_file,
                    stderr=log_file
                )
                with open(os.path.join(pid_dir, "bettershift.pid"), "w") as f:
                    f.write(str(proc.pid))
            started.append("BetterShift")
    
    services = " + ".join(started) if started else "services"
    return HTMLResponse(f'<div class="message ai"><div class="message-avatar">⚡</div><div class="message-content"><div class="message-text">🌅 Waking up {services}... <span hx-get="/check_wakeup" hx-trigger="load delay:2s" hx-swap="outerHTML">starting...</span></div></div></div>')


async def sleep_server(request):
    """
    Direct endpoint to sleep all AI services without going through chat.
    Stops: MLX server + BetterShift
    """
    import subprocess
    import os
    subprocess.run(["pkill", "-f", "mlx_server.py"], check=False)
    subprocess.run(["pkill", "-f", "next dev"], check=False)
    subprocess.run(["pkill", "-f", "next-server"], check=False)
    
    # Remove PID files for run_all.sh status consistency
    pid_dir = os.path.join(os.getcwd(), ".run_all_pids")
    try:
        if os.path.exists(os.path.join(pid_dir, "mlx.pid")):
            os.remove(os.path.join(pid_dir, "mlx.pid"))
        if os.path.exists(os.path.join(pid_dir, "bettershift.pid")):
            os.remove(os.path.join(pid_dir, "bettershift.pid"))
    except:
        pass
        
    return HTMLResponse('<div class="message ai"><div class="message-avatar">⚡</div><div class="message-content"><div class="message-text">😴 Sleep mode activated. MLX + BetterShift stopped.</div></div></div>')


async def voice_transcribe(request):
    """
    Transcribe audio using Whisper (faster-whisper).
    Expects multipart form with 'audio' file.
    """
    import tempfile
    import os
    
    form = await request.form()
    audio_file = form.get("audio")
    
    if not audio_file:
        return JSONResponse({"error": "No audio file"}, status_code=400)
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        content = await audio_file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        from faster_whisper import WhisperModel
        
        # Use tiny model for speed (~1-2s latency)
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, info = model.transcribe(tmp_path, beam_size=1)
        
        text = " ".join([segment.text for segment in segments]).strip()
        return JSONResponse({"text": text, "language": info.language})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        os.unlink(tmp_path)


async def voice_speak(request):
    """
    Text-to-speech using macOS 'say' command (instant, always available).
    For better quality, Piper can be added later.
    """
    import subprocess
    import tempfile
    import os
    
    data = await request.json()
    text = data.get("text", "")
    
    if not text:
        return JSONResponse({"error": "No text"}, status_code=400)
    
    # Use macOS say command with AIFF output
    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        # Generate speech (simple format, no --data-format)
        subprocess.run(
            ["say", "-o", tmp_path, text],
            check=True,
            timeout=30
        )
        
        # Return audio file
        return FileResponse(tmp_path, media_type="audio/aiff", filename="speech.aiff")
    except Exception as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return JSONResponse({"error": str(e)}, status_code=500)


async def delete_note(request):
    """Delete a note from memory"""
    note_id = request.path_params['note_id']
    try:
        # Use the database function instead of direct SQL
        success = database.delete_note(int(note_id))
        if success:
            # Return empty string - HTMX will remove the element with hx-swap="outerHTML"
            return HTMLResponse("")
        else:
            return HTMLResponse(f'<div style="color:var(--neon-pink);">Note not found</div>', status_code=404)
    except Exception as e:
        return HTMLResponse(f'<div style="color:var(--neon-pink);">Error: {e}</div>', status_code=500)


async def delete_archive_file(request):
    """Delete an archive file"""
    filename = request.path_params['filename']
    try:
        filepath = os.path.join("archives", filename)
        # Security check: ensure filename doesn't contain path traversal
        if ".." in filename or "/" in filename:
            return HTMLResponse(f'<div style="color:var(--neon-pink);">Invalid filename</div>', status_code=400)
        
        if os.path.exists(filepath):
            os.remove(filepath)
            return HTMLResponse("")
        else:
            return HTMLResponse(f'<div style="color:var(--neon-pink);">File not found</div>', status_code=404)
    except Exception as e:
        return HTMLResponse(f'<div style="color:var(--neon-pink);">Error: {e}</div>', status_code=500)


async def delete_archived_task(request):
    """Delete an archived task permanently"""
    task_id = request.path_params['task_id']
    try:
        success = database.delete_task(int(task_id))
        if success:
            return HTMLResponse("")
        else:
            return HTMLResponse(f'<div style="color:var(--neon-pink);">Task not found</div>', status_code=404)
    except Exception as e:
        return HTMLResponse(f'<div style="color:var(--neon-pink);">Error: {e}</div>', status_code=500)


async def get_presence_status(request):
    """Get current entity status from BetterShift"""
    try:
        # Call the check_entity_status tool
        result = await llm_client.execute_tool("check_entity_status", [])
        
        # Parse the result and format as HTML
        if "❌" in result or "error" in result.lower():
            return HTMLResponse(f'''
                <div style="color:var(--text-dim); font-size:0.8rem; text-align:center; padding:0.5rem;">
                    <div>⚪ Offline</div>
                    <div style="font-size:0.7rem; margin-top:0.25rem;">BetterShift unavailable</div>
                </div>
            ''')
        
        if "No calendars" in result or "No entities" in result:
            return HTMLResponse(f'''
                <div style="color:var(--text-dim); font-size:0.8rem; text-align:center; padding:0.5rem;">
                    <div>⚪ No Coverage</div>
                </div>
            ''')
        
        # Format the result as HTML
        lines = result.split('\n')
        html = '<div style="font-size:0.8rem;">'
        
        for line in lines:
            if line.startswith('Current Coverage:'):
                continue
            if line.strip():
                html += f'<div style="padding:0.25rem 0; color:var(--text);">{line}</div>'
        
        html += '</div>'
        
        return HTMLResponse(html)
        
    except Exception as e:
        return HTMLResponse(f'''
            <div style="color:var(--neon-pink); font-size:0.8rem; text-align:center; padding:0.5rem;">
                Error: {str(e)[:50]}
            </div>
        ''', status_code=500)


async def archive_chat(request):
    """Archive current chat to file and clear the session"""
    sid = get_session_id(request)
    
    try:
        # Get current chat history
        history = database.get_chat_history(sid)
        
        if not history or len(history) == 0:
            return HTMLResponse('''
                <div class="message ai">
                    <div class="message-avatar">⚡</div>
                    <div class="message-content">
                        <div class="message-text" style="color:var(--neon-pink);">No chat history to archive.</div>
                    </div>
                </div>
            ''')
        
        # Create archive file
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
        filename = f"archive_{timestamp}.txt"
        filepath = os.path.join("archives", filename)
        
        # Ensure archives directory exists
        os.makedirs("archives", exist_ok=True)
        
        # Write chat history to file
        with open(filepath, 'w') as f:
            f.write(f"Chat Archive - {timestamp}\n")
            f.write("=" * 60 + "\n\n")
            for msg in history:
                role = msg['role'].upper()
                content = msg['content']
                f.write(f"{role}:\n{content}\n\n")
        
        # Clear the database chat history for this session
        database.clear_chat_history(sid)
        
        # Clear the in-memory session
        if sid in SESSIONS:
            SESSIONS[sid] = []
        
        # Return fresh welcome message
        return HTMLResponse('''
            <div class="message ai">
                <div class="message-avatar">⚡</div>
                <div class="message-content">
                    <div class="message-text">✅ Chat archived! Hello! I'm Echo V3, your local AI assistant. How can I help you today?</div>
                </div>
            </div>
        ''')
        
    except Exception as e:
        return HTMLResponse(f'''
            <div class="message ai">
                <div class="message-avatar">⚡</div>
                <div class="message-content">
                    <div class="message-text" style="color:var(--neon-pink);">Error archiving chat: {e}</div>
                </div>
            </div>
        ''', status_code=500)


# ============ ROUTES ============
routes = [
    Route("/", chat_page),
    Route("/tasks", tasks_page),
    Route("/memory", memory_page),
    Route("/schedule", schedule_page),
    Route("/archives", archives_page),
    Route("/archives/search", search_archives),
    Route("/archives/delete/file/{filename}", delete_archive_file, methods=["DELETE"]),
    Route("/archives/delete/task/{task_id}", delete_archived_task, methods=["DELETE"]),
    
    Route("/send", send_message, methods=["POST"]),
    Route("/chat/archive", archive_chat, methods=["POST"]),
    Route("/status/presence", get_presence_status),
    Route("/tasks/toggle/{tid}", toggle_task, methods=["POST"]),
    Route("/tasks/add", add_task_ui, methods=["POST"]),
    Route("/models", list_models, methods=["GET"]),
    Route("/models/active", get_active_model_badge, methods=["GET"]),
    Route("/models/swap", swap_model, methods=["POST"]),
    Route("/check_wakeup", check_wakeup, methods=["GET"]),
    Route("/wake", wake_server, methods=["POST"]),
    Route("/sleep", sleep_server, methods=["POST"]),
    Route("/voice/transcribe", voice_transcribe, methods=["POST"]),
    Route("/voice/speak", voice_speak, methods=["POST"]),
    Route("/memory/delete/{note_id}", delete_note, methods=["DELETE"]),
    Route("/bettershift/{path:path}", bettershift_proxy.forward_request, methods=["GET", "POST", "PUT", "PATCH", "DELETE"]),
    Mount("/static", StaticFiles(directory="static"), name="static"),
]

app = Starlette(routes=routes, on_startup=[startup])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001, log_level="info")
