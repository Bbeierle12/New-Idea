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
            ("💬 Chat", "chat"),
            ("🤖 Agent", "agent"),
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
    ) -> None:
        super().__init__(master, padding=8)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        self._registry = registry
        self._worker = worker
        self._tools = tools
        self._logger = logger
        self._history_service = history
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
        dialog = GlyphDialog(self.winfo_toplevel(), title="Add Glyph")
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
        dialog = GlyphDialog(self.winfo_toplevel(), title="Edit Glyph", initial=glyph)
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
    ) -> None:
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

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
        ent_tags = ttk.Entry(frm, textvariable=self._var_tags)
        ent_tags.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        btn_save = ttk.Button(frm, text="Save", command=self._on_save)
        btn_cancel = ttk.Button(frm, text="Cancel", command=self._on_cancel)
        btn_save.grid(row=10, column=0, sticky="e", padx=(0, 8))
        btn_cancel.grid(row=10, column=1, sticky="w")

        self.bind("<Return>", lambda _e: self._on_save())
        self.bind("<Escape>", lambda _e: self._on_cancel())
        ent_name.focus_set()

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
class ChatPanel(ttk.Frame):
    """Chat REPL with tool-calling support."""

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
    ) -> None:
        super().__init__(master, padding=8)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
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

        transcript_frame = ttk.Frame(self)
        transcript_frame.grid(row=0, column=0, sticky="nsew")
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

        input_frame = ttk.Frame(self)
        input_frame.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        input_frame.columnconfigure(0, weight=1)

        self._input = tk.Text(input_frame, height=4, wrap="word")
        self._input.grid(row=0, column=0, sticky="ew")
        self._input.bind("<Control-Return>", self._on_send)

        buttons = ttk.Frame(input_frame)
        buttons.grid(row=0, column=1, padx=(8, 0), sticky="ns")
        self._send_button = ttk.Button(buttons, text="Send", command=self._on_send)
        clear_button = ttk.Button(buttons, text="Clear", command=self._clear_chat)
        self._send_button.grid(row=0, column=0, sticky="ew")
        clear_button.grid(row=1, column=0, pady=(4, 0), sticky="ew")

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
        state = tk.DISABLED if pending else tk.NORMAL
        self._send_button.configure(state=state)

    def _write_history(self, message: ChatMessage) -> None:
        meta: dict[str, str] = {}
        if message.name:
            meta["name"] = message.name
        if message.tool_call_id:
            meta["tool_call_id"] = message.tool_call_id
        self._history.append(message.role, message.content or "", **meta)

    def _clear_chat(self) -> None:
        self._messages.clear()
        self._transcript.configure(state="normal")
        self._transcript.delete("1.0", "end")
        self._transcript.configure(state="disabled")

    def _on_send(self, *_args: object) -> None:
        if self._pending:
            return
        content = self._input.get("1.0", "end").strip()
        if not content:
            return
        self._input.delete("1.0", "end")
        user_msg = ChatMessage(role="user", content=content)
        self._messages.append(user_msg)
        self._append_transcript(user_msg)
        self._write_history(user_msg)
        self._logger.info("chat_send", length=str(len(content)))
        self._set_pending(True)
        baseline = len(self._messages)
        tools_schema = self._tools.tool_descriptions()
        
        # Prepare for streaming display
        self._transcript.configure(state="normal")
        self._transcript.insert("end", "Assistant: ")
        self._transcript.configure(state="disabled")
        self._streaming_buffer = ""

        def job() -> dict[str, object]:
            conversation = [ChatMessage.from_dict(m.to_dict()) for m in self._messages]
            try:
                loop_result = self._chat_loop_streaming(conversation, tools_schema)
                loop_result["conversation"] = [m.to_dict() for m in conversation]
                loop_result["ok"] = True
                return loop_result
            except Exception as exc:  # noqa: BLE001
                self._logger.error(
                    "chat_error",
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
                    new_messages = conversation[baseline:]
                    self._messages = conversation
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
                        "Chat Error",
                        f"Failed to complete chat: {result.get('error')}",
                        parent=self.winfo_toplevel(),
                    )

            self.after(0, apply)

        self._worker.submit(job, description="chat_send", callback=callback)

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
    ) -> dict[str, object]:
        """Chat loop with streaming support."""
        return _run_tool_loop_streaming(
            self._llm,
            self._tools,
            self._logger,
            conversation,
            tools_schema,
            self._max_steps,
            command_history=self._command_history,
            history_source="chat",
            on_token=self._append_streaming_token,
        )

    # ------------------------------------------------------------------
    def _chat_loop(
        self,
        conversation: list[ChatMessage],
        tools_schema: list[dict[str, object]],
    ) -> dict[str, object]:
        return _run_tool_loop(
            self._llm,
            self._tools,
            self._logger,
            conversation,
            tools_schema,
            self._max_steps,
            command_history=self._command_history,
            history_source="chat",
        )




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
) -> dict[str, object]:
    """Tool loop with streaming support for assistant responses."""
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
) -> dict[str, object]:
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


class AgentPanel(ttk.Frame):
    """One-shot agent runner that loops through tool calls."""

    TRANSCRIPT_CHAR_LIMIT = 1200

    def __init__(
        self,
        master: tk.Misc,
        worker: Worker,
        llm_client: LLMClient,
        tools: ToolsBridge,
        command_history: CommandHistory,
        logger: Logger,
        *,
        max_steps: int = 6,
    ) -> None:
        super().__init__(master, padding=8)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._worker = worker
        self._llm = llm_client
        self._tools = tools
        self._command_history = command_history
        self._logger = logger
        self._max_steps = max_steps
        self._running = False
        self._goal_var = tk.StringVar()

        controls = ttk.Frame(self)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        controls.columnconfigure(0, weight=1)

        self._goal_entry = ttk.Entry(controls, textvariable=self._goal_var)
        self._goal_entry.grid(row=0, column=0, sticky="ew")
        self._goal_entry.bind("<Return>", self._on_run)

        self._run_button = ttk.Button(controls, text="Run", command=self._on_run)
        self._run_button.grid(row=0, column=1, padx=(8, 0))

        clear_button = ttk.Button(controls, text="Clear", command=self._clear_log)
        clear_button.grid(row=0, column=2, padx=(4, 0))

        self._log = tk.Text(self, wrap="word", state="disabled", height=20)
        self._log.grid(row=1, column=0, sticky="nsew")

    # ------------------------------------------------------------------
    def _on_run(self, *_args: object) -> None:
        if self._running:
            return
        goal = self._goal_var.get().strip()
        if not goal:
            messagebox.showinfo("Agent", "Enter a goal to run.", parent=self.winfo_toplevel())
            return
        self._set_running(True)
        if self._log.index("end-1c") != "1.0":
            self._append_text("\n")
        self._append_line("Goal", goal)
        self._append_line("Status", "Working…")
        tools_schema = self._tools.tool_descriptions()
        base_conversation = [
            ChatMessage(role="system", content=self._agent_prompt),
            ChatMessage(role="user", content=goal),
        ]

        def job() -> dict[str, object]:
            conversation = [ChatMessage.from_dict(msg.to_dict()) for msg in base_conversation]
            try:
                result = _run_tool_loop(
                    self._llm,
                    self._tools,
                    self._logger,
                    conversation,
                    tools_schema,
                    self._max_steps,
                    command_history=self._command_history,
                    history_source="agent",
                )
                return {
                    "ok": True,
                    "conversation": [msg.to_dict() for msg in conversation],
                    "reply": result.get("reply"),
                    "usage": result.get("usage"),
                }
            except Exception as exc:  # noqa: BLE001
                self._logger.error(
                    "agent_error",
                    error=f"{type(exc).__name__}: {exc}",
                )
                return {
                    "ok": False,
                    "error": exc,
                    "conversation": [msg.to_dict() for msg in conversation],
                }

        def callback(result: dict[str, object]) -> None:
            def apply() -> None:
                self._set_running(False)
                conversation_payload = result.get("conversation")
                if isinstance(conversation_payload, list):
                    self._render_conversation(conversation_payload)
                if result.get("ok"):
                    self._append_line("Status", "Completed")
                else:
                    error_text = str(result.get("error"))
                    self._append_line("Status", f"Failed: {error_text}")
                    messagebox.showerror(
                        "Agent Error",
                        f"Agent run failed: {error_text}",
                        parent=self.winfo_toplevel(),
                    )
                self._goal_entry.focus_set()

            self.after(0, apply)

        self._worker.submit(job, description="agent_run", callback=callback)

    def set_prompt(self, prompt: Optional[str]) -> None:
        self._agent_prompt = prompt or DEFAULT_AGENT_PROMPT

    def _render_conversation(self, payloads: list[dict[str, object]]) -> None:
        for payload in payloads:
            if not isinstance(payload, dict):
                continue
            message = ChatMessage.from_dict(payload)
            if message.role == "system":
                continue
            if message.role == "user":
                continue
            if message.role == "tool":
                prefix = f"[tool:{message.name}]" if message.name else "[tool]"
            else:
                prefix = "Assistant"
            self._append_line(prefix, message.content or "")

    def _append_line(self, prefix: str, content: str) -> None:
        display = self._truncate(content, self.TRANSCRIPT_CHAR_LIMIT)
        line = f"{prefix}: {display}\n" if prefix else f"{display}\n"
        self._append_text(line)

    def _append_text(self, text: str) -> None:
        self._log.configure(state="normal")
        self._log.insert("end", text)
        self._log.configure(state="disabled")
        self._log.see("end")

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[:limit] + "… (truncated)"

    def _set_running(self, running: bool) -> None:
        self._running = running
        state = tk.DISABLED if running else tk.NORMAL
        self._run_button.configure(state=state)
        self._goal_entry.configure(state=state)

    def _clear_log(self) -> None:
        if self._running:
            return
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")

def _extract_first_choice(payload: dict[str, object]) -> dict[str, object] | None:
    choices = payload.get("choices") if isinstance(payload, dict) else None
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            return first
    return None


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
        self.tools = ToolsBridge(self.registry, self.logger, default_shell_timeout=self.settings.get().shell_timeout)
        self.export_service = ExportService(self.logger)
        self.llm_client = LLMClient(self.settings, self.logger)
        self.chat_history = ChatHistory(self.paths.chat_history_path)
        self.command_history = CommandHistory(self.paths.command_history_path)
        self.crash_reporter = CrashReporter(self.paths.logs_dir / "crash.jsonl", self.logger)
        self.crash_reporter.install()
        self.update_checker = UpdateChecker("0.1.0", self.logger)

        self._setup_ui()
        self._wire_logger()
        self.worker.start()
        self.update_checker.schedule(self.worker, delay=5.0)
        self._bootstrap_worker()

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
        self.glyphs_panel = GlyphsPanel(self.content_frame, self.registry, self.worker, self.tools, self.logger, self.command_history)
        self._panels["glyphs"] = self.glyphs_panel
        
        # Chat panel
        self.chat_panel = ChatPanel(
            self.content_frame,
            self.worker,
            self.llm_client,
            self.tools,
            self.chat_history,
            self.command_history,
            self.logger,
        )
        self._panels["chat"] = self.chat_panel
        
        # Agent panel
        self.agent_panel = AgentPanel(
            self.content_frame,
            self.worker,
            self.llm_client,
            self.tools,
            self.command_history,
            self.logger,
        )
        self.agent_panel.set_prompt(self._current_agent_prompt())
        self._panels["agent"] = self.agent_panel
        
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
        self.agent_panel.set_prompt(self._current_agent_prompt())

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

        frame = ttk.Frame(self, padding=16)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text="API Key").grid(row=0, column=0, sticky="w")
        entry_api = ttk.Entry(frame, textvariable=self._var_api_key, show="*", width=50)
        entry_api.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        ttk.Label(frame, text="Model").grid(row=2, column=0, sticky="w")
        entry_model = ttk.Entry(frame, textvariable=self._var_model)
        entry_model.grid(row=3, column=0, sticky="ew", pady=(0, 12))

        ttk.Label(frame, text="Base URL").grid(row=4, column=0, sticky="w")
        entry_url = ttk.Entry(frame, textvariable=self._var_base_url)
        entry_url.grid(row=5, column=0, sticky="ew", pady=(0, 12))

        ttk.Label(frame, text="LLM timeout (seconds)").grid(row=6, column=0, sticky="w")
        entry_llm_timeout = ttk.Entry(frame, textvariable=self._var_llm_timeout)
        entry_llm_timeout.grid(row=7, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(frame, text="LLM rate limit per minute (optional)").grid(row=8, column=0, sticky="w")
        entry_rate = ttk.Entry(frame, textvariable=self._var_rate_limit)
        entry_rate.grid(row=9, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(frame, text="Shell timeout (seconds)").grid(row=10, column=0, sticky="w")
        entry_shell_timeout = ttk.Entry(frame, textvariable=self._var_shell_timeout)
        entry_shell_timeout.grid(row=11, column=0, sticky="ew", pady=(0, 12))

        ttk.Label(frame, text="Agent system prompt").grid(row=12, column=0, sticky="w")
        self._agent_prompt_text = tk.Text(frame, height=4, wrap="word")
        self._agent_prompt_text.grid(row=13, column=0, sticky="ew", pady=(0, 12))
        initial_prompt = self._settings.agent_prompt or DEFAULT_AGENT_PROMPT
        self._agent_prompt_text.insert("1.0", initial_prompt)

        btns = ttk.Frame(frame)
        btns.grid(row=14, column=0, sticky="e")
        btn_save = ttk.Button(btns, text="Save", command=self._on_save)
        btn_cancel = ttk.Button(btns, text="Cancel", command=self._on_cancel)
        btn_save.grid(row=0, column=0, padx=(0, 8))
        btn_cancel.grid(row=0, column=1)

        self.bind("<Return>", lambda _e: self._on_save())
        self.bind("<Escape>", lambda _e: self._on_cancel())
        entry_api.focus_set()

    def show(self) -> None:
        self.wait_window(self)

    def _on_save(self) -> None:
        data = {
            "api_key": self._var_api_key.get().strip() or None,
            "model": self._var_model.get().strip() or self._settings.model,
            "base_url": self._var_base_url.get().strip() or self._settings.base_url,
            "agent_prompt": self._agent_prompt_text.get("1.0", "end").strip() or None,
            "llm_timeout": self._var_llm_timeout.get().strip() or str(self._settings.llm_timeout),
            "llm_rate_limit_per_minute": self._var_rate_limit.get().strip() or None,
            "shell_timeout": self._var_shell_timeout.get().strip() or str(self._settings.shell_timeout),
        }
        if data["agent_prompt"] == DEFAULT_AGENT_PROMPT:
            data["agent_prompt"] = None
        try:
            self._service.update(**data)
        except ValueError as exc:
            messagebox.showerror("Settings", str(exc), parent=self)
            return
        self.destroy()

    def _on_cancel(self) -> None:
        self.destroy()
