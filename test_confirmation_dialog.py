"""Manual test script to demonstrate the ToolConfirmationDialog."""

import tkinter as tk
from tkinter import ttk, messagebox
from glyphx.app.gui import ToolConfirmationDialog


def test_confirmation_dialog():
    """Create a test window to demo the confirmation dialog."""
    root = tk.Tk()
    root.title("Tool Confirmation Dialog Test")
    root.geometry("400x300")
    
    result_var = tk.StringVar(value="No dialog shown yet")
    
    def show_shell_dialog():
        """Show confirmation for shell command."""
        dialog = ToolConfirmationDialog(
            root,
            tool_name="run_shell",
            arguments={
                "command": "rm -rf /important/data",
                "cwd": "/home/user/project"
            },
            mode="chat"
        )
        action, remember = dialog.show()
        result_var.set(f"Action: {action}, Remember: {remember}")
    
    def show_file_dialog():
        """Show confirmation for file write."""
        dialog = ToolConfirmationDialog(
            root,
            tool_name="write_file",
            arguments={
                "path": "/etc/passwd",
                "content": "malicious content here..."
            },
            mode="agent"
        )
        action, remember = dialog.show()
        result_var.set(f"Action: {action}, Remember: {remember}")
    
    def show_large_args_dialog():
        """Show confirmation with large arguments."""
        long_content = "x" * 500  # Long content to test truncation
        dialog = ToolConfirmationDialog(
            root,
            tool_name="run_shell",
            arguments={
                "command": f"echo {long_content}",
                "timeout": 30,
                "cwd": "/very/long/path/to/some/directory"
            },
            mode="chat"
        )
        action, remember = dialog.show()
        result_var.set(f"Action: {action}, Remember: {remember}")
    
    # Main frame
    frame = ttk.Frame(root, padding=20)
    frame.pack(fill="both", expand=True)
    
    ttk.Label(
        frame,
        text="Tool Confirmation Dialog Test",
        font=("Segoe UI", 14, "bold")
    ).pack(pady=(0, 20))
    
    ttk.Label(
        frame,
        text="Click a button to see the confirmation dialog:",
    ).pack(pady=(0, 10))
    
    ttk.Button(
        frame,
        text="Show Shell Command Confirmation",
        command=show_shell_dialog,
        width=40
    ).pack(pady=5)
    
    ttk.Button(
        frame,
        text="Show File Write Confirmation (Agent)",
        command=show_file_dialog,
        width=40
    ).pack(pady=5)
    
    ttk.Button(
        frame,
        text="Show Large Arguments Dialog",
        command=show_large_args_dialog,
        width=40
    ).pack(pady=5)
    
    ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=20)
    
    ttk.Label(frame, text="Last Result:").pack()
    ttk.Label(frame, textvariable=result_var, font=("Consolas", 10)).pack(pady=10)
    
    ttk.Button(frame, text="Close", command=root.quit).pack(pady=(20, 0))
    
    root.mainloop()


if __name__ == "__main__":
    test_confirmation_dialog()
