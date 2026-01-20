# WYGIWYH Integration - Setup Guide

## Install WYGIWYH (No Docker)

```bash
cd /Users/marley/Documents/ag
git clone https://github.com/eitchtee/WYGIWYH.git wygiwyh
cd wygiwyh
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
```

## First-time Setup

1. Start WYGIWYH manually first:

```bash
cd /Users/marley/Documents/ag/wygiwyh
python manage.py runserver 0.0.0.0:8000
```

1. Open <http://localhost:8000> and login

2. Go to Settings → Currencies → Add MUR (Mauritian Rupee)

3. Create your first account (e.g., "Main Account", currency: MUR)

## Automatic Start/Stop

WYGIWYH now starts/stops with `run_all.sh`:

```bash
./run_all.sh start   # Starts Echo + WYGIWYH + BetterShift
./run_all.sh stop    # Stops all
./run_all.sh status  # Check what's running
```

## Usage

### Chat Commands

- "What's my balance?"
- "I spent 500 rupees on food"
- "Add income of 25000 from salary"
- "Show monthly summary"

### Dashboard

Navigate to <http://localhost:5001/finance> (or click Treasury in sidebar)
