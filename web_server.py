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
import finance_dashboard

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
# ============ CSS & ASSETS ============
CSS = """
/* Echo V3 - Premium Cyberpunk Neural Interface */
/* Designed by Antigravity */

:root {
    /* Base Colors */
    --bg-deep: #020205;
    --bg-gradient: radial-gradient(circle at center, #0d0d1a 0%, #020205 100%);
    --bg-sidebar: rgba(10, 15, 30, 0.7);
    
    /* Neon Accents */
    --neon-purple: #bc13fe;
    --neon-blue: #00f3ff;
    --neon-pink: #ff0055;
    --neon-green: #39ff14;
    --neon-yellow: #ffcc00;
    
    /* Gradients */
    --grad-cyber: linear-gradient(135deg, var(--neon-blue), var(--neon-purple));
    --grad-heat: linear-gradient(135deg, var(--neon-pink), var(--neon-yellow));
    --grad-glass: linear-gradient(145deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01));
    
    /* UI Elements */
    --glass: rgba(20, 20, 30, 0.5);
    --glass-border: rgba(255, 255, 255, 0.1);
    --text-main: #ffffff;
    --text-dim: #a0a0c0;
}

* { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }

body {
    background-color: var(--bg-deep);
    background-image: var(--bg-gradient);
    color: var(--text-main);
    font-family: 'Rajdhani', sans-serif;
    overflow: hidden;
    height: 100vh;
    position: relative;
}

/* --- GLOBAL LAYOUT --- */
.page-container {
    padding: 2rem 3rem;
    max-width: 1600px;
    margin: 0 auto;
    width: 100%;
    height: 100%;
    overflow-y: auto;
}

/* --- PREMIUM CARD STYLES (Global) --- */
.task-card, .memory-card, .calendar-card, .archive-card, .info-card {
    background: var(--glass);
    border: 1px solid var(--glass-border);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    position: relative;
    backdrop-filter: blur(20px);
    transition: all 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
    display: flex;
    align-items: center;
    gap: 1.2rem;
    box-shadow: 0 4px 30px rgba(0,0,0,0.1);
}

.task-card:hover, .memory-card:hover, .calendar-card:hover, .archive-card:hover, .info-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 20px 40px rgba(0,0,0,0.3);
    background: rgba(255,255,255,0.03);
}

/* Specific Border Accents on Hover */
.task-card:hover { border-color: var(--neon-purple); }
.memory-card:hover { border-color: var(--neon-blue); }
.calendar-card:hover { border-color: var(--neon-yellow); }
.archive-card:hover { border-color: var(--neon-pink); }
.info-card:hover { border-color: var(--neon-green); }

/* Typography */
.card-title, .nav-title, .task-text {
    font-family: 'Orbitron', sans-serif;
    font-size: 1.1rem;
    color: #fff;
    letter-spacing: 1px;
    margin-bottom: 0.2rem;
}

.card-desc, .nav-desc {
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.9rem;
    color: var(--text-dim);
}

/* Grid Layouts */
.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.5rem;
}

/* Form Elements */
input[type="text"], input[type="search"], textarea {
    width: 100%;
    background: rgba(0,0,0,0.3);
    border: 1px solid var(--glass-border);
    padding: 1.2rem;
    border-radius: 12px;
    color: #fff;
    font-family: 'Rajdhani', sans-serif;
    font-size: 1.1rem;
    outline: none;
    transition: all 0.3s ease;
}

input[type="text"]:focus, input[type="search"]:focus, textarea:focus {
    border-color: var(--neon-blue);
    box-shadow: 0 0 20px rgba(0, 243, 255, 0.1);
    background: rgba(255,255,255,0.05);
}

/* Custom Scrollbar */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--neon-blue); }

/* --- GLOBAL LAYOUT --- */
.page-container {
    padding: 2rem 3rem;
    max-width: 1600px;
    margin: 0 auto;
    width: 100%;
    height: 100%;
    overflow-y: auto;
}

/* --- PREMIUM CARD STYLES (Global) --- */
.task-card, .memory-card, .calendar-card, .archive-card, .info-card {
    background: var(--glass);
    border: 1px solid var(--glass-border);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    position: relative;
    backdrop-filter: blur(20px);
    transition: all 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
    display: flex;
    align-items: center;
    gap: 1.2rem;
    box-shadow: 0 4px 30px rgba(0,0,0,0.1);
}

.task-card:hover, .memory-card:hover, .calendar-card:hover, .archive-card:hover, .info-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 20px 40px rgba(0,0,0,0.3);
    background: rgba(255,255,255,0.03);
}

/* Specific Border Accents on Hover */
.task-card:hover { border-color: var(--neon-purple); }
.memory-card:hover { border-color: var(--neon-blue); }
.calendar-card:hover { border-color: var(--neon-yellow); }
.archive-card:hover { border-color: var(--neon-pink); }
.info-card:hover { border-color: var(--neon-green); }

/* Typography */
.card-title, .nav-title, .task-text {
    font-family: 'Orbitron', sans-serif;
    font-size: 1.1rem;
    color: #fff;
    letter-spacing: 1px;
    margin-bottom: 0.2rem;
}

.card-desc, .nav-desc {
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.9rem;
    color: var(--text-dim);
}

/* Grid Layouts */
.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.5rem;
}

/* Form Elements */
input[type="text"], input[type="search"], textarea {
    width: 100%;
    background: rgba(0,0,0,0.3);
    border: 1px solid var(--glass-border);
    padding: 1.2rem;
    border-radius: 12px;
    color: #fff;
    font-family: 'Rajdhani', sans-serif;
    font-size: 1.1rem;
    outline: none;
    transition: all 0.3s ease;
}

input[type="text"]:focus, input[type="search"]:focus, textarea:focus {
    border-color: var(--neon-blue);
    box-shadow: 0 0 20px rgba(0, 243, 255, 0.1);
    background: rgba(255,255,255,0.05);
}

/* Custom Scrollbar */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--neon-blue); }

/* Noise Overlay */
body::before {
    content: "";
    position: fixed;
    top: 0; left: 0; width: 100%; height: 100%;
    background: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.04'/%3E%3C/svg%3E");
    pointer-events: none;
    z-index: 9999;
    opacity: 0.4;
}

/* 3D Animated Background Grid */
.cyber-grid {
    position: fixed;
    top: -50%;
    left: -50%;
    width: 200vw;
    height: 200vh;
    background-image: 
        linear-gradient(rgba(0, 243, 255, 0.05) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0, 243, 255, 0.05) 1px, transparent 1px);
    background-size: 60px 60px;
    transform: perspective(600px) rotateX(60deg) translateY(0) translateZ(-200px);
    animation: gridMove 20s linear infinite;
    z-index: -2;
    pointer-events: none;
    mask-image: radial-gradient(ellipse at center, black, transparent 80%);
    -webkit-mask-image: radial-gradient(ellipse at center, black, transparent 80%);
}

@keyframes gridMove {
    0% { transform: perspective(600px) rotateX(60deg) translateY(0) translateZ(-200px); }
    100% { transform: perspective(600px) rotateX(60deg) translateY(60px) translateZ(-200px); }
}

/* Ambient Orbs */
.orb {
    position: fixed;
    border-radius: 50%;
    filter: blur(120px);
    opacity: 0.25;
    pointer-events: none;
    z-index: -1;
    animation: glowPulse 12s ease-in-out infinite alternate;
}
.orb-1 {
    width: 600px; height: 600px;
    background: radial-gradient(circle, var(--neon-purple), transparent 70%);
    top: -200px; right: -200px;
}
.orb-2 {
    width: 800px; height: 800px;
    background: radial-gradient(circle, var(--neon-blue), transparent 70%);
    bottom: -300px; left: -200px;
    animation-delay: 5s;
}
@keyframes glowPulse {
    0% { transform: scale(1); opacity: 0.2; }
    100% { transform: scale(1.2); opacity: 0.4; }
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
    backdrop-filter: blur(30px);
    -webkit-backdrop-filter: blur(30px);
    z-index: 100;
    box-shadow: 10px 0 50px rgba(0,0,0,0.5);
}

.sidebar-header {
    padding: 1.5rem 1.8rem;
    border-bottom: 1px solid var(--glass-border);
    background: linear-gradient(180deg, rgba(255,255,255,0.03), transparent);
}

.logo {
    font-family: 'Orbitron', sans-serif;
    font-size: 1.8rem;
    font-weight: 900;
    letter-spacing: 0.2em;
    background: var(--grad-cyber);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 0 20px rgba(188, 19, 254, 0.4);
    margin-bottom: 0.3rem;
}

.version {
    font-size: 0.8rem;
    color: var(--neon-blue);
    letter-spacing: 0.3em;
    opacity: 0.6;
}

.status {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    margin-top: 1.2rem;
    font-size: 0.85rem;
    color: var(--neon-green);
    font-weight: 700;
    letter-spacing: 3px;
}

.pulse-dot {
    width: 10px; height: 10px;
    background: var(--neon-green);
    border-radius: 50%;
    box-shadow: 0 0 15px var(--neon-green);
    animation: blinker 2s linear infinite;
}
@keyframes blinker { 
    0%, 100% { opacity: 1; filter: brightness(1); }
    50% { opacity: 0.4; filter: brightness(1.5); }
}

/* Model Section */
.model-section {
    padding: 1.5rem;
    border-bottom: 1px solid var(--glass-border);
}

.model-section select {
    width: 100%;
    background: rgba(0,0,0,0.5);
    border: 1px solid var(--glass-border);
    color: var(--text-main);
    padding: 1rem;
    border-radius: 12px;
    font-family: 'Rajdhani', sans-serif;
    font-size: 1rem;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.model-section select:hover {
    border-color: var(--neon-blue);
    box-shadow: 0 0 20px rgba(0, 243, 255, 0.2);
    transform: translateY(-2px);
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
    padding: 0.8rem;
    margin-bottom: 0.6rem;
    border-radius: 16px;
    background: rgba(255,255,255,0.03);
    border: 1px solid transparent;
    cursor: pointer;
    transition: all 0.5s cubic-bezier(0.2, 0.8, 0.2, 1);
    text-decoration: none;
    color: var(--text-main);
    position: relative;
}

.nav-item:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: var(--item-color);
    transform: translateX(10px);
    box-shadow: 0 10px 30px var(--item-glow), inset 0 0 15px var(--item-glow);
}

.nav-item.active {
    background: linear-gradient(90deg, rgba(255, 255, 255, 0.12), transparent);
    border-color: var(--item-color);
    box-shadow: -8px 0 0 var(--item-color);
}

.nav-icon {
    font-size: 1.4rem;
    filter: drop-shadow(0 0 8px rgba(255, 255, 255, 0.3));
    transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.nav-item:hover .nav-icon {
    transform: scale(1.15) rotate(5deg);
}

/* Main Content Area */
.main-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    position: relative;
    background: transparent;
}

.chat-header {
    padding: 1rem 2.5rem;
    border-bottom: 1px solid var(--glass-border);
    background: rgba(5, 5, 15, 0.82);
    backdrop-filter: blur(40px);
    -webkit-backdrop-filter: blur(40px);
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 10px 40px rgba(0,0,0,0.4);
}

.chat-title {
    font-family: 'Orbitron', sans-serif;
    font-size: 1.3rem;
    font-weight: 800;
    letter-spacing: 1.5px;
    background: var(--grad-cyber);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 0 10px rgba(0, 243, 255, 0.25));
}

.chat-subtitle {
    font-size: 0.8rem;
    color: var(--text-dim);
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-top: 0.2rem;
    opacity: 0.7;
}

.header-actions {
    display: flex;
    gap: 0.8rem;
    align-items: center;
}

.action-btn {
    border-radius: 10px;
    cursor: pointer;
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.85rem;
    font-weight: 600;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    border: 1px solid transparent;
}

.action-btn .btn-text { display: inline; }
.action-btn .btn-icon { font-size: 1.1rem; }

.btn-wake { background: rgba(0, 243, 255, 0.1); border-color: var(--neon-blue); color: var(--neon-blue); }
.btn-sleep { background: rgba(188, 19, 254, 0.1); border-color: var(--neon-purple); color: var(--neon-purple); }
.btn-archive { background: rgba(255, 0, 85, 0.1); border-color: var(--neon-pink); color: var(--neon-pink); }

.action-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px currentColor;
}

/* Messages */
.messages {
    flex: 1;
    overflow-y: auto;
    padding: 1.5rem 2.5rem;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    scroll-behavior: smooth;
}

.message {
    display: flex;
    gap: 2rem;
    animation: messagePop 0.5s cubic-bezier(0.2, 0.8, 0.2, 1.1);
}

@keyframes messagePop {
    from { opacity: 0; transform: translateY(30px) scale(0.95); }
    to { opacity: 1; transform: translateY(0) scale(1); }
}

.message.user { flex-direction: row-reverse; }

.message-avatar {
    width: 60px; height: 60px;
    border-radius: 20px;
    background-size: cover;
    background-position: center;
    flex-shrink: 0;
    border: 2px solid;
    box-shadow: 0 0 25px rgba(0,0,0,0.5);
    position: relative;
    overflow: hidden;
}

.message.user .message-avatar {
    border-color: var(--neon-blue);
    background-image: url('/static/user_avatar.png');
    box-shadow: 0 0 20px rgba(0, 243, 255, 0.3);
}

.message.ai .message-avatar {
    border-color: var(--neon-purple);
    background-image: url('/static/ai_avatar.png');
    box-shadow: 0 0 20px rgba(188, 19, 254, 0.3);
}

.message-content {
    max-width: 75%;
    background: rgba(20, 20, 35, 0.6);
    border: 1px solid var(--glass-border);
    border-radius: 20px;
    padding: 1.2rem 1.6rem;
    backdrop-filter: blur(20px);
    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    position: relative;
    border-left-width: 3px;
}

.message.user .message-content {
    border-color: var(--neon-blue);
    background: linear-gradient(135deg, rgba(0, 243, 255, 0.08), rgba(2, 2, 5, 0.8));
    border-bottom-right-radius: 4px;
}

.message.ai .message-content {
    border-color: var(--neon-purple);
    background: linear-gradient(135deg, rgba(188, 19, 254, 0.08), rgba(2, 2, 5, 0.8));
    border-top-left-radius: 4px;
}

.message-text { 
    line-height: 1.8; 
    white-space: pre-wrap; 
    font-size: 1.1rem; 
    letter-spacing: 0.3px;
    color: #eef;
}

/* Input Area - PILL INTEGRATED STYLE */
.input-area {
    padding: 1.5rem 3rem;
    border-top: 1px solid var(--glass-border);
    background: rgba(2, 2, 5, 0.92);
    backdrop-filter: blur(50px);
    -webkit-backdrop-filter: blur(50px);
}

.input-container {
    display: flex;
    align-items: center;
    max-width: 1000px;
    margin: 0 auto;
    background: rgba(255, 255, 255, 0.03);
    border: 2px solid var(--glass-border);
    border-radius: 50px; /* Perfect Pill */
    padding: 0.6rem 1.2rem;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: inset 0 0 20px rgba(0,0,0,0.5);
    position: relative;
    gap: 0.8rem;
}

.input-container:focus-within {
    border-color: var(--neon-blue);
    box-shadow: 0 0 40px rgba(0, 243, 255, 0.15), inset 0 0 15px rgba(0, 243, 255, 0.05);
    transform: translateY(-2px);
    background: rgba(255, 255, 255, 0.06);
}

.input-wrapper {
    flex: 1;
    display: flex;
    align-items: center;
}

.message-input {
    width: 100%;
    background: transparent;
    border: none;
    padding: 1rem 0.5rem;
    color: #fff;
    font-family: 'Rajdhani', sans-serif;
    font-size: 1.25rem;
    resize: none;
    min-height: 50px;
    max-height: 200px;
    outline: none;
    box-shadow: none; /* Override old style */
}

.message-input::placeholder {
    color: var(--text-dim);
    opacity: 0.5;
}

/* Icons inside the pill */
.aux-btn, #mic-btn {
    background: transparent;
    border: none;
    color: var(--text-dim);
    font-size: 1.6rem;
    cursor: pointer;
    width: 45px;
    height: 45px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    border-radius: 50%;
    flex-shrink: 0;
}

.aux-btn:hover, #mic-btn:hover {
    color: var(--neon-blue);
    background: rgba(255, 255, 255, 0.05);
    transform: scale(1.15);
    text-shadow: 0 0 15px var(--neon-blue);
}

.send-btn {
    width: 65px;
    height: 65px;
    border-radius: 50%;
    background: var(--grad-cyber);
    border: none;
    color: #fff;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.8rem;
    box-shadow: 0 0 25px rgba(0, 243, 255, 0.4);
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    flex-shrink: 0;
    margin-left: 0.5rem;
}

.send-btn:hover {
    transform: scale(1.1) rotate(-5deg);
    box-shadow: 0 0 40px rgba(0, 243, 255, 0.6);
}

.send-btn:active { transform: scale(0.9); }

/* Scrollbar */
::-webkit-scrollbar { width: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; border: 2px solid transparent; background-clip: padding-box; }
::-webkit-scrollbar-thumb:hover { background: var(--neon-blue); background-clip: padding-box; }

/* Mobile Menu Toggle - NEON STYLE */
.menu-toggle {
    display: none;
    position: fixed;
    top: 1.2rem;
    left: 1.2rem;
    z-index: 1001;
    width: 50px;
    height: 50px;
    background: var(--glass);
    border: 1px solid var(--neon-blue);
    color: var(--neon-blue);
    border-radius: 12px;
    font-size: 1.8rem;
    cursor: pointer;
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    box-shadow: 0 0 15px rgba(0, 243, 255, 0.3);
    transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.menu-toggle:hover {
    transform: scale(1.1);
    box-shadow: 0 0 25px rgba(0, 243, 255, 0.5);
}

@media (max-width: 768px) {
    .sidebar { 
        position: fixed; 
        transform: translateX(-100%); 
        width: 280px; 
        z-index: 2000; 
        height: 100vh;
        overflow: hidden;
    }
    .sidebar.open { transform: translateX(0); }
    .menu-toggle { display: flex; top: 0.8rem; left: 0.8rem; width: 42px; height: 42px; font-size: 1.4rem; z-index: 2001; }
    
    .sidebar-header { padding-left: 4.5rem; padding-top: 1.2rem; padding-bottom: 1.2rem; }
    .nav { overflow-y: auto; flex: 1; overscroll-behavior: contain; }
    
    .messages { padding: 1rem 0.8rem; gap: 1rem; }
    .message { gap: 0.8rem; }
    .message-avatar { width: 40px; height: 40px; border-radius: 12px; }
    .message-content { max-width: 85%; padding: 1rem 1.2rem; }
    .message-text { font-size: 0.95rem; line-height: 1.5; }
    
    .input-area { padding: 0.8rem; }
    .input-container { padding: 0.3rem 0.5rem; border-radius: 30px; }
    .message-input { min-height: 40px; font-size: 1rem; }
    .send-btn { width: 48px; height: 48px; }
    
    .chat-header { padding: 0.7rem 1rem; padding-left: 4.2rem; min-height: 60px; }
    .chat-title { font-size: 1.05rem; letter-spacing: 1px; }
    .chat-subtitle { display: none; }
    
    .action-btn { padding: 0.4rem; gap: 0; }
    .action-btn .btn-text { display: none; }
    .action-btn .btn-icon { font-size: 1.2rem; }
}
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
    <button class="menu-toggle" onclick="toggleSidebar()">☰</button>
    <div class="cyber-grid"></div>
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    
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
                {nav_link("Treasury", "Finance Tracker", "💰", "/finance", "finance")}
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
        messages_html += f'''
            <div class="message {cls}">
                <div class="message-avatar"></div>
                <div class="message-content">
                    <div class="message-text">{m["content"]}</div>
                </div>
            </div>'''
    
    if not history:
        messages_html = f'''
            <div class="message ai">
                <div class="message-avatar"></div>
                <div class="message-content">
                    <div class="message-text">Hello! I'm Echo V3, your local AI assistant. Accessing neural link pathways... System is online and ready for deployment. What are our objectives today?</div>
                </div>
            </div>'''
        
    return f'''
            <div class="chat-header">
                <div class="chat-info">
                    <div class="chat-title">Neural Link Active</div>
                    <div class="chat-subtitle">Direct interface with Echo V3 AI</div>
                </div>
                <div class="header-actions">
                    <button class="action-btn btn-wake" hx-post="/wake" hx-target="#messages" hx-swap="beforeend" title="Wake up the AI server">
                        <span class="btn-icon">🌅</span><span class="btn-text">WAKE</span>
                    </button>
                    <button class="action-btn btn-sleep" hx-post="/sleep" hx-target="#messages" hx-swap="beforeend" title="Put the AI server to sleep">
                        <span class="btn-icon">😴</span><span class="btn-text">SLEEP</span>
                    </button>
                    <button class="action-btn btn-archive" hx-post="/chat/archive" hx-confirm="Archive current chat and clear history?" hx-target="#messages" hx-swap="innerHTML" title="Archive current chat">
                        <span class="btn-icon">🗄️</span><span class="btn-text">ARCHIVE</span>
                    </button>
                </div>
            </div>
            
            <div class="messages" id="messages">
                {messages_html}
            </div>
            
            <div class="input-area">
                <div class="input-container">
                    <button type="button" class="aux-btn" onclick="htmx.ajax('GET', '/tasks', {{target: 'body'}})" title="Add Task">+</button>
                    <div class="input-wrapper">
                        <textarea class="message-input" id="messageInput" name="msg" placeholder="Ask anything..." rows="1"></textarea>
                    </div>
                    <button type="button" id="mic-btn" onclick="toggleRecording()" title="Voice input">🎤</button>
                    <button class="send-btn" onclick="sendMsg()" title="Send Objective">⚡</button>
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
        userDiv.innerHTML = '<div class="message-avatar"></div><div class="message-content"><div class="message-text">' + 
            msg.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;") + '</div></div>';
        messagesContainer.appendChild(userDiv);
        
        // 2. Add Thinking Indicator
        let thinkDiv = document.createElement('div');
        thinkDiv.id = 'thinking-bubble';
        thinkDiv.className = 'message ai';
        thinkDiv.innerHTML = '<div class="message-avatar"></div><div class="message-content"><div class="message-text" style="color:var(--text-dim); font-style:italic">Thinking...</div></div>';
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
        list_html = '<div style="text-align:center; color:var(--text-dim); margin-top:4rem; font-family:\'Rajdhani\'; font-size:1.2rem;">All systems nominal. No active tasks.</div>'
    
    for t in tasks:
        status = "completed" if t['status'] == 'completed' else ""
        checked = "checked" if t['status'] == 'completed' else ""
        list_html += f'''
            <div class="task-card {status}" id="task-{t['id']}">
                <input type="checkbox" class="checkbox" 
                       hx-post="/tasks/toggle/{t['id']}" 
                       hx-target="#task-{t['id']}" 
                       hx-swap="outerHTML"
                       {checked}
                       style="accent-color:var(--neon-purple); width:20px; height:20px; cursor:pointer; margin-right:1rem;">
                <div class="task-text" style="flex:1;">{t['description']}</div>
            </div>'''
        
    return f'''
            <style>
                .task-card.completed {{ opacity: 0.6; border-color: rgba(255,255,255,0.05); }}
                .task-card.completed .task-text {{ text-decoration: line-through; color: var(--text-dim); }}
            </style>
            <div class="chat-header">
                <div>
                    <div class="chat-title" style="color:var(--neon-purple);">Mission Control</div>
                    <div class="chat-subtitle">Task Management System</div>
                </div>
                <div style="display:flex; gap:1rem; align-items:center;">
                    <span hx-get="/tasks" hx-select=".main-content" hx-target=".main-content" 
                          style="cursor:pointer; font-size:1.2rem; opacity:0.7; transition:0.3s;" 
                          onmouseover="this.style.opacity='1'; this.style.transform='rotate(180deg)'"
                          onmouseout="this.style.opacity='0.7'; this.style.transform='rotate(0deg)'"
                          title="Refresh">🔄</span>
                </div>
            </div>
            
            <div class="page-container">
                <form hx-post="/tasks/add" hx-target="#task-list" hx-swap="afterbegin" onsubmit="setTimeout(()=>this.reset(), 10)">
                    <input type="text" name="desc" placeholder="+ Add new objective..." style="margin-bottom: 2rem;">
                </form>
                
                <div id="task-list">{list_html}</div>
            </div>
    '''


def render_schedule_view(calendars=None, error=None):
    calendars = calendars or []
    cal_list = ""
    if error:
        cal_list = f'<div style="background:rgba(255,0,85,0.1); border:1px solid var(--neon-pink); padding:1rem; border-radius:12px; color:var(--neon-pink); display:flex; gap:1rem; align-items:center;"><div>⚠️</div><div>{error}</div></div>'
    elif not calendars:
        cal_list = '<div style="color:var(--text-dim); text-align:center; margin-top:4rem; font-family:\'Rajdhani\';">No active calendars detected.</div>'
    else:
        # Ensure calendars is a list of dicts
        if isinstance(calendars, str):
            cal_list = f'<div style="background:rgba(255,0,85,0.1); border:1px solid var(--neon-pink); padding:1rem; border-radius:12px; color:var(--neon-pink);">Error: {calendars}</div>'
        else:
            cal_items = []
            for c in calendars:
                if isinstance(c, dict):
                    name = c.get('name', 'Unknown')
                    cal_id = c.get('id', 'Unknown')
                    color = c.get('backgroundColor', '#333')
                else:
                    name = str(c)
                    cal_id = ''
                    color = '#333'
                    
                cal_items.append(f'''
                <div class="calendar-card">
                    <div style="position:absolute; top:0; left:0; width:4px; height:100%; background:{color}; box-shadow:0 0 10px {color};"></div>
                    <div style="width:100%">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div class="nav-icon" style="font-size:2rem; filter:drop-shadow(0 0 8px rgba(255,255,255,0.2));">📆</div>
                            <div style="font-size:0.7rem; color:var(--text-dim); border:1px solid var(--glass-border); padding:0.2rem 0.6rem; border-radius:20px;">ACTIVE</div>
                        </div>
                        <div style="margin-top:0.5rem;">
                            <div class="card-title" style="margin-bottom:0.3rem;">{name}</div>
                            <div class="card-desc">{cal_id}</div>
                        </div>
                        <div class="glow-effect" style="position:absolute; bottom:-20px; right:-20px; width:100px; height:100px; background:{color}; filter:blur(50px); opacity:0.15; pointer-events:none;"></div>
                    </div>
                </div>''')
            cal_list = f"<div class='card-grid'>{list(cal_items)}</div>".replace("['", "").replace("']", "").replace("', '", "")

    return f'''
            <div class="chat-header">
                <div>
                    <div class="chat-title" style="color:var(--neon-yellow);">Chrono Sync</div>
                    <div class="chat-subtitle">BetterShift Protocol Interface</div>
                </div>
            </div>
            
            <div class="page-container">
                <p style="color:var(--text-dim); margin-bottom:2rem; font-family:'Rajdhani'; font-size:1.1rem; border-left:2px solid var(--neon-yellow); padding-left:1rem;">
                    Synchronized with external calendar systems.
                </p>
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
        notes_html = '<div style="text-align:center; color:var(--text-dim); margin-top:4rem; font-family:\'Rajdhani\';">Memory banks empty. No records found.</div>'
    else:
        for n in notes:
            notes_html += f'''
                <div class="memory-card" id="note-{n['id']}">
                    <div style="display:flex; gap:1rem; align-items:flex-start;">
                        <div style="font-size:1.5rem; filter:drop-shadow(0 0 5px rgba(255,255,255,0.2));">🧠</div>
                        <div style="flex:1;">
                            <div style="font-size:1rem; line-height:1.6; color:var(--text-main); font-weight:300;">{n['content']}</div>
                            <div style="margin-top:0.8rem; font-size:0.75rem; color:var(--text-dim); text-transform:uppercase; letter-spacing:1px; display:flex; align-items:center; gap:0.5rem;">
                                <span>DATALOG: {n['created_at'][:10]}</span>
                                <span style="width:4px; height:4px; background:var(--text-dim); border-radius:50%;"></span>
                                <span>ID: {n['id']}</span>
                            </div>
                        </div>
                        <button 
                            hx-delete="/memory/delete/{n['id']}" 
                            hx-target="#note-{n['id']}" 
                            hx-swap="outerHTML"
                            style="background:rgba(255,0,85,0.1); border:1px solid var(--neon-pink); color:var(--neon-pink); padding:0.4rem; border-radius:8px; cursor:pointer; font-size:0.9rem; transition:all 0.2s; opacity:0; transform:translateX(10px);"
                            onmouseover="this.style.background='rgba(255,0,85,0.2)'; this.style.boxShadow='0 0 10px rgba(255,0,85,0.2)'"
                            onmouseout="this.style.background='rgba(255,0,85,0.1)'; this.style.boxShadow='none'">
                            🗑️
                        </button>
                    </div>
                </div>'''
    
    return f'''
            <div class="chat-header">
                <div>
                    <div class="chat-title" style="color:var(--neon-blue);">Core Memory</div>
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

async def finance_page(request):
    content = await finance_dashboard.render_finance_view()
    return HTMLResponse(get_base_html("finance", content, ""))

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
        # Filter files with error handling
        filtered_files = []
        for f in files:
            try:
                if query in f.lower() or query in open(f, 'r', encoding='utf-8').read().lower():
                    filtered_files.append(f)
            except Exception:
                continue
        files = filtered_files
        archived_tasks = [t for t in archived_tasks if query in t['description'].lower()]
        
    # Render File List
    file_html = ""
    for f in files:
        name = os.path.basename(f)
        try:
            with open(f, 'r', encoding='utf-8') as file:
                content = file.read()
        except Exception as e:
            content = f"[Error reading file: {e}]"
        
        safe_id = name.replace('.', '_')
        file_html += f'''
            <div id="archive-file-{safe_id}" class="archive-card">
                <div class="info-card" onclick="toggleFile('{safe_id}')" style="cursor:pointer; width:100%; border:none; background:none; padding:0; box-shadow:none; margin:0;">
                    <div style="background:rgba(0,243,255,0.1); width:40px; height:40px; border-radius:8px; display:flex; align-items:center; justify-content:center; color:var(--neon-blue);">📄</div>
                    <div style="flex:1;">
                        <div class="card-title">{name}</div>
                        <div class="card-desc">Click to expand</div>
                    </div>
                    <button 
                        hx-delete="/archives/delete/file/{name}" 
                        hx-confirm="Delete this archive?"
                        hx-target="#archive-file-{safe_id}" 
                        hx-swap="outerHTML"
                        onclick="event.stopPropagation()"
                        style="background:rgba(255,0,85,0.1); border:1px solid var(--neon-pink); color:var(--neon-pink); padding:0.5rem; border-radius:8px; cursor:pointer; transition:all 0.3s; opacity:0; transform:translateX(10px);"
                        class="delete-btn">
                        🗑️
                    </button>
                </div>
                <div id="file-{safe_id}" style="display:none; width:100%; margin-top:1rem; background:rgba(0,0,0,0.3); padding:1.5rem; border-radius:12px; font-family:'Rajdhani', monospace; font-size:0.9rem; white-space:pre-wrap; color:var(--text-dim); border:1px solid var(--glass-border); box-shadow:inset 0 0 20px rgba(0,0,0,0.5);">
                    {content}
                </div>
            </div>'''
        
    # Render Task List
    task_html = ""
    for t in archived_tasks:
        task_html += f'''
            <div class="task-card completed" id="archived-task-{t['id']}">
                <div style="width:20px; height:20px; background:var(--neon-purple); border-radius:4px; display:flex; align-items:center; justify-content:center; color:#fff; font-size:0.8rem;">✓</div>
                <div class="task-text" style="flex:1; color:var(--text-dim); text-decoration:line-through;">
                    {t['description']} 
                    <span style="font-size:0.75em; display:block; margin-top:0.2rem; opacity:0.7;">Completed: {t.get('completed_at', 'unknown')}</span>
                </div>
                <button 
                    hx-delete="/archives/delete/task/{t['id']}" 
                    hx-target="#archived-task-{t['id']}" 
                    hx-swap="outerHTML"
                    style="background:rgba(255,0,85,0.1); border:1px solid var(--neon-pink); color:var(--neon-pink); padding:0.4rem; border-radius:8px; cursor:pointer; opacity:0.5; transition:0.3s;"
                    onmouseover="this.style.opacity='1'"
                    onmouseout="this.style.opacity='0.5'">
                    🗑️
                </button>
            </div>'''
        
    return f'''
            <style>
                .archive-card {{ flex-direction: column; align-items: stretch; }}
                .archive-card:hover .delete-btn {{
                    opacity: 1 !important;
                    transform: translateX(0) !important;
                }}
            </style>
            <div class="chat-header">
                <div>
                    <div class="chat-title" style="color:#fff;">Archives</div>
                    <div class="chat-subtitle">Historical Records & Logs</div>
                </div>
            </div>
            
            <div class="page-container">
                <input type="text" name="q" placeholder="🔍 Search records..." 
                       hx-get="/archives/search" hx-trigger="keyup changed delay:500ms" hx-target="#archive-content"
                       style="margin-bottom: 2rem;">
                       
                <div id="archive-content">
                    <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap:2rem;">
                        <div>
                            <h3 style="margin-bottom:1.5rem; color:var(--neon-blue); font-family:'Orbitron',sans-serif; font-size:1.1rem; letter-spacing:1px; display:flex; align-items:center; gap:0.5rem;">
                                <span>📂</span> CHAT LOGS
                            </h3>
                            {file_html if file_html else '<div style="color:var(--text-dim); padding:2rem; text-align:center; border:1px dashed var(--glass-border); border-radius:12px;">No archival records found.</div>'}
                        </div>
                        <div>
                            <h3 style="margin-bottom:1.5rem; color:var(--neon-purple); font-family:'Orbitron',sans-serif; font-size:1.1rem; letter-spacing:1px; display:flex; align-items:center; gap:0.5rem;">
                                <span>✅</span> MISSION LOG
                            </h3>
                            {task_html if task_html else '<div style="color:var(--text-dim); padding:2rem; text-align:center; border:1px dashed var(--glass-border); border-radius:12px;">No archived objectives.</div>'}
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
    <div class="message ai"><div class="message-avatar"></div><div class="message-content"><div class="message-text">{response_text}</div></div></div>
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
                return HTMLResponse('<div class="message ai"><div class="message-avatar"></div><div class="message-content"><div class="message-text">⚡ <strong>I\'m Awake!</strong> Ready for vision & chat.</div></div></div>')
    except: 
        pass
    
    # Still waiting, return same polling element (recursive poll)
    return HTMLResponse('<div class="message ai"><div class="message-avatar"></div><div class="message-content"><div class="message-text">🌅 Waking up... <span hx-get="/check_wakeup" hx-trigger="load delay:2s" hx-swap="outerHTML">models loading...</span></div></div></div>')


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
        return HTMLResponse('<div class="message ai"><div class="message-avatar"></div><div class="message-content"><div class="message-text">⚡ Already awake! All services running.</div></div></div>')
    
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
    return HTMLResponse(f'<div class="message ai"><div class="message-avatar"></div><div class="message-content"><div class="message-text">🌅 Waking up {services}... <span hx-get="/check_wakeup" hx-trigger="load delay:2s" hx-swap="outerHTML">starting...</span></div></div></div>')


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
        
    return HTMLResponse('<div class="message ai"><div class="message-avatar"></div><div class="message-content"><div class="message-text">😴 Sleep mode activated. MLX + BetterShift stopped.</div></div></div>')


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
        # Security check: Use basename to prevent path traversal (handles URL encoding too)
        filename = os.path.basename(filename)
        
        # Additional validation: only allow .txt files
        if not filename.endswith('.txt'):
            return HTMLResponse(f'<div style="color:var(--neon-pink);">Invalid file type</div>', status_code=400)
        
        filepath = os.path.join("archives", filename)
        
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
                    <div class="message-avatar"></div>
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
        
        # Get completed tasks to archive
        completed_tasks = database.get_tasks(status="completed")
        
        # Write chat history and tasks to file
        with open(filepath, 'w') as f:
            f.write(f"Chat Archive - {timestamp}\n")
            f.write("=" * 60 + "\n\n")
            
            # Write chat history
            f.write("CHAT HISTORY:\n")
            f.write("-" * 60 + "\n\n")
            for msg in history:
                role = msg['role'].upper()
                content = msg['content']
                f.write(f"{role}:\n{content}\n\n")
            
            # Write completed tasks
            if completed_tasks:
                f.write("\n" + "=" * 60 + "\n")
                f.write("COMPLETED TASKS:\n")
                f.write("-" * 60 + "\n\n")
                for task in completed_tasks:
                    f.write(f"✅ {task['description']}\n")
                    f.write(f"   Completed: {task.get('completed_at', 'N/A')}\n\n")
        
        # Clear the database chat history for this session
        database.clear_chat_history(sid)
        
        # Archive completed tasks (mark as 'archived' instead of deleting)
        database.archive_completed_tasks()
        
        # Clear the in-memory session
        if sid in SESSIONS:
            SESSIONS[sid] = []
        
        # Return fresh welcome message
        return HTMLResponse('''
            <div class="message ai">
                <div class="message-avatar"></div>
                <div class="message-content">
                    <div class="message-text">✅ Chat archived! Hello! I'm Echo V3, your local AI assistant. How can I help you today?</div>
                </div>
            </div>
        ''')
        
    except Exception as e:
        return HTMLResponse(f'''
            <div class="message ai">
                <div class="message-avatar"></div>
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
    Route("/finance", finance_page),
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
