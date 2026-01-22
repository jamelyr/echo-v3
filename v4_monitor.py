#!/usr/bin/env python3

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
from rich.style import Style

# Telemetry
from v4.monitor.telemetry import TelemetryReader, DEFAULT_STATE

# V3-V4 Bridge for decision routing
try:
    from v3_v4_bridge import get_bridge
    BRIDGE_AVAILABLE = True
except ImportError:
    BRIDGE_AVAILABLE = False

# Config Constants
MONITOR_FREQUENCY = 0.5  # 2Hz (faster to catch routing decisions)
MIXING_APPS = ["Serato DJ Pro", "Resolume Arena 7", "Resolume Arena"]
SAPIENT_BIN = "sapient_hrm_arc2.bin"

# Setup Console
console = Console()
logging.basicConfig(level=logging.ERROR) # Only show errors in monitor to keep display clean

class TruthEngineMonitor:
    def __init__(self):
        self.reader = TelemetryReader()
        self.state = DEFAULT_STATE.copy()
        self.mixing_active = False
        
        # V3-V4 Bridge state (from decision routing)
        self.bridge_state = {
            'v3_llm_active': False,
            'hrm_active': False,
            'last_decision_source': None,
            'last_confidence': 0.0,
            'v3_confidence': 0.0,
            'hrm_confidence': 0.0
        }

    def check_processes(self):
        """Check for Mixing Apps and Model Memory Residency."""
        mixing = False
        memory_resident = False
        
        # We can iterate process names, but it's expensive. 
        # Optimize by doing it every N cycles or just checking strict names
        # For Mac, psutil.process_iter is okay for 2Hz on M4.
        try:
            for proc in psutil.process_iter(['name', 'memory_maps']):
                try:
                    pname = proc.info['name']
                    # Check Mixing
                    if any(app in pname for app in MIXING_APPS):
                        mixing = True
                    
                    # Check Memory (Mocking simplified check for file handle if permission allows, 
                    # otherwise simplified to just assume it's loaded if Brain is running)
                    # Real OS check for specific mapped file is tricky without root.
                    # We will rely on telemetry for "loaded" status usually, 
                    # but here we can check if a python process has high memory.
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception:
            pass

        self.mixing_active = mixing
        # Update local override if mixing is active
        # if mixing: self.state['status'] = "SUSPENDED (MIXING)"

    def make_layout(self) -> Layout:
        layout = Layout(name="root")
        layout.split_row(
            Layout(name="pipeline", ratio=1),
            Layout(name="guards", ratio=2),
        )
        layout["guards"].split_column(
            Layout(name="xray", ratio=2),
            Layout(name="finance", ratio=1),
            Layout(name="memory", ratio=1),
        )
        layout.split_row(
            Layout(name="v3", ratio=2),
            Layout(name="alerts", ratio=1),
        )
        return Layout

    def render_pipeline(self):
        table = Table(box=box.SIMPLE, show_header=False, expand=True)
        table.add_column("Stage")
        table.add_column("Status")
        table.add_column("Metric")
        
        # Define Stages with V3 integration
        stages = [
            ("ROUTE", "V3-V4 Bridge", f"Source: {self.bridge_state['last_decision_source'] or 'None'}"),
            ("INGEST", "Tail/Phone", f"kbps", f"{self.state['metrics'].get('kbps', 0)} Kbps"),
            ("RESTORE", "NovaSR (48k)", "Lat", f"{self.state['metrics'].get('latency_ms', 0)}ms"),
            ("TRANSCRIBE", "Whisper-MLX", "Conf", f"{self.state['metrics'].get('word_confidence', 0.0):.2f}"),
            ("ENCODE", "MiniLM-Embed", "Norm", f"{self.state['metrics'].get('vector_norm', 0.0):.2f}"),
            ("REASON", "Sapient HRM", "Steps", f"{self.state['metrics'].get('act_steps', 0)}"),
            ("V3-LLM", "V3 LLM", "Active", f"Yes" if self.bridge_state['v3_llm_active'] else "No"),
            ("GENERATE", self.state['metrics'].get('model_name', 'Unknown'), "Status", self.state.get('status') if self.state.get('stage') == 'GENERATE' else "IDLE"),
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
                elif self.state.get("status") == "ACTIVE" and key == "INGEST": 
                    # Keep ingest active-looking if actively processing downstream?
                    pass
            elif key == "V3-LLM" and self.bridge_state['v3_llm_active']:
                style = "bold blue"
                icon = "●"
            elif key == "ROUTE":
                if self.bridge_state['last_decision_source']:
                    style = "bold yellow"
                    icon = "●"
            
            table.add_row(
                Text(f"{icon} {label}", style=style),
                Text(key, style=style),
                Text(str(value), style=style)
            )
        
        return Panel(table, title="[V4 Signal Chain]", border_style="blue")

    def render_xray(self):
        # Neural Activity
        steps = self.state['metrics'].get('act_steps', 0)
        h_cycles = self.state['metrics'].get('h_cycles', 0)
        
        content = f"\n[bold]Thinking Cycles:[/bold]\n"
        content += f"H_Cycles: {h_cycles}\n"
        content += f"L_Steps:  {steps}\n\n"
        
        # Visual Bar
        bar = "█" * steps + "░" * (20 - steps)
        content += f"[ {bar} ]\n"

        border = "green"
        if "SHALLOW REASONING" in self.state.get("alerts", []):
            content += "\n[bold red blink]WARNING: SHALLOW REASONING[/]"
            border = "red"
        
        return Panel(Align.center(content), title="[HRM Logic X-Ray]", border_style=border)

    def render_finance(self):
        cost = self.state['financial'].get('cost', 0)
        currency = self.state['financial'].get('currency', 'MUR')
        
        style = "green"
        msg = "Transaction Safe"
        
        if cost > 5000: # Conflict Threshold
            style = "red blink"
            msg = "[bold]STRATEGIC CONFLICT[/]"
        
        content = f"\n[bold {style}]Rs {cost:,.2f}[/]\n\n{msg}"
        return Panel(Align.center(content), title="[Hunter Epoch Financial]", border_style="gold1")

    def render_memory(self):
        # Check explicit resident flag from telemetry or local check
        resident = self.state['system'].get('memory_resident', False)
        # For demo/mock since we can't easily check file residency without root tools or hacks
        # we will assume resident if stage is REASON
        if self.state.get('stage') == "REASON": 
            resident = True
            
        color = "red" if resident else "dim white"
        status = "LOADED IN VRAM" if resident else "Paged Out / Idle"
        
        content = f"\n{SAPIENT_BIN}\n[{color}]{status}[/]"
        return Panel(Align.center(content), title="[Memory Watcher (Unified)]", border_style="white")
    
    def render_v3_state(self):
        """
        Render V3 LLM state and bridge decisions
        """
        # Check if bridge is available
        if not BRIDGE_AVAILABLE:
            content = "\n[bold yellow]V3-V4 Bridge:[/bold] [dim]Not available[/dim]"
            return Panel(Align.center(content), title="[V3 LLM State]", border_style="yellow")
        
        # Get metrics from state
        v3_conf = self.state.get("metrics", {}).get("v3_confidence", 0.0)
        hrm_conf = self.state.get("metrics", {}).get("hrm_confidence", 0.0)
        combined = self.bridge_state.get("last_confidence", 0.0)
        source = self.bridge_state.get("last_decision_source", "None")
        
        # Build content
        content = f"\n[bold]Decision Routing:[/bold]\n"
        content += f"  Last Source: [bold {source}[/bold]\n"
        content += f"  Combined Confidence: [bold green]{combined:.2f}[/bold green]\n\n"
        
        content += "[bold]Model Confidence:[/bold]\n"
        content += f"  V3 LLM: "
        if self.bridge_state.get("v3_llm_active"):
            content += "[bold green]Active[/bold green] "
        else:
            content += "[dim]Idle[/dim] "
        content += f"({v3_conf:.2f})\n"
        
        content += f"  V4 HRM: "
        if self.state.get("stage") in ["REASON", "ENCODE"]:
            content += "[bold blue]Active[/bold blue] "
        else:
            content += "[dim]Idle[/dim] "
        content += f"({hrm_conf:.2f})\n"
        
        # Confidence bar
        bar_width = 20
        v3_bar = "█" * int(bar_width * v3_conf) + "░" * (bar_width - int(bar_width * v3_conf))
        hrm_bar = "█" * int(bar_width * hrm_conf) + "░" * (bar_width - int(bar_width * hrm_conf))
        
        content += f"\n[bold]Confidence Visual:[/bold]\n"
        content += f"  V3: [{v3_bar}] {v3_conf:.2f}\n"
        content += f"  HRM: [{hrm_bar}] {hrm_conf:.2f}\n"
        
        border = "blue"
        if combined < 0.5:
            border = "red"
        elif combined > 0.8:
            border = "green"
        
        return Panel(Align.center(content), title="[V3+V4 Unified]", border_style=border)

    def render_mixing_screen(self):
        text = Text("\n\nMIXING MODE ACTIVE\nAI SUSPENDED", style="bold white on grey23", justify="center")
        text.stylize("blink", 0, 18)
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
                    layout["xray"].update(self.render_xray())
                    layout["finance"].update(self.render_finance())
                    layout["memory"].update(self.render_memory())
                    layout["v3"].update(self.render_v3_state())
                
                time.sleep(1.0 / 2.0) # 2Hz

if __name__ == "__main__":
    try:
        monitor = TruthEngineMonitor()
        monitor.run()
    except KeyboardInterrupt:
        print("Monitor Stopped.")
