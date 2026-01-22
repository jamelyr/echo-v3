#!/usr/bin/env python3
"""
V4 Monitor (Simplified - No HRM)
Telemetry display for V3-only system
"""
import time
import psutil
import logging
from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.text import Text
from rich.align import Align

# Telemetry
from v4.monitor.telemetry import TelemetryReader, DEFAULT_STATE

# Config Constants
MONITOR_FREQUENCY = 0.5  # 2Hz
MIXING_APPS = ["Serato DJ Pro", "Resolume Arena 7", "Resolume Arena", "Final Cut Pro", "Logic Pro"]

# Setup Console
console = Console()
logging.basicConfig(level=logging.ERROR) # Only show errors in monitor to keep display clean

class V3Monitor:
    def __init__(self):
        self.reader = TelemetryReader()
        self.state = DEFAULT_STATE.copy()
        self.mixing_active = False
    
    def check_processes(self):
        """Check for Mixing Apps"""
        mixing = False
        
        try:
            for proc in psutil.process_iter(['name']):
                try:
                    pname = proc.info['name']
                    if any(app in pname for app in MIXING_APPS):
                        mixing = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception:
            pass
        
        self.mixing_active = mixing
    
    def make_layout(self) -> Layout:
        layout = Layout(name="root")
        layout.split_row(
            Layout(name="pipeline", ratio=1),
            Layout(name="system", ratio=1),
        )
        layout["system"].split_column(
            Layout(name="finance", ratio=1),
            Layout(name="status", ratio=1),
        )
        return layout
    
    def render_pipeline(self):
        table = Table(box=box.SIMPLE, show_header=False, expand=True)
        table.add_column("Stage")
        table.add_column("Status")
        table.add_column("Metric")
        
        # Simplified pipeline stages (V3 only)
        stages = [
            ("INGEST", "Audio Input", f"kbps", f"{self.state['metrics'].get('kbps', 0)} Kbps"),
            ("RESTORE", "NovaSR (48k)", "Lat", f"{self.state['metrics'].get('latency_ms', 0)}ms"),
            ("TRANSCRIBE", "Whisper-MLX", "Conf", f"{self.state['metrics'].get('word_confidence', 0.0):.2f}"),
            ("ENCODE", "MiniLM-Embed", "Norm", f"{self.state['metrics'].get('vector_norm', 0.0):.2f}"),
            ("V3-LLM", "V3 LLM", "Status", self.state.get('status') if self.state.get('stage') == 'V3-LLM' else "IDLE"),
            ("ACT", "Executor", "Cost", f"Rs {self.state['financial'].get('cost', 0)}")
        ]
        
        current_stage = self.state.get("stage", "IDLE")
        
        for key, label, metric_name, value in stages:
            style = "dim"
            icon = "○"
            if key == current_stage:
                style = "bold green"
                icon = "●"
                if self.state.get("status") == "BLOCKED":
                    style = "bold red"
                    icon = "x"
            
            table.add_row(
                Text(f"{icon} {label}", style=style),
                Text(key, style=style),
                Text(str(value), style=style)
            )
        
        return Panel(table, title="[V3 Signal Chain]", border_style="blue")
    
    def render_finance(self):
        cost = self.state['financial'].get('cost', 0)
        
        style = "green"
        msg = "Transaction Safe"
        
        if cost > 5000: # Conflict Threshold
            style = "red blink"
            msg = "[bold]STRATEGIC CONFLICT[/]"
        
        content = f"\n[bold {style}]Rs {cost:,.2f}[/]\n\n{msg}"
        return Panel(Align.center(content), title="[Hunter Epoch Financial]", border_style="gold1")
    
    def render_status(self):
        """Render system status"""
        # V3 State
        v3_active = self.state.get('stage') in ['TRANSCRIBE', 'V3-LLM', 'ACT']
        
        # System stats
        cpu = psutil.cpu_percent(interval=0.1)
        
        content = f"\n[bold]System Status:[/bold]\n"
        content += f"  V3 LLM: "
        if v3_active:
            content += "[bold green]Active[/bold green]\n"
        else:
            content += "[dim]Idle[/dim]\n"
        
        content += f"\n  CPU: {cpu:.1f}%\n"
        
        if self.mixing_active:
            content += "\n[bold red]MIXING MODE ACTIVE[/bold red]\n"
            content += "[dim]Audio processing paused[/dim]\n"
        
        border = "blue"
        
        return Panel(Align.center(content), title="[System Status]", border_style=border)
    
    def render_mixing_screen(self):
        text = Text("\n\nMIXING MODE ACTIVE\nAI SUSPENDED", style="bold white on grey23", justify="center")
        return Panel(Align.center(text), style="on grey23")
    
    def run(self):
        layout = self.make_layout()
        
        with Live(layout, refresh_per_second=2, screen=True) as live:
            while True:
                # 1. Update State
                self.state = self.reader.read()
                self.check_processes()
                
                # 2. Render
                if self.mixing_active:
                    live.update(self.render_mixing_screen())
                else:
                    layout["pipeline"].update(self.render_pipeline())
                    layout["finance"].update(self.render_finance())
                    layout["status"].update(self.render_status())
                
                time.sleep(1.0 / 2.0) # 2Hz


if __name__ == "__main__":
    try:
        monitor = V3Monitor()
        monitor.run()
    except KeyboardInterrupt:
        print("Monitor Stopped.")
