"""Tkinter application shell for GlyphX."""

from __future__ import annotations

import json
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from .services.export import ExportService, ExportSummary
from .services.llm import ChatMessage, LLMClient

from .infra.chat_history import ChatHistory
from .infra.diagnostics import CrashReporter, UpdateChecker
from .infra.history import CommandHistory, CommandRecord
from .infra.logger import LogEvent, Logger
from .infra.paths import AppPaths, ensure_app_paths
from .infra.worker import Worker
from .services.registry import Glyph, GlyphCreate, RegistryService
from .services.settings import SettingsService
from .services.tools import ToolsBridge
from .services.auto_tagger import AutoTagger
from .services.description_generator import DescriptionGenerator
from .services.session_summarizer import SessionSummarizer
from .services.intent_parser import IntentParser
from .services.classifier import CommandClassifier


DEFAULT_AGENT_PROMPT = (
    "You are GlyphX Agent, a focused assistant that can run saved glyphs, execute shell commands, "
    "and read or write local files when helpful. Complete the user's goal efficiently and report a "
    "concise summary of what you accomplished."
)


class SidebarPanel(ttk.Frame):
    """Navigation sidebar with vertical tabs."""

    def __init__(self, master: tk.Misc, on_section_change: callable) -> None:
        super().__init__(master, padding=4, relief="raised", borderwidth=1)
        self._on_section_change = on_section_change
        self._buttons: dict[str, ttk.Button] = {}
        self._current_section: Optional[str] = None
        
        # Configure layout
        self.columnconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(self, text="GlyphX", font=("Segoe UI", 14, "bold"))
        title_label.grid(row=0, column=0, pady=(8, 16), sticky="ew")
        
        # Separator
        ttk.Separator(self, orient="horizontal").grid(row=1, column=0, sticky="ew", pady=8)
        
        # Navigation buttons
        sections = [
            ("📁 File", "file"),
            ("🏷️ Glyphs", "glyphs"),
            ("💬 Terminal & AI", "terminal"),
            ("📊 Console", "console"),
            ("⚙️ Settings", "settings"),
            ("📦 Data Archive", "archive"),
        ]
        
        for idx, (label, section_id) in enumerate(sections):
            btn = ttk.Button(
                self,
                text=label,
                command=lambda s=section_id: self._select_section(s),
                width=18,
            )
            btn.grid(row=idx + 2, column=0, pady=2, sticky="ew", padx=4)
            self._buttons[section_id] = btn
        
        # Spacer
        spacer = ttk.Frame(self)
        spacer.grid(row=len(sections) + 2, column=0, sticky="nsew")
        self.rowconfigure(len(sections) + 2, weight=1)
        
        # Bottom separator
        ttk.Separator(self, orient="horizontal").grid(row=len(sections) + 3, column=0, sticky="ew", pady=8)
        
        # Version info at bottom
        version_label = ttk.Label(self, text="v0.1.0", foreground="gray", font=("Segoe UI", 9))
        version_label.grid(row=len(sections) + 4, column=0, pady=(0, 8))
    
    def _select_section(self, section_id: str) -> None:
        """Handle section selection."""
        if section_id == self._current_section:
            return
        
        # Update button states
        for sid, btn in self._buttons.items():
            if sid == section_id:
                btn.state(["pressed"])
            else:
                btn.state(["!pressed"])
        
        self._current_section = section_id
        self._on_section_change(section_id)
    
    def set_section(self, section_id: str) -> None:
        """Programmatically set the current section."""
        self._select_section(section_id)


class TerminalPanel(ttk.Frame):
    """Interactive terminal emulator panel."""

    def __init__(
        self,
        master: tk.Misc,
        tools: ToolsBridge,
        worker: Worker,
        logger: Logger,
        command_history: CommandHistory,
        session_summarizer=None,
        llm_client=None,
    ) -> None:
        super().__init__(master, padding=8)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._tools = tools
        self._worker = worker
        self._logger = logger
        self._command_history = command_history
        self._session_summarizer = session_summarizer
        self._llm_client = llm_client
        self._is_running = False
        self._ai_mode = tk.BooleanVar(value=False)
        self._cwd_var = tk.StringVar(value=str(Path.cwd()))

        # Header with working directory
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(1, weight=1)
        
        ttk.Label(header, text="Working Directory:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        cwd_entry = ttk.Entry(header, textvariable=self._cwd_var)
        cwd_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ttk.Button(header, text="Browse…", command=self._browse_cwd).grid(row=0, column=2)
        ttk.Button(header, text="Clear", command=self._clear_output).grid(row=0, column=3, padx=(8, 0))
        
        # Add Summarize button if session summarizer is available
        if self._session_summarizer:
            ttk.Button(header, text="📝 Summarize", command=self._summarize_session).grid(row=0, column=4, padx=(8, 0))
        
        # Add AI toggle if LLM client is available
        if self._llm_client:
            ttk.Checkbutton(
                header, 
                text="🤖 AI Assistant", 
                variable=self._ai_mode,
                command=self._toggle_ai_mode
            ).grid(row=0, column=5, padx=(8, 0))

        # Output display
        output_frame = ttk.Frame(self)
        output_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        self._output = tk.Text(
            output_frame,
            wrap="word",
            state="disabled",
            height=20,
            font=("Consolas", 10),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="#ffffff",
        )
        output_scroll = ttk.Scrollbar(output_frame, command=self._output.yview)
        self._output.configure(yscrollcommand=output_scroll.set)
        self._output.grid(row=0, column=0, sticky="nsew")
        output_scroll.grid(row=0, column=1, sticky="ns")

        # Configure text tags for colored output
        self._output.tag_config("prompt", foreground="#569cd6", font=("Consolas", 10, "bold"))
        self._output.tag_config("command", foreground="#9cdcfe")
        self._output.tag_config("stdout", foreground="#d4d4d4")
        self._output.tag_config("stderr", foreground="#f48771")
        self._output.tag_config("error", foreground="#f48771", font=("Consolas", 10, "bold"))
        self._output.tag_config("success", foreground="#4ec9b0")
        self._output.tag_config("ai", foreground="#c586c0", font=("Consolas", 10, "italic"))

        # Command input
        input_frame = ttk.Frame(self)
        input_frame.grid(row=2, column=0, sticky="ew")
        input_frame.columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="$", font=("Consolas", 10, "bold")).grid(row=0, column=0, padx=(0, 8))
        self._input = ttk.Entry(input_frame, font=("Consolas", 10))
        self._input.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self._input.bind("<Return>", self._on_execute)
        self._input.bind("<Up>", self._history_prev)
        self._input.bind("<Down>", self._history_next)

        self._run_button = ttk.Button(input_frame, text="Run", command=self._on_execute)
        self._run_button.grid(row=0, column=2)

        self._history_index = -1
        self._history_cache: list[str] = []
        
        # Initial prompt
        self._append_prompt()

    def _browse_cwd(self) -> None:
        """Browse for working directory."""
        from tkinter import filedialog
        directory = filedialog.askdirectory(
            parent=self.winfo_toplevel(),
            title="Select Working Directory",
            initialdir=self._cwd_var.get(),
        )
        if directory:
            self._cwd_var.set(directory)

    def _clear_output(self) -> None:
        """Clear the terminal output."""
        self._output.configure(state="normal")
        self._output.delete("1.0", "end")
        self._output.configure(state="disabled")
        self._append_prompt()

    def _append_prompt(self) -> None:
        """Append a command prompt."""
        cwd = Path(self._cwd_var.get()).name or self._cwd_var.get()
        self._output.configure(state="normal")
        self._output.insert("end", f"\n{cwd} ", "prompt")
        self._output.insert("end", "$ ", "prompt")
        self._output.configure(state="disabled")
        self._output.see("end")

    def _append_text(self, text: str, tag: str = "stdout") -> None:
        """Append text to the output."""
        self._output.configure(state="normal")
        self._output.insert("end", text, tag)
        self._output.configure(state="disabled")
        self._output.see("end")

    def _history_prev(self, _event: object = None) -> None:
        """Navigate to previous command in history."""
        if not self._history_cache:
            self._history_cache = [
                rec.command for rec in self._command_history.tail()
                if rec.source in ("terminal", "chat", "agent")
            ]
        if not self._history_cache:
            return
        
        if self._history_index < len(self._history_cache) - 1:
            self._history_index += 1
            self._input.delete(0, "end")
            self._input.insert(0, self._history_cache[-(self._history_index + 1)])

    def _history_next(self, _event: object = None) -> None:
        """Navigate to next command in history."""
        if self._history_index > 0:
            self._history_index -= 1
            self._input.delete(0, "end")
            self._input.insert(0, self._history_cache[-(self._history_index + 1)])
        elif self._history_index == 0:
            self._history_index = -1
            self._input.delete(0, "end")

    def _on_execute(self, *_args: object) -> None:
        """Execute the command or AI query."""
        if self._is_running:
            return
        
        command = self._input.get().strip()
        if not command:
            return

        # AI Mode: Send to LLM for interpretation
        if self._ai_mode.get() and self._llm_client:
            self._execute_ai_command(command)
            return

        # Handle built-in commands
        if command.lower() in ("clear", "cls"):
            self._clear_output()
            self._input.delete(0, "end")
            return

        if command.lower().startswith("cd "):
            new_dir = command[3:].strip()
            try:
                new_path = Path(new_dir).expanduser().resolve()
                if new_path.is_dir():
                    self._cwd_var.set(str(new_path))
                    self._append_text(command + "\n", "command")
                    self._append_prompt()
                else:
                    self._append_text(command + "\n", "command")
                    self._append_text(f"cd: not a directory: {new_dir}\n", "error")
                    self._append_prompt()
            except Exception as exc:
                self._append_text(command + "\n", "command")
                self._append_text(f"cd: {exc}\n", "error")
                self._append_prompt()
            self._input.delete(0, "end")
            return

        # Display command
        self._append_text(command + "\n", "command")
        self._input.delete(0, "end")
        self._set_running(True)
        
        # Save to history
        self._command_history.append("terminal", command)
        self._history_index = -1
        self._history_cache = []

        # Log command
        self._logger.info("terminal_exec", command=command, cwd=self._cwd_var.get())

        # Execute command via worker
        def job() -> dict[str, str]:
            try:
                return self._tools.run_shell(command, cwd=self._cwd_var.get())
            except Exception as exc:
                return {
                    "label": "error",
                    "returncode": "-1",
                    "stdout": "",
                    "stderr": f"Execution error: {exc}",
                }

        def callback(result: dict[str, str]) -> None:
            def display() -> None:
                self._set_running(False)
                
                # Display output
                stdout = result.get("stdout", "")
                stderr = result.get("stderr", "")
                returncode = result.get("returncode", "0")

                if stdout:
                    self._append_text(stdout, "stdout")
                    if not stdout.endswith("\n"):
                        self._append_text("\n", "stdout")
                
                if stderr:
                    self._append_text(stderr, "stderr")
                    if not stderr.endswith("\n"):
                        self._append_text("\n", "stderr")

                # Show exit code if non-zero
                if returncode != "0":
                    self._append_text(f"[Exit code: {returncode}]\n", "error")
                
                self._append_prompt()
                self._input.focus_set()

            self.after(0, display)

        self._worker.submit(job, description="terminal_command", callback=callback)
    
    def _toggle_ai_mode(self) -> None:
        """Toggle AI assistant mode."""
        if self._ai_mode.get():
            self._append_text("\n[🤖 AI Assistant enabled - ask me anything!]\n", "success")
            self._input.delete(0, "end")
            self._input.insert(0, "")
        else:
            self._append_text("\n[Terminal mode - direct command execution]\n", "stdout")
    
    def _execute_ai_command(self, query: str) -> None:
        """Execute an AI-assisted command."""
        self._append_text(f"🤖 {query}\n", "command")
        self._input.delete(0, "end")
        self._set_running(True)
        
        # Get recent terminal context
        recent_commands = self._command_history.tail(5)
        context_lines = [f"  {r.command}" for r in recent_commands if r.source == "terminal"]
        context = "\n".join(context_lines) if context_lines else "  (no recent commands)"
        
        # Build AI prompt
        system_prompt = f"""You are a terminal assistant helping the user with shell commands.

Current working directory: {self._cwd_var.get()}
Recent commands:
{context}

When the user asks a question:
1. If they want to run a command, respond with ONLY the command to execute (no explanation)
2. If they ask for help/explanation, provide a brief, helpful response
3. If they ask "run X" or "execute Y", provide the appropriate command

Be concise and practical. Assume the user is on Windows using PowerShell."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        def job():
            try:
                response = self._llm_client.chat(messages, stream=False)
                # Extract content from OpenAI API response format
                choices = response.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    return message.get("content", "")
                return ""
            except Exception as exc:
                return f"AI Error: {exc}"
        
        def callback(result):
            def display():
                self._set_running(False)
                
                if result.startswith("AI Error:"):
                    self._append_text(f"{result}\n", "error")
                else:
                    # Check if response looks like a command (short, no explanation)
                    lines = result.strip().split('\n')
                    if len(lines) == 1 and len(result) < 100 and not any(word in result.lower() for word in ['here', 'you can', 'this will', 'command']):
                        # Looks like a command - ask if user wants to run it
                        self._append_text(f"💡 Suggested command: {result}\n", "success")
                        self._append_text("Press Enter to run it, or edit first.\n", "stdout")
                        self._input.insert(0, result.strip())
                    else:
                        # Looks like an explanation
                        self._append_text(f"{result}\n", "stdout")
                
                self._append_prompt()
                self._input.focus_set()
            
            self.after(0, display)
        
        self._worker.submit(job, description="ai_terminal_query", callback=callback)
    
    def _summarize_session(self) -> None:
        """Summarize recent terminal commands using Gemma."""
        if not self._session_summarizer:
            return
        
        def job():
            try:
                return self._session_summarizer.summarize_recent(self._command_history, limit=10)
            except Exception as exc:
                return f"Error generating summary: {exc}"
        
        def callback(result):
            if isinstance(result, Exception):
                messagebox.showerror(
                    "Session Summary",
                    f"Failed to generate summary: {result}",
                    parent=self.winfo_toplevel()
                )
            else:
                messagebox.showinfo(
                    "Session Summary",
                    result,
                    parent=self.winfo_toplevel()
                )
        
        self._worker.submit(job, description="summarize_session", callback=callback)

    def _set_running(self, running: bool) -> None:
        """Update UI state during command execution."""
        self._is_running = running
        state = tk.DISABLED if running else tk.NORMAL
        self._input.configure(state=state)
        self._run_button.configure(state=state)


class ConsolePanel(ttk.Frame):
    """Append-only text area for logs."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self._text = tk.Text(self, wrap="word", state="disabled", height=12)
        vsb = ttk.Scrollbar(self, command=self._text.yview)
        self._text.configure(yscrollcommand=vsb.set)
        self._text.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

    def append(self, event: LogEvent) -> None:
        self._text.configure(state="normal")
        payload = f"[{event.level}] {event.message}"
        if event.context:
            ctx = " ".join(f"{k}={v}" for k, v in event.context.items())
            payload = f"{payload} {ctx}"
        self._text.insert("end", payload + "\n")
        self._text.configure(state="disabled")
        self._text.see("end")


class GlyphsPanel(ttk.Frame):
    """Glyphs list with Add/Edit/Remove/Run actions."""

    def __init__(
        self,
        master: tk.Misc,
        registry: RegistryService,
        worker: Worker,
        tools: ToolsBridge,
        logger: Logger,
        history: CommandHistory,
        auto_tagger=None,
        description_generator=None,
    ) -> None:
        super().__init__(master, padding=8)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        self._registry = registry
        self._worker = worker
        self._tools = tools
        self._logger = logger
        self._history_service = history
        self._auto_tagger = auto_tagger
        self._description_generator = description_generator
        self._all_items: list[Glyph] = []
        self._items: list[Glyph] = []
        self._details_var = tk.StringVar(value="Double-click a glyph to run it.")
        self._search_var = tk.StringVar()

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Glyphs").grid(row=0, column=0, sticky="w")
        btn_frame = ttk.Frame(header)
        btn_frame.grid(row=0, column=1, sticky="e")
        self._btn_add = ttk.Button(btn_frame, text="Add", command=self._add_glyph)
        self._btn_edit = ttk.Button(btn_frame, text="Edit", command=self._edit_glyph, state="disabled")
        self._btn_remove = ttk.Button(btn_frame, text="Remove", command=self._remove_glyph, state="disabled")
        self._btn_run = ttk.Button(btn_frame, text="Run", command=self._run_selected, state="disabled")
        self._btn_import = ttk.Button(btn_frame, text="Import…", command=self._import_glyphs)
        for i, btn in enumerate((self._btn_add, self._btn_edit, self._btn_remove, self._btn_run, self._btn_import)):
            btn.grid(row=0, column=i, padx=(4 if i else 0, 0))

        search_frame = ttk.Frame(self)
        search_frame.grid(row=1, column=0, sticky="ew")
        ttk.Label(search_frame, text="Search").grid(row=0, column=0, sticky="w")
        entry = ttk.Entry(search_frame, textvariable=self._search_var)
        entry.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        search_frame.columnconfigure(1, weight=1)
        self._search_var.trace_add("write", lambda *_: self._apply_filter())

        self._list = tk.Listbox(self, height=12, activestyle="none")
        self._list.grid(row=2, column=0, sticky="nsew", pady=(6, 4))
        self._list.bind("<Double-1>", lambda _e: self._run_selected())
        self._list.bind("<<ListboxSelect>>", lambda _e: self._update_buttons())
        self.bind_all("<Control-n>", lambda _e: self._add_glyph())
        self.bind_all("<Control-r>", lambda _e: self._run_selected())
        self.bind_all("<Delete>", lambda _e: self._remove_glyph())

        self._details_label = ttk.Label(self, textvariable=self._details_var, justify="left")
        self._details_label.grid(row=3, column=0, sticky="ew", pady=(4, 10))

        history_frame = ttk.LabelFrame(self, text="Command History")
        history_frame.grid(row=4, column=0, sticky="nsew")
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)
        self._history_list = tk.Listbox(history_frame, height=6, activestyle="none")
        self._history_list.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(history_frame, command=self._history_list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._history_list.configure(yscrollcommand=scrollbar.set)

    def refresh(self) -> None:
        self._all_items = sorted(self._registry.list_glyphs(), key=lambda g: g.index)
        self._apply_filter()
        self._refresh_history()

    def _selected_glyph(self) -> Optional[Glyph]:
        try:
            (idx,) = self._list.curselection()
        except ValueError:
            return None
        if not self._items:
            return None
        if idx < 0 or idx >= len(self._items):
            return None
        return self._items[idx]

    def _update_buttons(self) -> None:
        glyph = self._selected_glyph()
        has_sel = glyph is not None
        state = tk.NORMAL if has_sel else tk.DISABLED
        self._btn_edit.configure(state=state)
        self._btn_remove.configure(state=state)
        self._btn_run.configure(state=state)
        self._update_details(glyph)

    def _update_details(self, glyph: Optional[Glyph]) -> None:
        if not glyph:
            self._details_var.set("Double-click a glyph to run it.")
            return
        summary = glyph.cmd
        if glyph.cwd:
            summary = f"{summary}  (cwd: {glyph.cwd})"
        if glyph.tags:
            summary = f"{summary}\nTags: {', '.join(glyph.tags)}"
        if len(summary) > 140:
            summary = summary[:140] + "…"
        self._details_var.set(summary)

    def _add_glyph(self) -> None:
        dialog = GlyphDialog(
            self.winfo_toplevel(), 
            title="Add Glyph",
            auto_tagger=self._auto_tagger,
            description_generator=self._description_generator,
        )
        result = dialog.show()
        if result is None:
            return
        glyph = self._registry.add_glyph(result)
        self._logger.info("glyph_add_requested", name=glyph.name)
        self.refresh()

    def _edit_glyph(self) -> None:
        glyph = self._selected_glyph()
        if not glyph:
            return
        dialog = GlyphDialog(
            self.winfo_toplevel(), 
            title="Edit Glyph", 
            initial=glyph,
            auto_tagger=self._auto_tagger,
            description_generator=self._description_generator,
        )
        result = dialog.show()
        if result is None:
            return
        updated = self._registry.update_glyph(glyph.id, result)
        if updated is None:
            messagebox.showerror("Edit Glyph", "Failed to update glyph.")
            return
        self._logger.info("glyph_edit_saved", glyph_id=updated.id)
        self.refresh()

    def _remove_glyph(self) -> None:
        glyph = self._selected_glyph()
        if not glyph:
            return
        if not messagebox.askyesno(
            "Remove Glyph", f"Remove '{glyph.name}'?", parent=self.winfo_toplevel()
        ):
            return
        if self._registry.remove_glyph(glyph.id):
            self._logger.info("glyph_removed", glyph_id=glyph.id, name=glyph.name)
        self.refresh()

    def _run_selected(self) -> None:
        glyph = self._selected_glyph()
        if not glyph:
            return
        self._logger.info(
            "run_glyph",
            glyph_id=glyph.id,
            name=glyph.name,
            cwd=str(glyph.cwd or ""),
            cmd=glyph.cmd,
        )

        def _done(res: dict[str, str]) -> None:
            def notify() -> None:
                self._logger.info(
                    "[tool] result",
                    returncode=str(res.get("returncode", "")),
                    stdout=(res.get("stdout", "")[:160] or "").replace("\n", "\\n"),
                    stderr=(res.get("stderr", "")[:160] or "").replace("\n", "\\n"),
                )
                self._history_service.append("glyph", glyph.cmd)
                self._refresh_history()

            self.after(0, notify)

        self._worker.submit(
            self._tools.run_glyph,
            glyph.id,
            description=f"run_glyph:{glyph.name}",
            callback=_done,
        )

    def _import_glyphs(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Import Glyphs",
            filetypes=[("Glyph Registry", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            count = self._registry.import_file(Path(path))
        except Exception as exc:  # pragma: no cover - user feedback
            messagebox.showerror(
                "Import Glyphs",
                f"Failed to import glyphs: {exc}",
                parent=self.winfo_toplevel(),
            )
            return
        messagebox.showinfo(
            "Import Glyphs",
            f"Imported {count} glyph(s).",
            parent=self.winfo_toplevel(),
        )
        self.refresh()

    def _apply_filter(self) -> None:
        query = self._search_var.get().strip().lower()
        tokens = query.split()
        if tokens:
            filtered = []
            for glyph in self._all_items:
                haystack = " ".join(
                    [
                        glyph.name.lower(),
                        glyph.cmd.lower(),
                        " ".join(tag.lower() for tag in glyph.tags),
                    ]
                )
                if all(token in haystack for token in tokens):
                    filtered.append(glyph)
        else:
            filtered = list(self._all_items)
        self._items = filtered
        self._list.delete(0, "end")
        for glyph in self._items:
            tags = f" [{', '.join(glyph.tags)}]" if glyph.tags else ""
            label = f"{glyph.emoji + ' ' if glyph.emoji else ''}{glyph.name}{tags}"
            self._list.insert("end", label)
        self._update_buttons()

    def _refresh_history(self) -> None:
        records = self._history_service.tail()
        self._history_list.delete(0, "end")
        for record in records:
            self._history_list.insert("end", self._format_history(record))

    @staticmethod
    def _format_history(record: CommandRecord) -> str:
        ts = datetime.fromtimestamp(record.timestamp).strftime("%H:%M:%S")
        return f"[{ts}] {record.source}: {record.command}"[:200]


class GlyphDialog(tk.Toplevel):
    """Add/Edit glyph dialog with validation."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        title: str,
        initial: Optional[Glyph] = None,
        auto_tagger=None,
        description_generator=None,
    ) -> None:
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._auto_tagger = auto_tagger
        self._description_generator = description_generator

        self._var_name = tk.StringVar(value=initial.name if initial else "")
        self._var_emoji = tk.StringVar(value=initial.emoji if initial else "")
        self._var_cmd = tk.StringVar(value=initial.cmd if initial else "")
        self._var_cwd = tk.StringVar(value=initial.cwd if initial else "")
        initial_tags = ", ".join(initial.tags) if initial and initial.tags else ""
        self._var_tags = tk.StringVar(value=initial_tags)
        self._result: Optional[GlyphCreate] = None

        frm = ttk.Frame(self, padding=12)
        frm.grid(row=0, column=0, sticky="nsew")
        for i in range(2):
            frm.columnconfigure(i, weight=1)

        ttk.Label(frm, text="Name").grid(row=0, column=0, sticky="w")
        ent_name = ttk.Entry(frm, textvariable=self._var_name, width=40)
        ent_name.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        ttk.Label(frm, text="Emoji (optional)").grid(row=2, column=0, sticky="w")
        ent_emoji = ttk.Entry(frm, textvariable=self._var_emoji)
        ent_emoji.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        ttk.Label(frm, text="Command").grid(row=4, column=0, sticky="w")
        ent_cmd = ttk.Entry(frm, textvariable=self._var_cmd)
        ent_cmd.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        ttk.Label(frm, text="Working directory (optional)").grid(row=6, column=0, sticky="w")
        ent_cwd = ttk.Entry(frm, textvariable=self._var_cwd)
        ent_cwd.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        ttk.Label(frm, text="Tags (comma separated)").grid(row=8, column=0, sticky="w")
        
        # AI-assisted tagging row
        tag_row = ttk.Frame(frm)
        tag_row.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        tag_row.columnconfigure(0, weight=1)
        
        ent_tags = ttk.Entry(tag_row, textvariable=self._var_tags)
        ent_tags.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        
        if self._auto_tagger:
            btn_suggest_tags = ttk.Button(
                tag_row, 
                text="🤖 Suggest", 
                width=12,
                command=self._suggest_tags
            )
            btn_suggest_tags.grid(row=0, column=1, sticky="e")
        
        # AI description hint (if generator available)
        if self._description_generator:
            self._lbl_description = ttk.Label(
                frm, 
                text="💡 Tip: Leave command blank and click Save to auto-generate", 
                foreground="gray",
                font=("TkDefaultFont", 8, "italic")
            )
            self._lbl_description.grid(row=10, column=0, columnspan=2, sticky="w", pady=(0, 8))

        btn_save = ttk.Button(frm, text="Save", command=self._on_save)
        btn_cancel = ttk.Button(frm, text="Cancel", command=self._on_cancel)
        btn_save.grid(row=11, column=0, sticky="e", padx=(0, 8))
        btn_cancel.grid(row=11, column=1, sticky="w")

        self.bind("<Return>", lambda _e: self._on_save())
        self.bind("<Escape>", lambda _e: self._on_cancel())
        ent_name.focus_set()

    def _suggest_tags(self) -> None:
        """Use Gemma to suggest tags based on command."""
        command = self._var_cmd.get().strip()
        name = self._var_name.get().strip()
        
        if not command:
            messagebox.showinfo("Auto-Tag", "Enter a command first.", parent=self)
            return

        try:
            if name:
                suggested = self._auto_tagger.suggest_from_name_and_command(name, command)
            else:
                suggested = self._auto_tagger.suggest_tags(command)
            
            if suggested:
                current = self._var_tags.get().strip()
                if current:
                    combined = f"{current}, {', '.join(suggested)}"
                else:
                    combined = ", ".join(suggested)
                self._var_tags.set(combined)
            else:
                messagebox.showinfo("Auto-Tag", "No tags suggested. Make sure Gemma is running.", parent=self)
        except Exception as exc:
            messagebox.showerror("Auto-Tag", f"Failed: {exc}", parent=self)

    def show(self) -> Optional[GlyphCreate]:
        self.wait_window(self)
        return self._result

    def _on_save(self) -> None:
        name = self._var_name.get().strip()
        cmd = self._var_cmd.get().strip()
        if not name or not cmd:
            messagebox.showerror("Validation", "Name and Command are required.", parent=self)
            return
        emoji = (self._var_emoji.get() or "").strip() or None
        cwd = (self._var_cwd.get() or "").strip() or None
        tags = [tag.strip() for tag in (self._var_tags.get() or "").split(",") if tag.strip()]
        self._result = GlyphCreate(name=name, cmd=cmd, emoji=emoji, cwd=cwd, tags=tags)
        self.destroy()

    def _on_cancel(self) -> None:
        self._result = None
        self.destroy()


class ToolConfirmationDialog(tk.Toplevel):
    """Confirmation dialog for tool operations."""
    
    def __init__(self, master: tk.Misc, tool_name: str, arguments: dict, mode: str = "chat") -> None:
        super().__init__(master)
        self.title("Tool Execution Confirmation")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        
        self.result = None
        
        # Main frame
        frame = ttk.Frame(self, padding=16)
        frame.grid(row=0, column=0, sticky="nsew")
        
        # Warning icon and title
        title_frame = ttk.Frame(frame)
        title_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        
        ttk.Label(
            title_frame, 
            text="⚠️", 
            font=("Segoe UI", 24)
        ).grid(row=0, column=0, padx=(0, 12))
        
        ttk.Label(
            title_frame,
            text=f"Confirm {tool_name.replace('_', ' ').title()} Execution",
            font=("Segoe UI", 12, "bold")
        ).grid(row=0, column=1)
        
        # Mode indicator
        mode_text = "AI Agent" if mode == "agent" else "AI Chat"
        ttk.Label(
            frame,
            text=f"The {mode_text} wants to execute the following operation:",
            font=("Segoe UI", 10)
        ).grid(row=1, column=0, sticky="w", pady=(0, 8))
        
        # Tool details
        details_frame = ttk.LabelFrame(frame, text="Operation Details", padding=12)
        details_frame.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        details_frame.columnconfigure(1, weight=1)
        
        # Format arguments
        row = 0
        for key, value in arguments.items():
            ttk.Label(details_frame, text=f"{key}:", font=("Segoe UI", 9, "bold")).grid(
                row=row, column=0, sticky="nw", padx=(0, 8), pady=2
            )
            
            # Truncate long values
            display_value = str(value)
            if len(display_value) > 200:
                display_value = display_value[:197] + "..."
            
            value_label = ttk.Label(details_frame, text=display_value, wraplength=400)
            value_label.grid(row=row, column=1, sticky="w", pady=2)
            row += 1
        
        # Safety notice
        safety_frame = ttk.Frame(frame)
        safety_frame.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        
        ttk.Label(
            safety_frame,
            text="ℹ️ This operation may modify your system or files.",
            foreground="blue",
            font=("Segoe UI", 9)
        ).grid(row=0, column=0, sticky="w")
        
        # Remember choice checkbox
        self.remember_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Don't ask again for this session",
            variable=self.remember_var
        ).grid(row=4, column=0, sticky="w", pady=(0, 12))
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=5, column=0, sticky="e")
        
        ttk.Button(
            button_frame,
            text="Allow",
            command=self._on_allow
        ).grid(row=0, column=0, padx=(0, 8))
        
        ttk.Button(
            button_frame,
            text="Deny",
            command=self._on_deny
        ).grid(row=0, column=1, padx=(0, 8))
        
        ttk.Button(
            button_frame,
            text="Always Deny",
            command=self._on_always_deny
        ).grid(row=0, column=2)
        
        # Keyboard shortcuts
        self.bind("<Return>", lambda e: self._on_allow())
        self.bind("<Escape>", lambda e: self._on_deny())
        
    def _on_allow(self) -> None:
        self.result = ("allow", self.remember_var.get())
        self.destroy()
    
    def _on_deny(self) -> None:
        self.result = ("deny", self.remember_var.get())
        self.destroy()
    
    def _on_always_deny(self) -> None:
        self.result = ("always_deny", True)
        self.destroy()
    
    def show(self) -> tuple[str, bool]:
        """Show dialog and return (action, remember) tuple."""
        self.wait_window(self)
        return self.result or ("deny", False)


class AIPanel(ttk.Frame):
    """Unified AI Chat and Agent panel with mode toggle."""

    TRANSCRIPT_CHAR_LIMIT = 1200

    def __init__(
        self,
        master: tk.Misc,
        worker: Worker,
        llm_client: LLMClient,
        tools: ToolsBridge,
        history: ChatHistory,
        command_history: CommandHistory,
        logger: Logger,
        *,
        max_steps: int = 6,
        settings_service: Optional['SettingsService'] = None,
    ) -> None:
        super().__init__(master, padding=8)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._worker = worker
        self._llm = llm_client
        self._tools = tools
        self._history = history
        self._command_history = command_history
        self._agent_prompt = DEFAULT_AGENT_PROMPT
        self._logger = logger
        self._messages: list[ChatMessage] = []
        self._pending = False
        self._max_steps = max_steps
        self._mode = tk.StringVar(value="chat")
        self._cancel_flag = False
        self._current_job = None
        self._settings_service = settings_service

        # Mode selector at top
        mode_frame = ttk.Frame(self)
        mode_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Radiobutton(mode_frame, text="💬 Chat", variable=self._mode, value="chat", command=self._on_mode_change).pack(side="left", padx=4)
        ttk.Radiobutton(mode_frame, text="🤖 Agent", variable=self._mode, value="agent", command=self._on_mode_change).pack(side="left", padx=4)
        
        # Mode indicator label with color coding and interactivity
        self._mode_indicator = tk.Label(
            mode_frame, 
            text="", 
            font=("Segoe UI", 9, "bold"),
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=2,
            cursor="hand2"
        )
        self._mode_indicator.pack(side="left", padx=(12, 0))
        self._mode_indicator.bind("<Button-1>", self._on_mode_indicator_click)
        self._mode_indicator.bind("<Enter>", self._on_mode_indicator_hover)
        self._mode_indicator.bind("<Leave>", self._on_mode_indicator_leave)
        self._mode_indicator_tooltip_window = None
        self._update_mode_indicator()
        
        # Transcript/log (shared between both modes)
        transcript_frame = ttk.Frame(self)
        transcript_frame.grid(row=1, column=0, sticky="nsew")
        transcript_frame.columnconfigure(0, weight=1)
        transcript_frame.rowconfigure(0, weight=1)

        self._transcript = tk.Text(
            transcript_frame,
            wrap="word",
            state="disabled",
            height=20,
        )
        transcript_scroll = ttk.Scrollbar(transcript_frame, command=self._transcript.yview)
        self._transcript.configure(yscrollcommand=transcript_scroll.set)
        self._transcript.grid(row=0, column=0, sticky="nsew")
        transcript_scroll.grid(row=0, column=1, sticky="ns")

        # Input frame (switches between chat and agent modes)
        input_frame = ttk.Frame(self)
        input_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        input_frame.columnconfigure(0, weight=1)

        self._input = tk.Text(input_frame, height=4, wrap="word")
        self._input.grid(row=0, column=0, sticky="ew")
        self._input.bind("<Control-Return>", self._on_send_or_run)

        buttons = ttk.Frame(input_frame)
        buttons.grid(row=0, column=1, padx=(8, 0), sticky="ns")
        self._action_button = ttk.Button(buttons, text="Send", command=self._on_send_or_run)
        self._stop_button = ttk.Button(buttons, text="Stop", command=self._stop_operation, state="disabled")
        clear_button = ttk.Button(buttons, text="Clear", command=self._clear_transcript)
        self._action_button.grid(row=0, column=0, sticky="ew")
        self._stop_button.grid(row=1, column=0, pady=(4, 0), sticky="ew")
        clear_button.grid(row=2, column=0, pady=(4, 0), sticky="ew")
        
    def _on_mode_change(self) -> None:
        """Update UI when mode changes."""
        mode = self._mode.get()
        # Both modes now use the same interface
        self._action_button.configure(text="Send")
        self._update_mode_indicator()
    
    def _update_mode_indicator(self) -> None:
        """Update the mode indicator label with color coding."""
        mode = self._mode.get()
        if mode == "chat":
            self._mode_indicator.configure(
                text="🛡️ Safe Mode",
                background="#d4edda",  # Light green
                foreground="#155724"   # Dark green
            )
            # Create tooltip text
            tooltip_text = (
                "Chat Mode (Safe)\n"
                "• Requires confirmation for dangerous commands\n"
                "• File operations restricted\n"
                "• Output limits enforced\n"
                "• Click for more info"
            )
        else:
            self._mode_indicator.configure(
                text="⚡ Agent Mode",
                background="#fff3cd",  # Light yellow
                foreground="#856404"   # Dark yellow/brown
            )
            tooltip_text = (
                "Agent Mode (Autonomous)\n"
                "• Tools execute without confirmation\n"
                "• Use with caution\n"
                "• Monitor tool execution carefully\n"
                "• Click for more info"
            )
        
        # Update tooltip (store for click handler)
        self._mode_indicator_tooltip = tooltip_text

    def _on_mode_indicator_click(self, event: tk.Event) -> None:
        """Show detailed mode information when indicator is clicked."""
        mode = self._mode.get()
        
        if mode == "chat":
            title = "Chat Mode - Safe Operation"
            message = (
                "You are in CHAT MODE (Safe)\n\n"
                "Safety Features Active:\n"
                "• Dangerous shell commands require confirmation\n"
                "• File write operations are restricted\n"
                "• Tool output is truncated to prevent token bloat\n"
                "• Session-based approval caching reduces dialogs\n\n"
                "Best for:\n"
                "• Interactive conversations\n"
                "• Exploring new tools\n"
                "• Learning what the assistant can do\n"
                "• When you want control over tool execution\n\n"
                "Switch to Agent Mode for autonomous operation."
            )
        else:
            title = "Agent Mode - Autonomous Operation"
            message = (
                "You are in AGENT MODE (Autonomous)\n\n"
                "⚠️ Warning: Reduced Safety Checks\n"
                "• Tools execute WITHOUT confirmation dialogs\n"
                "• Commands run with minimal intervention\n"
                "• You are responsible for monitoring execution\n\n"
                "Safety features still active:\n"
                "• Output truncation (configurable in settings)\n"
                "• Basic validation of file operations\n"
                "• Timeout limits enforced\n\n"
                "Best for:\n"
                "• Autonomous task execution\n"
                "• Batch operations\n"
                "• When you trust the assistant's judgment\n\n"
                "⚠️ Use with caution! Switch to Chat Mode for safer operation."
            )
        
        # Show modal dialog with mode information
        from tkinter import messagebox
        messagebox.showinfo(title, message)

    def _on_mode_indicator_hover(self, event: tk.Event) -> None:
        """Show tooltip when hovering over mode indicator."""
        if hasattr(self, '_mode_indicator_tooltip'):
            # Create tooltip window
            self._mode_indicator_tooltip_window = tk.Toplevel(self._mode_indicator)
            self._mode_indicator_tooltip_window.wm_overrideredirect(True)
            
            # Position tooltip near the cursor
            x = event.x_root + 10
            y = event.y_root + 10
            self._mode_indicator_tooltip_window.wm_geometry(f"+{x}+{y}")
            
            # Create tooltip label
            label = tk.Label(
                self._mode_indicator_tooltip_window,
                text=self._mode_indicator_tooltip,
                justify="left",
                background="#ffffe0",
                foreground="black",
                relief="solid",
                borderwidth=1,
                font=("Segoe UI", 9),
                padx=8,
                pady=4
            )
            label.pack()

    def _on_mode_indicator_leave(self, event: tk.Event) -> None:
        """Hide tooltip when leaving mode indicator."""
        if self._mode_indicator_tooltip_window:
            self._mode_indicator_tooltip_window.destroy()
            self._mode_indicator_tooltip_window = None

    # ------------------------------------------------------------------
    def _append_transcript(self, message: ChatMessage) -> None:
        prefix_map = {
            "user": "You",
            "assistant": "Assistant",
            "tool": f"[tool:{message.name}]" if message.name else "[tool]",
        }
        prefix = prefix_map.get(message.role, message.role.title())
        content = self._truncate(message.content or "", self.TRANSCRIPT_CHAR_LIMIT)
        self._transcript.configure(state="normal")
        self._transcript.insert("end", f"{prefix}: {content}\n")
        self._transcript.configure(state="disabled")
        self._transcript.see("end")

    def _stream_message(self, message: ChatMessage) -> None:
        content = message.content or ""
        if not content:
            self._append_transcript(message)
            return

        chunks = content.split(" ")

        def emit(index: int) -> None:
            if index >= len(chunks):
                self._transcript.configure(state="normal")
                self._transcript.insert("end", "\n")
                self._transcript.configure(state="disabled")
                self._transcript.see("end")
                return
            piece = chunks[index]
            if index < len(chunks) - 1:
                piece += " "
            self._transcript.configure(state="normal")
            self._transcript.insert("end", piece)
            self._transcript.configure(state="disabled")
            self._transcript.see("end")
            self.after(40, lambda: emit(index + 1))

        self._transcript.configure(state="normal")
        self._transcript.insert("end", "Assistant: ")
        self._transcript.configure(state="disabled")
        emit(0)

    def _append_info(self, text: str) -> None:
        self._transcript.configure(state="normal")
        self._transcript.insert("end", f"[info] {text}\n")
        self._transcript.configure(state="disabled")
        self._transcript.see("end")

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[:limit] + "… (truncated)"

    def _set_pending(self, pending: bool) -> None:
        self._pending = pending
        if pending:
            self._action_button.configure(state=tk.DISABLED)
            self._stop_button.configure(state=tk.NORMAL)
            self._cancel_flag = False
        else:
            self._action_button.configure(state=tk.NORMAL)
            self._stop_button.configure(state=tk.DISABLED)
            self._current_job = None
    
    def _stop_operation(self) -> None:
        """Cancel the current operation."""
        self._cancel_flag = True
        self._append_info("🛑 Stopping operation...")
        if self._current_job:
            # Note: Worker doesn't support cancellation yet, this is a flag for the loop
            pass

    def _write_history(self, message: ChatMessage) -> None:
        meta: dict[str, str] = {}
        if message.name:
            meta["name"] = message.name
        if message.tool_call_id:
            meta["tool_call_id"] = message.tool_call_id
        mode = self._mode.get()
        self._history.append(message.role, message.content or "", mode=mode, **meta)

    def _clear_transcript(self) -> None:
        """Clear the transcript/log."""
        if self._pending:
            return
        self._messages.clear()
        self._transcript.configure(state="normal")
        self._transcript.delete("1.0", "end")
        self._transcript.configure(state="disabled")
    
    def _on_send_or_run(self, *_args: object) -> None:
        """Send message in either chat or agent mode (both conversational now)."""
        if self._pending:
            return
        content = self._input.get("1.0", "end").strip()
        if not content:
            return
        self._input.delete("1.0", "end")
        
        mode = self._mode.get()
        
        # Add user message to conversation
        user_msg = ChatMessage(role="user", content=content)
        self._messages.append(user_msg)
        self._append_transcript(user_msg)
        self._write_history(user_msg)
        self._logger.info(f"{mode}_send", length=str(len(content)))
        self._set_pending(True)
        baseline = len(self._messages)
        tools_schema = self._tools.tool_descriptions()
        
        # Prepare for streaming display
        self._transcript.configure(state="normal")
        self._transcript.insert("end", "Assistant: ")
        self._transcript.configure(state="disabled")
        self._streaming_buffer = ""

        def job() -> dict[str, object]:
            # Build conversation with system prompt for agent mode
            conversation = []
            if mode == "agent" and self._messages:
                # Inject agent system prompt at the beginning
                conversation.append(ChatMessage(role="system", content=self._agent_prompt))
                # Add all messages except the system prompt
                conversation.extend([
                    ChatMessage.from_dict(m.to_dict()) 
                    for m in self._messages 
                    if m.role != "system"
                ])
            else:
                conversation = [ChatMessage.from_dict(m.to_dict()) for m in self._messages]
            
            try:
                loop_result = self._chat_loop_streaming(conversation, tools_schema, mode)
                loop_result["conversation"] = [m.to_dict() for m in conversation]
                loop_result["ok"] = True
                return loop_result
            except Exception as exc:  # noqa: BLE001
                self._logger.error(
                    f"{mode}_error",
                    error=f"{type(exc).__name__}: {exc}",
                )
                return {
                    "ok": False,
                    "error": exc,
                    "conversation": [m.to_dict() for m in conversation],
                }

        def callback(result: dict[str, object]) -> None:
            def apply() -> None:
                self._set_pending(False)
                # Add newline after streaming content
                self._transcript.configure(state="normal")
                self._transcript.insert("end", "\n")
                self._transcript.configure(state="disabled")
                
                conversation_payload = result.get("conversation")
                if isinstance(conversation_payload, list):
                    conversation = [
                        ChatMessage.from_dict(payload)
                        for payload in conversation_payload
                        if isinstance(payload, dict)
                    ]
                    # Extract only the new messages (skip system prompt if present)
                    new_messages = []
                    for msg in conversation[baseline:]:
                        if msg.role != "system":
                            new_messages.append(msg)
                    
                    # Update main message list
                    self._messages.extend(new_messages)
                    
                    for idx, msg in enumerate(new_messages):
                        self._write_history(msg)
                        # Skip displaying assistant message since we already streamed it
                        if msg.role == "assistant" and idx == len(new_messages) - 1:
                            continue
                        # Display tool messages
                        if msg.role != "assistant":
                            self._append_transcript(msg)
                    usage = result.get("usage")
                    if isinstance(usage, dict):
                        prompt_tokens = usage.get("prompt_tokens")
                        completion_tokens = usage.get("completion_tokens")
                        total_tokens = usage.get("total_tokens")
                        self._append_info(
                            f"usage: prompt={prompt_tokens} completion={completion_tokens} total={total_tokens}"
                        )
                if not result.get("ok"):
                    messagebox.showerror(
                        f"{mode.title()} Error",
                        f"Failed to complete {mode}: {result.get('error')}",
                        parent=self.winfo_toplevel(),
                    )

            self.after(0, apply)

        self._worker.submit(job, description=f"{mode}_send", callback=callback)

    def _append_streaming_token(self, token: str) -> None:
        """Append a token to the transcript in real-time (called from worker thread)."""
        def update():
            self._transcript.configure(state="normal")
            self._transcript.insert("end", token)
            self._transcript.configure(state="disabled")
            self._transcript.see("end")
        self.after(0, update)

    def _chat_loop_streaming(
        self,
        conversation: list[ChatMessage],
        tools_schema: list[dict[str, object]],
        mode: str = "chat",
    ) -> dict[str, object]:
        """Chat/agent loop with streaming support."""
        # Get truncation settings
        truncation_enabled = True
        truncation_max_bytes = 8000
        if self._settings_service:
            settings = self._settings_service.get()
            truncation_enabled = settings.context_truncation_enabled
            truncation_max_bytes = settings.tool_output_max_bytes
        
        return _run_tool_loop_streaming(
            self._llm,
            self._tools,
            self._logger,
            conversation,
            tools_schema,
            self._max_steps,
            command_history=self._command_history,
            history_source=mode,
            on_token=self._append_streaming_token,
            truncation_max_bytes=truncation_max_bytes,
            truncation_enabled=truncation_enabled,
        )

    # ------------------------------------------------------------------
    def _chat_loop(
        self,
        conversation: list[ChatMessage],
        tools_schema: list[dict[str, object]],
    ) -> dict[str, object]:
        # Get truncation settings
        truncation_enabled = True
        truncation_max_bytes = 8000
        if self._settings_service:
            settings = self._settings_service.get()
            truncation_enabled = settings.context_truncation_enabled
            truncation_max_bytes = settings.tool_output_max_bytes
        
        return _run_tool_loop(
            self._llm,
            self._tools,
            self._logger,
            conversation,
            tools_schema,
            self._max_steps,
            command_history=self._command_history,
            history_source="chat",
            truncation_max_bytes=truncation_max_bytes,
            truncation_enabled=truncation_enabled,
        )

    def set_prompt(self, prompt: Optional[str]) -> None:
        """Set the agent system prompt."""
        self._agent_prompt = prompt or DEFAULT_AGENT_PROMPT


# Keep ChatPanel as an alias for backward compatibility
ChatPanel = AIPanel


def _run_tool_loop_streaming(
    llm_client: LLMClient,
    tools: ToolsBridge,
    logger: Logger,
    conversation: list[ChatMessage],
    tools_schema: list[dict[str, object]],
    max_steps: int,
    *,
    command_history: CommandHistory | None = None,
    history_source: str = "",
    on_token: Optional[callable] = None,
    truncation_max_bytes: int = 8000,
    truncation_enabled: bool = True,
) -> dict[str, object]:
    """Tool loop with streaming support for assistant responses."""
    # Set the mode on tools bridge for proper safety handling
    tools.set_mode(history_source or "chat")
    
    for step in range(1, max_steps + 1):
        logger.info("chat_step", step=str(step), messages=str(len(conversation)))
        
        # Use streaming if on_token callback is provided
        if on_token:
            response = llm_client.chat_stream(
                conversation, 
                tools=tools_schema,
                on_token=on_token,
            )
        else:
            response = llm_client.chat(conversation, tools=tools_schema)
            
        choice = _extract_first_choice(response)
        if choice is None:
            raise RuntimeError("Model returned no choices")
        message_payload = choice.get("message") or {}
        tool_calls = message_payload.get("tool_calls") or []
        if tool_calls:
            for call in tool_calls:
                fn_info = call.get("function", {})
                name = fn_info.get("name")
                arguments = fn_info.get("arguments", "{}")
                if not isinstance(name, str):
                    continue
                arguments_text = str(arguments)
                preview = arguments_text[:200] + "…" if len(arguments_text) > 200 else arguments_text
                logger.info(
                    "chat_tool_invocation",
                    name=name,
                    arguments=preview,
                )
                try:
                    result = tools.execute_tool(name, arguments)
                    content = json.dumps(result, ensure_ascii=False)
                    # Truncate tool results to prevent token bloat
                    if truncation_enabled:
                        content = _truncate_tool_result(content, truncation_max_bytes)
                except Exception as exc:  # noqa: BLE001
                    content = json.dumps({"error": str(exc)}, ensure_ascii=False)
                    logger.error(
                        "chat_tool_error",
                        name=name,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                tool_msg = ChatMessage(
                    role="tool",
                    content=content,
                    name=name,
                    tool_call_id=call.get("id"),
                )
                conversation.append(tool_msg)
                if command_history is not None:
                    try:
                        params = json.loads(arguments) if isinstance(arguments, str) else (arguments or {})
                    except json.JSONDecodeError:
                        params = {}
                    command_text = ""
                    if name == "run_shell":
                        command_text = str(params.get("command", ""))
                    elif name == "run_glyph":
                        identifier = params.get("identifier", "")
                        command_text = f"glyph:{identifier}" if identifier else "glyph"
                    if command_text:
                        command_history.append(history_source or name, command_text)
            continue

        content = message_payload.get("content") or ""
        assistant_msg = ChatMessage(role="assistant", content=content)
        conversation.append(assistant_msg)
        return {"reply": content, "usage": response.get("usage")}

    raise RuntimeError("Model exceeded tool-call step limit")


def _run_tool_loop(
    llm_client: LLMClient,
    tools: ToolsBridge,
    logger: Logger,
    conversation: list[ChatMessage],
    tools_schema: list[dict[str, object]],
    max_steps: int,
    *,
    command_history: CommandHistory | None = None,
    history_source: str = "",
    truncation_max_bytes: int = 8000,
    truncation_enabled: bool = True,
) -> dict[str, object]:
    # Set the mode on tools bridge for proper safety handling
    tools.set_mode(history_source or "chat")
    
    for step in range(1, max_steps + 1):
        logger.info("chat_step", step=str(step), messages=str(len(conversation)))
        response = llm_client.chat(conversation, tools=tools_schema)
        choice = _extract_first_choice(response)
        if choice is None:
            raise RuntimeError("Model returned no choices")
        message_payload = choice.get("message") or {}
        tool_calls = message_payload.get("tool_calls") or []
        if tool_calls:
            for call in tool_calls:
                fn_info = call.get("function", {})
                name = fn_info.get("name")
                arguments = fn_info.get("arguments", "{}")
                if not isinstance(name, str):
                    continue
                arguments_text = str(arguments)
                preview = arguments_text[:200] + "…" if len(arguments_text) > 200 else arguments_text
                logger.info(
                    "chat_tool_invocation",
                    name=name,
                    arguments=preview,
                )
                try:
                    result = tools.execute_tool(name, arguments)
                    content = json.dumps(result, ensure_ascii=False)
                    # Truncate tool results to prevent token bloat
                    if truncation_enabled:
                        content = _truncate_tool_result(content, truncation_max_bytes)
                except Exception as exc:  # noqa: BLE001
                    content = json.dumps({"error": str(exc)}, ensure_ascii=False)
                    logger.error(
                        "chat_tool_error",
                        name=name,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                tool_msg = ChatMessage(
                    role="tool",
                    content=content,
                    name=name,
                    tool_call_id=call.get("id"),
                )
                conversation.append(tool_msg)
                if command_history is not None:
                    try:
                        params = json.loads(arguments) if isinstance(arguments, str) else (arguments or {})
                    except json.JSONDecodeError:
                        params = {}
                    command_text = ""
                    if name == "run_shell":
                        command_text = str(params.get("command", ""))
                    elif name == "run_glyph":
                        identifier = params.get("identifier", "")
                        command_text = f"glyph:{identifier}" if identifier else "glyph"
                    if command_text:
                        command_history.append(history_source or name, command_text)
            continue

        content = message_payload.get("content") or ""
        assistant_msg = ChatMessage(role="assistant", content=content)
        conversation.append(assistant_msg)
        return {"reply": content, "usage": response.get("usage")}

    raise RuntimeError("Model exceeded tool-call step limit")


def _extract_first_choice(payload: dict[str, object]) -> dict[str, object] | None:
    choices = payload.get("choices") if isinstance(payload, dict) else None
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            return first
    return None


def _truncate_tool_result(content: str, max_bytes: int = 8000) -> str:
    """Truncate tool result content to prevent token bloat in conversation.
    
    Args:
        content: The tool result JSON string
        max_bytes: Maximum size in bytes (default 8KB, ~2000 tokens)
    
    Returns:
        Truncated content if necessary, with truncation marker
    """
    content_bytes = content.encode('utf-8', errors='ignore')
    if len(content_bytes) <= max_bytes:
        return content
    
    # Try to parse JSON and truncate intelligently
    try:
        data = json.loads(content)
        # If it has stdout/stderr/content/data fields, truncate those
        if isinstance(data, dict):
            truncated = False
            for key in ['stdout', 'stderr', 'content', 'data', 'output']:
                if key in data and isinstance(data[key], str):
                    original_len = len(data[key])
                    # Truncate if this field is large
                    if original_len > 1000:  # Truncate any field over 1KB
                        data[key] = data[key][:max_bytes // 2] + f"\n\n[... truncated {original_len - max_bytes // 2} chars for token efficiency]"
                        truncated = True
            
            # Re-encode and check total size
            result = json.dumps(data, ensure_ascii=False)
            if len(result.encode('utf-8')) <= max_bytes or truncated:
                return result
    except (json.JSONDecodeError, Exception):
        pass
    
    # Fallback: simple byte truncation
    truncated = content_bytes[:max_bytes].decode('utf-8', errors='ignore')
    return truncated + "\n\n[... truncated for token efficiency]"


class CombinedTerminalAIPanel(ttk.Frame):
    """Combined Terminal and AI Chat panel with split view (VS Code style)."""
    
    def __init__(
        self,
        master: tk.Misc,
        worker: Worker,
        llm_client: LLMClient,
        tools: ToolsBridge,
        chat_history: ChatHistory,
        command_history: CommandHistory,
        logger: Logger,
        *,
        session_summarizer=None,
        settings_service: Optional['SettingsService'] = None,
    ) -> None:
        super().__init__(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        # Create a PanedWindow for resizable split (can collapse terminal completely)
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.grid(row=0, column=0, sticky="nsew")
        
        # Left side: Terminal
        terminal_frame = ttk.Frame(paned, padding=4)
        terminal_frame.columnconfigure(0, weight=1)
        terminal_frame.rowconfigure(0, weight=1)
        
        self.terminal_panel = TerminalPanel(
            terminal_frame,
            tools,
            worker,
            logger,
            command_history,
            session_summarizer=session_summarizer,
            llm_client=llm_client,
        )
        self.terminal_panel.grid(row=0, column=0, sticky="nsew")
        
        # Right side: AI Chat
        ai_frame = ttk.Frame(paned, padding=4)
        ai_frame.columnconfigure(0, weight=1)
        ai_frame.rowconfigure(0, weight=1)
        
        self.ai_panel = AIPanel(
            ai_frame,
            worker,
            llm_client,
            tools,
            chat_history,
            command_history,
            logger,
            settings_service=settings_service,
        )
        self.ai_panel.grid(row=0, column=0, sticky="nsew")
        
        # Add frames to paned window
        # Terminal can collapse to 0 width, AI chat always visible
        paned.add(terminal_frame, weight=1)
        paned.add(ai_frame, weight=1)
        
        # Configure the sash to allow complete collapse of terminal panel
        # This allows dragging the divider all the way to the left
        self._paned = paned
    
    def set_prompt(self, prompt: Optional[str]) -> None:
        """Set the agent system prompt on the AI panel."""
        self.ai_panel.set_prompt(prompt)


class Application:
    """Main application wiring."""

    def __init__(self, paths: AppPaths | None = None) -> None:
        self.paths = paths or ensure_app_paths()
        self.root = tk.Tk()
        self.root.title("GlyphX")
        self.root.geometry("900x600")

        self.logger = Logger(self.paths.logs_dir / "app.log")
        self.worker = Worker(self.logger)
        self.registry = RegistryService(self.paths.registry_path, self.logger)
        self.settings = SettingsService(self.paths.settings_path, self.logger)
        
        # Initialize tools with safety configuration
        from .infra.safety import SafetyConfig
        self.safety_config = SafetyConfig(
            enabled=True,
            require_confirmation=True,
        )
        self.tools = ToolsBridge(
            self.registry, 
            self.logger, 
            default_shell_timeout=self.settings.get().shell_timeout,
            safety_config=self.safety_config,
            confirmation_callback=self._request_tool_confirmation,
        )
        self.export_service = ExportService(self.logger)
        self.llm_client = LLMClient(self.settings, self.logger)
        self.chat_history = ChatHistory(self.paths.chat_history_path)
        self.command_history = CommandHistory(self.paths.command_history_path)
        self.crash_reporter = CrashReporter(self.paths.logs_dir / "crash.jsonl", self.logger)
        self.crash_reporter.install()
        self.update_checker = UpdateChecker("0.1.0", self.logger)

        # Initialize Gemma background worker services
        self._init_gemma_services()

        self._setup_ui()
        self._wire_logger()
        self.worker.start()
        self.update_checker.schedule(self.worker, delay=5.0)
        self._bootstrap_worker()
    
    def _init_gemma_services(self) -> None:
        """Initialize Gemma-powered background services if enabled."""
        cfg = self.settings.get()
        
        if cfg.gemma_enabled:
            try:
                self.auto_tagger = AutoTagger(cfg.gemma_base_url, cfg.gemma_model)
                self.description_generator = DescriptionGenerator(cfg.gemma_base_url, cfg.gemma_model)
                self.session_summarizer = SessionSummarizer(cfg.gemma_base_url, cfg.gemma_model)
                self.intent_parser = IntentParser(cfg.gemma_base_url, cfg.gemma_model)
                self.classifier = CommandClassifier(cfg.gemma_base_url, cfg.gemma_model)
                self.logger.info("gemma_services_enabled", model=cfg.gemma_model)
            except Exception as exc:
                self.logger.warning("gemma_services_failed", error=str(exc))
                self.auto_tagger = None
                self.description_generator = None
                self.session_summarizer = None
                self.intent_parser = None
                self.classifier = None
        else:
            self.auto_tagger = None
            self.description_generator = None
            self.session_summarizer = None
            self.intent_parser = None
            self.classifier = None

    def run(self) -> None:
        self.root.mainloop()

    # Internal -------------------------------------------------------------
    def _setup_ui(self) -> None:
        self.root.option_add("*Font", ("Segoe UI", 11))
        
        # Main container with sidebar
        main_container = ttk.Frame(self.root)
        main_container.pack(fill="both", expand=True)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(0, weight=1)
        
        # Sidebar navigation
        self.sidebar = SidebarPanel(main_container, self._on_sidebar_change)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 1))
        
        # Content area with all panels
        self.content_frame = ttk.Frame(main_container)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(0, weight=1)
        
        # Create all panels (hidden initially)
        self._panels: dict[str, tk.Widget] = {}
        
        # File panel (placeholder for now)
        file_panel = ttk.Frame(self.content_frame, padding=20)
        file_label = ttk.Label(file_panel, text="📁 File Operations", font=("Segoe UI", 16, "bold"))
        file_label.pack(pady=20)
        ttk.Button(file_panel, text="Import Glyphs…", command=self._import_glyphs, width=30).pack(pady=5)
        ttk.Button(file_panel, text="Export Glyphs…", command=self._export_glyphs, width=30).pack(pady=5)
        self._panels["file"] = file_panel
        
        # Glyphs panel
        self.glyphs_panel = GlyphsPanel(
            self.content_frame, 
            self.registry, 
            self.worker, 
            self.tools, 
            self.logger, 
            self.command_history,
            auto_tagger=self.auto_tagger,
            description_generator=self.description_generator,
        )
        self._panels["glyphs"] = self.glyphs_panel
        
        # Combined Terminal & AI Chat panel (VS Code style split view)
        self.combined_panel = CombinedTerminalAIPanel(
            self.content_frame,
            self.worker,
            self.llm_client,
            self.tools,
            self.chat_history,
            self.command_history,
            self.logger,
            session_summarizer=self.session_summarizer,
            settings_service=self.settings,
        )
        self.combined_panel.set_prompt(self._current_agent_prompt())
        self._panels["terminal"] = self.combined_panel
        
        # Keep references for backward compatibility
        self.terminal_panel = self.combined_panel.terminal_panel
        self.chat_panel = self.combined_panel.ai_panel
        
        # Console panel
        self.console_panel = ConsolePanel(self.content_frame)
        self._panels["console"] = self.console_panel
        
        # Settings panel (placeholder for now)
        settings_panel = ttk.Frame(self.content_frame, padding=20)
        settings_label = ttk.Label(settings_panel, text="⚙️ Settings", font=("Segoe UI", 16, "bold"))
        settings_label.pack(pady=20)
        ttk.Button(settings_panel, text="Open Settings Dialog", command=self._open_settings, width=30).pack(pady=5)
        self._panels["settings"] = settings_panel
        
        # Archive panel (placeholder for future implementation)
        archive_panel = ttk.Frame(self.content_frame, padding=20)
        archive_label = ttk.Label(archive_panel, text="📦 Data Archive", font=("Segoe UI", 16, "bold"))
        archive_label.pack(pady=20)
        archive_info = ttk.Label(archive_panel, text="Data archiving features coming soon...", foreground="gray")
        archive_info.pack(pady=10)
        self._panels["archive"] = archive_panel
        
        # Show glyphs panel by default
        self._show_panel("glyphs")
        self.sidebar.set_section("glyphs")
        
        self._build_menu()
        # populate list
        self.glyphs_panel.refresh()
    
    def _on_sidebar_change(self, section_id: str) -> None:
        """Handle sidebar section changes."""
        self._show_panel(section_id)
    
    def _show_panel(self, panel_id: str) -> None:
        """Show the specified panel and hide others."""
        # Hide all panels
        for panel in self._panels.values():
            panel.grid_forget()
        
        # Show the selected panel
        if panel_id in self._panels:
            self._panels[panel_id].grid(row=0, column=0, sticky="nsew")

    def _current_agent_prompt(self) -> str:
        settings = self.settings.get()
        return settings.agent_prompt or DEFAULT_AGENT_PROMPT

    def _on_settings_changed(self) -> None:
        current = self.settings.get()
        self.tools.set_shell_timeout(current.shell_timeout)
        self.combined_panel.set_prompt(self._current_agent_prompt())

    def _build_menu(self) -> None:
        menu = tk.Menu(self.root)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="Import Glyphs…", command=self._import_glyphs)
        file_menu.add_command(label="Export…", command=self._export_glyphs)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.root.quit, accelerator="Ctrl+Q")
        menu.add_cascade(label="File", menu=file_menu)

        config_menu = tk.Menu(menu, tearoff=False)
        config_menu.add_command(
            label="Settings…",
            command=self._open_settings,
            accelerator="Ctrl+,",
        )
        menu.add_cascade(label="Config", menu=config_menu)

        self.root.config(menu=menu)
        self.root.bind_all("<Control-q>", lambda *_: self.root.quit())
        self.root.bind_all("<Control-Shift-,>", lambda *_: self._open_settings())
        self.root.bind_all("<Control-,>", lambda *_: self._open_settings())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _wire_logger(self) -> None:
        def sink(event: LogEvent) -> None:
            self.root.after(0, lambda: self.console_panel.append(event))

        self.logger.set_sink(sink)

    def _bootstrap_worker(self) -> None:
        def greet() -> None:
            self.logger.info("hello from worker")

        self.worker.submit(greet, description="bootstrap_log")

    def _on_close(self) -> None:
        try:
            self.worker.shutdown()
        finally:
            self.root.destroy()
    
    def _request_tool_confirmation(self, tool_name: str, arguments: dict, mode: str) -> tuple[str, bool]:
        """Request user confirmation for tool execution (runs on main thread)."""
        dialog = ToolConfirmationDialog(self.root, tool_name, arguments, mode)
        return dialog.show()

    def _import_glyphs(self) -> None:
        """Import glyphs from JSON file via the main menu."""
        self.glyphs_panel._import_glyphs()

    def _export_glyphs(self) -> None:
        glyphs = self.registry.list_glyphs()
        if not glyphs:
            messagebox.showinfo("Export Glyphs", "No glyphs available to export.", parent=self.root)
            return

        folder = filedialog.askdirectory(parent=self.root, title="Export Glyph Launchers")
        if not folder:
            return

        destination = Path(folder)
        self.logger.info(
            "export_selected",
            destination=str(destination),
            glyphs=str(len(glyphs)),
        )

        def done(summary: ExportSummary) -> None:
            def notify() -> None:
                files = "\n".join(str(path.name) for path in summary.created) or "(none)"
                messagebox.showinfo(
                    "Export Complete",
                    f"Exported {len(summary.created)} file(s) to:\n{destination}\n\n{files}",
                    parent=self.root,
                )

            self.root.after(0, notify)

        self.worker.submit(
            self.export_service.export,
            list(glyphs),
            destination,
            description="export_glyphs",
            callback=done,
        )

    def _open_settings(self, *_args: object) -> None:
        dialog = SettingsDialog(self.root, self.settings)
        dialog.show()
        self._on_settings_changed()


class SettingsDialog(tk.Toplevel):
    """Modal dialog to configure API settings."""

    def __init__(self, master: tk.Misc, service: SettingsService) -> None:
        super().__init__(master)
        self.title("Settings")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self._service = service
        self._settings = service.get()

        self._var_api_key = tk.StringVar(value=self._settings.api_key or "")
        self._var_model = tk.StringVar(value=self._settings.model)
        self._var_base_url = tk.StringVar(value=self._settings.base_url)
        self._var_llm_timeout = tk.StringVar(value=str(self._settings.llm_timeout))
        self._var_rate_limit = tk.StringVar(value="" if self._settings.llm_rate_limit_per_minute is None else str(self._settings.llm_rate_limit_per_minute))
        self._var_shell_timeout = tk.StringVar(value=str(self._settings.shell_timeout))
        
        # Gemma settings
        self._var_gemma_enabled = tk.BooleanVar(value=self._settings.gemma_enabled)
        self._var_gemma_base_url = tk.StringVar(value=self._settings.gemma_base_url)
        self._var_gemma_model = tk.StringVar(value=self._settings.gemma_model)
        
        # Safety settings
        self._var_tool_output_max_bytes = tk.IntVar(value=self._settings.tool_output_max_bytes)
        self._var_context_truncation_enabled = tk.BooleanVar(value=self._settings.context_truncation_enabled)
        self._var_default_mode = tk.StringVar(value=self._settings.default_mode)

        # Create notebook (tabbed interface)
        notebook = ttk.Notebook(self)
        notebook.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        
        # Create tabs
        self._create_llm_tab(notebook)
        self._create_safety_tab(notebook)
        
        # Bottom buttons
        btns = ttk.Frame(self, padding=(8, 0, 8, 8))
        btns.grid(row=1, column=0, sticky="e")
        btn_save = ttk.Button(btns, text="Save", command=self._on_save)
        btn_cancel = ttk.Button(btns, text="Cancel", command=self._on_cancel)
        btn_save.grid(row=0, column=0, padx=(0, 8))
        btn_cancel.grid(row=0, column=1)

        self.bind("<Return>", lambda _e: self._on_save())
        self.bind("<Escape>", lambda _e: self._on_cancel())
        
    def _create_llm_tab(self, notebook: ttk.Notebook) -> None:
        """Create the LLM configuration tab."""
        frame = ttk.Frame(notebook, padding=16)
        notebook.add(frame, text="🤖 LLM")
        frame.columnconfigure(0, weight=1)

        # Preset buttons at the top
        preset_frame = ttk.LabelFrame(frame, text="Quick Presets", padding=8)
        preset_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        preset_frame.columnconfigure(0, weight=1)
        preset_frame.columnconfigure(1, weight=1)
        preset_frame.columnconfigure(2, weight=1)
        
        ttk.Button(preset_frame, text="🤖 OpenAI", command=self._preset_openai).grid(row=0, column=0, padx=2, sticky="ew")
        ttk.Button(preset_frame, text="🦙 Ollama", command=self._preset_ollama).grid(row=0, column=1, padx=2, sticky="ew")
        ttk.Button(preset_frame, text="🔧 Custom", command=self._preset_custom).grid(row=0, column=2, padx=2, sticky="ew")

        ttk.Label(frame, text="API Key (leave empty for Ollama)").grid(row=1, column=0, sticky="w")
        entry_api = ttk.Entry(frame, textvariable=self._var_api_key, show="*", width=50)
        entry_api.grid(row=2, column=0, sticky="ew", pady=(0, 12))

        ttk.Label(frame, text="Model").grid(row=3, column=0, sticky="w")
        
        # Model selection with combobox and refresh button
        model_frame = ttk.Frame(frame)
        model_frame.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        model_frame.columnconfigure(0, weight=1)
        
        self._model_combo = ttk.Combobox(model_frame, textvariable=self._var_model)
        self._model_combo.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        
        ttk.Button(model_frame, text="🔄 Refresh", command=self._refresh_models, width=10).grid(row=0, column=1)

        ttk.Label(frame, text="Base URL").grid(row=5, column=0, sticky="w")
        entry_url = ttk.Entry(frame, textvariable=self._var_base_url)
        entry_url.grid(row=6, column=0, sticky="ew", pady=(0, 12))

        ttk.Label(frame, text="LLM timeout (seconds)").grid(row=7, column=0, sticky="w")
        entry_llm_timeout = ttk.Entry(frame, textvariable=self._var_llm_timeout)
        entry_llm_timeout.grid(row=8, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(frame, text="LLM rate limit per minute (optional)").grid(row=9, column=0, sticky="w")
        entry_rate = ttk.Entry(frame, textvariable=self._var_rate_limit)
        entry_rate.grid(row=10, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(frame, text="Shell timeout (seconds)").grid(row=11, column=0, sticky="w")
        entry_shell_timeout = ttk.Entry(frame, textvariable=self._var_shell_timeout)
        entry_shell_timeout.grid(row=12, column=0, sticky="ew", pady=(0, 12))

        ttk.Label(frame, text="Agent system prompt").grid(row=13, column=0, sticky="w")
        self._agent_prompt_text = tk.Text(frame, height=4, wrap="word")
        self._agent_prompt_text.grid(row=14, column=0, sticky="ew", pady=(0, 12))
        initial_prompt = self._settings.agent_prompt or DEFAULT_AGENT_PROMPT
        self._agent_prompt_text.insert("1.0", initial_prompt)

        # Gemma Background Worker Settings
        gemma_frame = ttk.LabelFrame(frame, text="🤖 Gemma Background Worker (Optional)", padding=8)
        gemma_frame.grid(row=15, column=0, sticky="ew", pady=(0, 12))
        gemma_frame.columnconfigure(1, weight=1)
        
        ttk.Checkbutton(
            gemma_frame, 
            text="Enable Gemma for auto-tagging, descriptions, and summaries",
            variable=self._var_gemma_enabled
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        
        ttk.Label(gemma_frame, text="Gemma Base URL:").grid(row=1, column=0, sticky="w", padx=(20, 8))
        ttk.Entry(gemma_frame, textvariable=self._var_gemma_base_url).grid(row=1, column=1, columnspan=2, sticky="ew", pady=(0, 4))
        
        ttk.Label(gemma_frame, text="Gemma Model:").grid(row=2, column=0, sticky="w", padx=(20, 8))
        self._gemma_model_combo = ttk.Combobox(gemma_frame, textvariable=self._var_gemma_model)
        self._gemma_model_combo.grid(row=2, column=1, sticky="ew", padx=(0, 4))
        ttk.Button(gemma_frame, text="🔄", command=self._refresh_gemma_models, width=4).grid(row=2, column=2)
    
    def _create_safety_tab(self, notebook: ttk.Notebook) -> None:
        """Create the Safety configuration tab."""
        frame = ttk.Frame(notebook, padding=16)
        notebook.add(frame, text="🛡️ Safety")
        frame.columnconfigure(0, weight=1)
        
        # Info section
        info_frame = ttk.LabelFrame(frame, text="About Safety Features", padding=8)
        info_frame.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        
        info_text = (
            "GlyphX includes safety features to protect against excessive resource usage:\n\n"
            "• Chat Mode (🛡️ Safe): Tools are disabled for basic conversations\n"
            "• Agent Mode (⚡ Agent): Tools are enabled with safety validation\n"
            "• Context Truncation: Limits tool output to prevent memory issues"
        )
        ttk.Label(info_frame, text=info_text, justify="left", wraplength=450).grid(row=0, column=0, sticky="w")
        
        # Tool Output Settings
        output_frame = ttk.LabelFrame(frame, text="Tool Output Settings", padding=8)
        output_frame.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        output_frame.columnconfigure(1, weight=1)
        
        ttk.Label(output_frame, text="Max output size (bytes):").grid(row=0, column=0, sticky="w", pady=4)
        
        # Spinbox for tool output max bytes
        output_control_frame = ttk.Frame(output_frame)
        output_control_frame.grid(row=0, column=1, sticky="ew", pady=4)
        output_control_frame.columnconfigure(0, weight=1)
        
        self._spinbox_output = tk.Spinbox(
            output_control_frame,
            from_=1000,
            to=100000,
            increment=1000,
            textvariable=self._var_tool_output_max_bytes,
            width=15
        )
        self._spinbox_output.grid(row=0, column=0, sticky="w", padx=(0, 8))
        
        # Display KB value
        self._label_kb = ttk.Label(output_control_frame, text="")
        self._label_kb.grid(row=0, column=1, sticky="w")
        self._update_kb_label()
        self._var_tool_output_max_bytes.trace_add("write", lambda *_: self._update_kb_label())
        
        ttk.Label(output_frame, text="Range: 1,000 - 100,000 bytes (1 KB - 100 KB)", font=("Segoe UI", 8)).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        
        # Context Truncation
        ttk.Checkbutton(
            output_frame,
            text="Enable automatic context truncation",
            variable=self._var_context_truncation_enabled
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=4)
        
        ttk.Label(
            output_frame,
            text="When enabled, tool outputs exceeding the limit will be automatically truncated.",
            font=("Segoe UI", 8),
            foreground="gray"
        ).grid(row=3, column=0, columnspan=2, sticky="w")
        
        # Default Mode Settings
        mode_frame = ttk.LabelFrame(frame, text="Default Mode", padding=8)
        mode_frame.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        
        ttk.Label(mode_frame, text="Start in mode:").grid(row=0, column=0, sticky="w", pady=4)
        
        mode_selector = ttk.Combobox(
            mode_frame,
            textvariable=self._var_default_mode,
            values=["chat", "agent"],
            state="readonly",
            width=15
        )
        mode_selector.grid(row=0, column=1, sticky="w", padx=(8, 0), pady=4)
        
        ttk.Label(
            mode_frame,
            text="• chat: Safe mode with tools disabled (recommended)\n• agent: Agent mode with tools enabled",
            font=("Segoe UI", 8),
            foreground="gray",
            justify="left"
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
        
        # Reset to Defaults button
        reset_frame = ttk.Frame(frame)
        reset_frame.grid(row=3, column=0, sticky="e")
        ttk.Button(reset_frame, text="Reset to Defaults", command=self._reset_safety_defaults).grid(row=0, column=0)
    
    def _update_kb_label(self) -> None:
        """Update the KB label when the output size changes."""
        try:
            bytes_val = self._var_tool_output_max_bytes.get()
            kb_val = bytes_val / 1000
            self._label_kb.config(text=f"({kb_val:.1f} KB)")
        except:
            self._label_kb.config(text="")
    
    def _reset_safety_defaults(self) -> None:
        """Reset safety settings to default values."""
        self._var_tool_output_max_bytes.set(8000)
        self._var_context_truncation_enabled.set(True)
        self._var_default_mode.set("chat")
        messagebox.showinfo(
            "Reset to Defaults",
            "Safety settings have been reset to defaults:\n\n"
            "• Max output: 8,000 bytes (8 KB)\n"
            "• Truncation: Enabled\n"
            "• Default mode: chat",
            parent=self
        )

    def show(self) -> None:
        self.wait_window(self)

    def _preset_openai(self) -> None:
        """Apply OpenAI preset configuration."""
        self._var_base_url.set("https://api.openai.com/v1")
        self._var_model.set("gpt-4o-mini")
        self._var_llm_timeout.set("60.0")
        self._var_rate_limit.set("60")
        # Keep existing API key
        messagebox.showinfo(
            "OpenAI Preset",
            "Applied OpenAI configuration:\n\n"
            "• Base URL: https://api.openai.com/v1\n"
            "• Model: gpt-4o-mini\n"
            "• Timeout: 60s\n"
            "• Rate Limit: 60/min\n\n"
            "Don't forget to set your API key!",
            parent=self
        )

    def _preset_ollama(self) -> None:
        """Apply Ollama preset configuration for local models."""
        self._var_api_key.set("")  # Ollama doesn't need API key
        self._var_base_url.set("http://localhost:11434/v1")
        self._var_model.set("llama3.2")
        self._var_llm_timeout.set("120.0")
        self._var_rate_limit.set("")  # No rate limit for local
        messagebox.showinfo(
            "Ollama Preset",
            "Applied Ollama configuration:\n\n"
            "• Base URL: http://localhost:11434/v1\n"
            "• Model: llama3.2\n"
            "• Timeout: 120s\n"
            "• Rate Limit: None (local model)\n"
            "• API Key: Not required\n\n"
            "Make sure Ollama is running:\n"
            "  ollama serve\n"
            "  ollama pull llama3.2",
            parent=self
        )

    def _preset_custom(self) -> None:
        """Show info about custom configuration."""
        messagebox.showinfo(
            "Custom Configuration",
            "Configure your custom LLM provider:\n\n"
            "• Enter your API endpoint in Base URL\n"
            "• Set your model name\n"
            "• Add API key if required\n"
            "• Adjust timeouts as needed\n\n"
            "Compatible with any OpenAI-compatible API.",
            parent=self
        )
    
    def _refresh_models(self) -> None:
        """Fetch available models from the configured provider."""
        base_url = self._var_base_url.get().strip()
        api_key = self._var_api_key.get().strip() or None
        
        if not base_url:
            messagebox.showwarning(
                "Refresh Models",
                "Please enter a Base URL first.",
                parent=self
            )
            return
        
        # Show loading message
        self._model_combo.configure(state="disabled")
        self._model_combo.set("Loading models...")
        self.update()
        
        try:
            models = self._fetch_models(base_url, api_key)
            
            if models:
                self._model_combo.configure(values=models, state="normal")
                if self._var_model.get() not in models and models:
                    self._var_model.set(models[0])
                messagebox.showinfo(
                    "Models Loaded",
                    f"Found {len(models)} available models.",
                    parent=self
                )
            else:
                self._model_combo.configure(state="normal")
                messagebox.showwarning(
                    "No Models",
                    "No models found. Check your Base URL and API key.",
                    parent=self
                )
        except Exception as exc:
            self._model_combo.configure(state="normal")
            self._model_combo.set(self._settings.model)
            messagebox.showerror(
                "Refresh Failed",
                f"Failed to fetch models:\n{exc}\n\n"
                "Make sure the service is running and accessible.",
                parent=self
            )
    
    def _fetch_models(self, base_url: str, api_key: str | None) -> list[str]:
        """Fetch available models from OpenAI-compatible API."""
        from openai import OpenAI
        import re
        
        # Detect provider type from URL
        is_ollama = "ollama" in base_url.lower() or "11434" in base_url
        
        try:
            client = OpenAI(base_url=base_url, api_key=api_key or "not-needed")
            
            if is_ollama:
                # Ollama: Use /api/tags endpoint directly
                import requests
                ollama_base = re.sub(r'/v1/?$', '', base_url)
                response = requests.get(f"{ollama_base}/api/tags", timeout=5.0)
                response.raise_for_status()
                data = response.json()
                models = [model['name'] for model in data.get('models', [])]
            else:
                # OpenAI-compatible: Use /v1/models endpoint
                response = client.models.list()
                models = [model.id for model in response.data]
            
            # Sort models alphabetically
            return sorted(models)
            
        except Exception as exc:
            raise Exception(f"Could not fetch models: {exc}")
    
    def _refresh_gemma_models(self) -> None:
        """Fetch available Ollama models for Gemma."""
        base_url = self._var_gemma_base_url.get().strip()
        
        if not base_url:
            messagebox.showwarning(
                "Refresh Models",
                "Please enter a Gemma Base URL first.",
                parent=self
            )
            return
        
        self._gemma_model_combo.configure(state="disabled")
        self._gemma_model_combo.set("Loading...")
        self.update()
        
        try:
            models = self._fetch_models(base_url, None)
            
            if models:
                self._gemma_model_combo.configure(values=models, state="normal")
                if self._var_gemma_model.get() not in models and models:
                    # Prefer gemma models
                    gemma_models = [m for m in models if 'gemma' in m.lower()]
                    self._var_gemma_model.set(gemma_models[0] if gemma_models else models[0])
                messagebox.showinfo(
                    "Models Loaded",
                    f"Found {len(models)} Ollama models.",
                    parent=self
                )
            else:
                self._gemma_model_combo.configure(state="normal")
                messagebox.showwarning(
                    "No Models",
                    "No Ollama models found. Make sure Ollama is running:\n"
                    "  ollama serve",
                    parent=self
                )
        except Exception as exc:
            self._gemma_model_combo.configure(state="normal")
            self._gemma_model_combo.set(self._settings.gemma_model)
            messagebox.showerror(
                "Refresh Failed",
                f"Failed to fetch Ollama models:\n{exc}\n\n"
                "Make sure Ollama is running:\n"
                "  ollama serve",
                parent=self
            )

    def _on_save(self) -> None:
        data = {
            "api_key": self._var_api_key.get().strip() or None,
            "model": self._var_model.get().strip() or self._settings.model,
            "base_url": self._var_base_url.get().strip() or self._settings.base_url,
            "agent_prompt": self._agent_prompt_text.get("1.0", "end").strip() or None,
            "llm_timeout": self._var_llm_timeout.get().strip() or str(self._settings.llm_timeout),
            "llm_rate_limit_per_minute": self._var_rate_limit.get().strip() or None,
            "shell_timeout": self._var_shell_timeout.get().strip() or str(self._settings.shell_timeout),
            "gemma_enabled": self._var_gemma_enabled.get(),
            "gemma_base_url": self._var_gemma_base_url.get().strip() or "http://localhost:11434/v1",
            "gemma_model": self._var_gemma_model.get().strip() or "gemma:300m",
            "tool_output_max_bytes": self._var_tool_output_max_bytes.get(),
            "context_truncation_enabled": self._var_context_truncation_enabled.get(),
            "default_mode": self._var_default_mode.get(),
        }
        if data["agent_prompt"] == DEFAULT_AGENT_PROMPT:
            data["agent_prompt"] = None
        try:
            self._service.update(**data)
        except ValueError as exc:
            messagebox.showerror("Settings", str(exc), parent=self)
            return
        
        # Notify user about changes
        messages = []
        if self._settings.gemma_enabled != data["gemma_enabled"]:
            messages.append("Gemma settings updated. Restart GlyphX for changes to take effect.")
        if (self._settings.tool_output_max_bytes != data["tool_output_max_bytes"] or
            self._settings.context_truncation_enabled != data["context_truncation_enabled"]):
            messages.append("Safety settings updated. Changes take effect immediately.")
        if self._settings.default_mode != data["default_mode"]:
            messages.append(f"Default mode changed to '{data['default_mode']}'. Will apply on next start.")
        
        if messages:
            messagebox.showinfo("Settings Saved", "\n\n".join(messages), parent=self)
        
        self.destroy()

    def _on_cancel(self) -> None:
        self.destroy()
