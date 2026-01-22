#!/usr/bin/env python3
"""
Antigravity Worker (ag) - V3+V4 Integrated
The tactical agent that executes commands approved by V4's Hunter Epoch
Connected to V4 decision system via message queue (file-based for now)
"""
import sys
import os
import subprocess
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import sqlite3

# Setup
ACTION_QUEUE_DIR = Path(os.path.expanduser("~/Documents/ag/v4/queue/actions"))
APPROVED_DIR = ACTION_QUEUE_DIR / "approved"
COMPLETED_DIR = ACTION_QUEUE_DIR / "completed"
PENDING_DIR = ACTION_QUEUE_DIR / "pending"

# Create directories
for d in [APPROVED_DIR, COMPLETED_DIR, PENDING_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Logging
LOG_FILE = os.path.expanduser("~/echo/antigravity.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AntigravityWorker")

class AntigravityWorker:
    """
    Tactical agent that executes Hunter Epoch approved actions
    """
    
    def __init__(self, auto_start=True):
        """
        Initialize worker
        
        Args:
            auto_start: If True, start monitoring immediately
        """
        self.running = False
        self.worker_id = os.getpid()
        logger.info(f"Worker {self.worker_id} initialized")
        
        if auto_start:
            asyncio.create_task(self.monitor_approved_actions())
    
    def log_action(self, action_type: str, details: str, status: str = "START"):
        """
        Log action to file and console
        
        Args:
            action_type: Type of action (SHELL, PYTHON, TASK, etc.)
            details: Action description
            status: Status (START, SUCCESS, FAILURE, BLOCKED)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [ACTION:{action_type}] [{status}] {details}\n"
        
        with open(LOG_FILE, "a") as f:
            f.write(entry)
        
        emoji_map = {
            "START": "🚀",
            "SUCCESS": "✅",
            "FAILURE": "❌",
            "BLOCKED": "🚫",
            "VERIFY": "⚠️"
        }
        print(f"Antigravity: {emoji_map.get(status, '📋')} {entry.strip()}")
    
    async def execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an approved action
        
        Args:
            action: Action dict from V4
        
        Returns:
            Execution result dict
        """
        action_type = action.get("type", "unknown")
        action_id = action.get("id", "unknown")
        
        logger.info(f"Executing action {action_id} of type {action_type}")
        self.log_action(action_type.upper(), f"Action ID: {action_id}", "START")
        
        try:
            if action_type == "shell":
                result = await self._execute_shell(action)
            elif action_type == "python":
                result = await self._execute_python(action)
            elif action_type == "task":
                result = await self._execute_task(action)
            elif action_type == "database":
                result = await self._execute_database(action)
            else:
                result = {
                    "success": False,
                    "error": f"Unknown action type: {action_type}",
                    "status": "FAILURE"
                }
            
            # Add metadata
            result["action_id"] = action_id
            result["worker_id"] = self.worker_id
            
            if result.get("success"):
                self.log_action(action_type.upper(), f"Completed: {action_id}", "SUCCESS")
            else:
                self.log_action(action_type.upper(), f"Failed: {result.get('error')}", "FAILURE")
            
            return result
            
        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            result = {
                "success": False,
                "error": str(e),
                "action_id": action_id,
                "worker_id": self.worker_id,
                "status": "FAILURE"
            }
            self.log_action(action_type.upper(), f"Exception: {str(e)}", "FAILURE")
            return result
    
    async def _execute_shell(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute shell command
        
        Args:
            action: Action dict with 'command' key
        
        Returns:
            Execution result
        """
        command = action.get("command", "")
        timeout = action.get("timeout", 60)
        
        logger.info(f"Executing shell: {command}")
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            success = process.returncode == 0
            
            return {
                "success": success,
                "output": stdout.decode('utf-8', errors='replace'),
                "error": stderr.decode('utf-8', errors='replace'),
                "return_code": process.returncode,
                "status": "SUCCESS" if success else "FAILURE"
            }
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Command timed out after {timeout}s",
                "status": "FAILURE"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status": "FAILURE"
            }
    
    async def _execute_python(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Python code
        
        Args:
            action: Action dict with 'code' key
        
        Returns:
            Execution result
        """
        code = action.get("code", "")
        timeout = action.get("timeout", 60)
        
        logger.info(f"Executing Python code (length: {len(code)})")
        
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                ["-c", code],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            success = process.returncode == 0
            
            return {
                "success": True,
                "output": stdout.decode('utf-8', errors='replace'),
                "error": stderr.decode('utf-8', errors='replace'),
                "return_code": process.returncode,
                "status": "SUCCESS" if success else "FAILURE"
            }
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Python execution timed out after {timeout}s",
                "status": "FAILURE"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status": "FAILURE"
            }
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Python execution timed out after {timeout}s",
                "status": "FAILURE"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status": "FAILURE"
            }
    
    async def _execute_task(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute task-related action via database
        
        Args:
            action: Action dict with 'operation' key
        
        Returns:
            Execution result
        """
        operation = action.get("operation", "")
        params = action.get("params", {})
        
        logger.info(f"Executing task operation: {operation}")
        
        try:
            import database
            database.init_db()
            
            result = {"success": True, "status": "SUCCESS"}
            
            if operation == "add_task":
                description = params.get("description", "")
                task_id = database.add_task(description)
                result["task_id"] = task_id
                result["output"] = f"Task added with ID: {task_id}"
            
            elif operation == "complete_task":
                task_id = params.get("task_id", 0)
                success = database.complete_task(task_id)
                result["task_id"] = task_id
                result["output"] = f"Task {task_id} completed: {success}"
            
            elif operation == "list_tasks":
                tasks = database.get_tasks(status=params.get("status"))
                result["tasks"] = tasks
                result["output"] = f"Found {len(tasks)} tasks"
            
            else:
                result["success"] = False
                result["error"] = f"Unknown operation: {operation}"
                result["status"] = "FAILURE"
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status": "FAILURE"
            }
    
    async def _execute_database(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute database query
        
        Args:
            action: Action dict with 'query' key
        
        Returns:
            Execution result
        """
        query = action.get("query", "")
        params = action.get("params", [])
        
        logger.info(f"Executing database query")
        
        try:
            import sqlite3
            conn = sqlite3.connect('echo.db')
            cursor = conn.cursor()
            
            cursor.execute(query, params)
            
            if query.strip().upper().startswith("SELECT"):
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in rows]
                
                conn.close()
                return {
                    "success": True,
                    "status": "SUCCESS",
                    "output": json.dumps(results, indent=2),
                    "row_count": len(results)
                }
            else:
                conn.commit()
                conn.close()
                return {
                    "success": True,
                    "status": "SUCCESS",
                    "output": f"Query executed successfully",
                    "row_count": cursor.rowcount
                }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status": "FAILURE"
            }
    
    async def monitor_approved_actions(self):
        """
        Monitor approved action queue and execute actions
        
        Continuously watches for new files in approved directory
        """
        self.running = True
        logger.info("Starting action monitor...")
        
        processed_ids = set()
        
        while self.running:
            try:
                # Check for new approved actions
                if APPROVED_DIR.exists():
                    for action_file in APPROVED_DIR.glob("*.json"):
                        try:
                            action_id = action_file.stem
                            
                            if action_id in processed_ids:
                                continue
                            
                            # Read action
                            with open(action_file, 'r') as f:
                                action = json.load(f)
                            
                            logger.info(f"New approved action: {action_id}")
                            
                            # Execute action
                            result = await self.execute_action(action)
                            
                            # Move to completed
                            completed_file = COMPLETED_DIR / f"{action_id}.json"
                            action_file.rename(completed_file)
                            
                            # Save result
                            result_file = COMPLETED_DIR / f"{action_id}_result.json"
                            with open(result_file, 'w') as f:
                                json.dump(result, f, indent=2)
                            
                            processed_ids.add(action_id)
                            
                            # If verification requested, move to pending
                            if action.get("requires_verification", False):
                                pending_file = PENDING_DIR / f"{action_id}_verify.json"
                                result_file.rename(pending_file)
                                logger.warning(f"Action {action_id} requires verification")
                            
                        except Exception as e:
                            logger.error(f"Failed to process action {action_file}: {e}")
                            # Move to failed
                            if action_file.exists():
                                failed_file = COMPLETED_DIR / f"{action_file.stem}_failed.json"
                                try:
                                    action_file.rename(failed_file)
                                except:
                                    pass
                
                # Wait before next check
                await asyncio.sleep(2)
                
            except asyncio.CancelledError:
                logger.info("Worker monitor cancelled")
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(5)
    
    def stop(self):
        """
        Stop the worker monitor
        """
        self.running = False
        logger.info("Worker stopping...")


def main():
    """
    Main entry point for command-line usage
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Antigravity Tactical Agent - V3+V4 Integrated")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Command: START (Monitor approved actions)
    start_parser = subparsers.add_parser("start", help="Start action monitor")
    start_parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    
    # Command: EXECUTE (Run single action)
    exec_parser = subparsers.add_parser("execute", help="Execute single action")
    exec_parser.add_argument("--type", required=True, help="Action type (shell, python, task, database)")
    exec_parser.add_argument("--command", help="Shell command to execute")
    exec_parser.add_argument("--code", help="Python code to execute")
    exec_parser.add_argument("--operation", help="Task operation")
    exec_parser.add_argument("--params", help="Operation params (JSON string)")
    
    # Command: SYNC (Repo updates)
    sync_parser = subparsers.add_parser("sync", help="Sync repositories")
    sync_parser.add_argument("--target", help="Target repo", default="all")
    
    args = parser.parse_args()
    
    if args.command == "start":
        if args.daemon:
            logger.info("Starting as daemon...")
            # TODO: Implement daemon mode
            print("Daemon mode not yet implemented. Use screen/tmux instead.")
        else:
            logger.info("Starting interactive monitor...")
            worker = AntigravityWorker(auto_start=True)
            
            # Run forever
            try:
                loop = asyncio.get_event_loop()
                loop.run_forever()
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                worker.stop()
    
    elif args.command == "execute":
        worker = AntigravityWorker(auto_start=False)
        
        action = {"id": f"manual_{datetime.now().timestamp()}"}
        action["type"] = args.type
        
        if args.type == "shell":
            action["command"] = args.command or "echo 'Hello from Antigravity Worker'"
        elif args.type == "python":
            action["code"] = args.code or "print('Hello from Antigravity Worker')"
        elif args.type == "task":
            action["operation"] = args.operation
            if args.params:
                import json
                action["params"] = json.loads(args.params)
        elif args.type == "database":
            action["query"] = args.command
            if args.params:
                import json
                action["params"] = json.loads(args.params)
        
        # Execute and print result
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(worker.execute_action(action))
        
        print("\n" + "="*60)
        print("EXECUTION RESULT")
        print("="*60)
        print(json.dumps(result, indent=2))
        print("="*60)
    
    elif args.command == "sync":
        logger.info(f"Syncing {args.target}...")
        # Simulation of git fetch/pull
        print(f"Antigravity: Syncing {args.target}...")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()