# GlyphX Manual Testing Guide

**Version:** Step 5 - Production Readiness  
**Last Updated:** 2024  
**Purpose:** Manual testing procedures for GUI features and user workflows

---

## Table of Contents

1. [Pre-Testing Setup](#pre-testing-setup)
2. [Settings Dialog Testing](#settings-dialog-testing)
3. [Mode Switching Testing](#mode-switching-testing)
4. [Safety Features Testing](#safety-features-testing)
5. [Error Handling Testing](#error-handling-testing)
6. [Integration Testing](#integration-testing)
7. [Regression Testing](#regression-testing)

---

## Pre-Testing Setup

### Requirements
- ✅ Python 3.13+ installed
- ✅ All dependencies installed (`pip install -e .[dev]`)
- ✅ OpenAI API key available (or compatible LLM API)
- ✅ All automated tests passing (100+ tests)

### Launch Application
```bash
# Windows
python run_glyphx.py

# Or use the task
python -m glyphx.app
```

### Expected Result
- ✅ Application launches without errors
- ✅ Main window appears with title "GlyphX"
- ✅ Left sidebar visible with tabs
- ✅ Terminal panel visible at bottom
- ✅ AI chat panel visible on right
- ✅ Mode indicator visible in status bar

---

## Settings Dialog Testing

### Test 1.1: Open Settings Dialog

**Steps:**
1. Click "Settings..." button in the AI panel
2. Or use menu: Settings → Preferences

**Expected Result:**
- ✅ Settings dialog opens
- ✅ Two tabs visible: "LLM Settings" and "Safety Settings"
- ✅ Dialog is modal (main window is disabled)
- ✅ Dialog has appropriate size (not too small/large)

---

### Test 1.2: LLM Settings Tab

**Steps:**
1. Open Settings dialog
2. Ensure "LLM Settings" tab is selected
3. Verify all fields are visible:
   - API Key (password field, shows dots)
   - Model (text field)
   - Base URL (text field)
   - Timeout (numeric field)

**Expected Result:**
- ✅ All fields visible and accessible
- ✅ API Key field shows •••• characters (password masked)
- ✅ Current values populated if configured
- ✅ Defaults shown if not configured:
  - Model: "gpt-4o"
  - Base URL: "https://api.openai.com/v1"
  - Timeout: 30.0 seconds

**Test Values:**
- Enter API Key: `sk-test-12345678901234567890123456789012`
- Verify key is masked
- Change Model to: `gpt-4o-mini`
- Change Base URL to: `https://custom.api.com/v1`
- Change Timeout to: `60`

---

### Test 1.3: Safety Settings Tab

**Steps:**
1. Open Settings dialog
2. Click "Safety Settings" tab
3. Verify all controls visible:
   - Tool Output Limit (slider)
   - Context Truncation Enabled (checkbox)
   - Default Mode (radio buttons: Chat/Agent)

**Expected Result:**
- ✅ Safety Settings tab visible
- ✅ Tool Output Limit slider: 1000 - 100000 bytes
- ✅ Current value displayed next to slider
- ✅ KB/MB format shown (e.g., "8.0 KB" or "50.0 KB")
- ✅ Context Truncation checkbox (checked by default)
- ✅ Default Mode radio buttons (Chat selected by default)

**Test Values:**
1. Move slider to minimum (1000) - verify "1.0 KB" shown
2. Move slider to middle (50000) - verify "50.0 KB" shown
3. Move slider to maximum (100000) - verify "100.0 KB" shown
4. Uncheck Context Truncation
5. Select "Agent" mode

---

### Test 1.4: Save Settings

**Steps:**
1. Configure both tabs with test values (from 1.2 and 1.3)
2. Click "Save" button
3. Reopen Settings dialog

**Expected Result:**
- ✅ Dialog closes after clicking Save
- ✅ Main window re-enabled
- ✅ Reopening dialog shows saved values:
  - LLM tab: test API key (masked), gpt-4o-mini, custom URL, 60s timeout
  - Safety tab: slider at test position, truncation unchecked, Agent mode selected

---

### Test 1.5: Cancel Settings

**Steps:**
1. Open Settings dialog
2. Change some values (don't click Save)
3. Click "Cancel" button
4. Reopen Settings dialog

**Expected Result:**
- ✅ Dialog closes after clicking Cancel
- ✅ Main window re-enabled
- ✅ Reopening dialog shows original values (not the changed values)
- ✅ No changes persisted to config file

---

### Test 1.6: Reset to Defaults

**Steps:**
1. Configure custom settings and save
2. Reopen Settings dialog
3. Go to Safety Settings tab
4. Click "Reset to Defaults" button
5. Check both tabs

**Expected Result:**
- ✅ Safety settings reset to defaults:
  - Tool Output Limit: 8000 bytes (8.0 KB)
  - Context Truncation: Enabled (checked)
  - Default Mode: Chat (selected)
- ✅ LLM settings unchanged (only safety settings reset)
- ✅ Must click Save to persist the reset

---

### Test 1.7: Settings Validation

**Test Invalid Values:**

1. **Tool Output Limit Too Low:**
   - Try to set slider below 1000 bytes
   - Expected: Slider won't go below minimum

2. **Tool Output Limit Too High:**
   - Try to set slider above 100000 bytes
   - Expected: Slider won't go above maximum

3. **Invalid Timeout:**
   - Enter negative timeout: `-5`
   - Click Save
   - Expected: Error message or value rejected

4. **Empty Required Fields:**
   - Clear API Key field
   - Click Save
   - Expected: Settings save (API key can be empty for testing)

---

## Mode Switching Testing

### Test 2.1: Mode Indicator Visibility

**Steps:**
1. Launch application
2. Locate mode indicator in status bar (bottom of window)

**Expected Result:**
- ✅ Mode indicator visible in status bar
- ✅ Shows current mode (default: "Chat" mode)
- ✅ Indicator is clickable (cursor changes to hand on hover)

---

### Test 2.2: Switch to Agent Mode

**Steps:**
1. Click mode indicator
2. Or use keyboard shortcut: Ctrl+M (Cmd+M on Mac)
3. Or select from menu: Mode → Agent

**Expected Result:**
- ✅ Mode indicator updates to "Agent" mode
- ✅ Visual indication of change (e.g., color or icon)
- ✅ Mode persists across application restart

---

### Test 2.3: Switch to Chat Mode

**Steps:**
1. Ensure in Agent mode
2. Click mode indicator again
3. Or use keyboard shortcut: Ctrl+M
4. Or select from menu: Mode → Chat

**Expected Result:**
- ✅ Mode indicator updates to "Chat" mode
- ✅ Visual indication of change
- ✅ Mode persists across application restart

---

### Test 2.4: Mode Persistence

**Steps:**
1. Set mode to Agent
2. Close application completely
3. Relaunch application
4. Check mode indicator

**Expected Result:**
- ✅ Application starts in Agent mode (last used mode)
- ✅ Mode indicator shows "Agent"

---

### Test 2.5: Mode Affects Tool Availability

**Steps:**
1. Switch to Chat mode
2. Send message: "List all tools available"
3. Switch to Agent mode
4. Send message: "List all tools available"

**Expected Result:**
- ✅ Chat mode: Limited tool set (read-only operations)
- ✅ Agent mode: Full tool set (read + write operations)
- ✅ LLM responds differently based on mode

---

## Safety Features Testing

### Test 3.1: Safe Command Execution

**Steps:**
1. In Agent mode, send message: "Run command: echo hello"
2. Observe behavior

**Expected Result:**
- ✅ Command executes without confirmation
- ✅ Output shows: "hello"
- ✅ No safety warnings displayed

---

### Test 3.2: Dangerous Command Blocking

**Steps:**
1. In Agent mode, send message: "Run command: rm -rf /"
2. Or: "Delete all files in C:\\"

**Expected Result:**
- ✅ Confirmation dialog appears
- ✅ Dialog shows command about to execute
- ✅ Dialog has "Allow" and "Deny" buttons
- ✅ Dialog warns about dangerous operation
- ✅ Default action is "Deny" (safer option)

---

### Test 3.3: Approve Dangerous Command

**Steps:**
1. Trigger dangerous command confirmation (from 3.2)
2. Click "Allow" button
3. Observe behavior

**Expected Result:**
- ✅ Command executes (or attempts to)
- ✅ Output shows result
- ✅ Session remembers approval (same command won't prompt again in this session)

---

### Test 3.4: Deny Dangerous Command

**Steps:**
1. Trigger dangerous command confirmation
2. Click "Deny" button

**Expected Result:**
- ✅ Command does NOT execute
- ✅ Message shown: "Operation cancelled by user"
- ✅ No files modified
- ✅ Application remains stable

---

### Test 3.5: Output Truncation

**Steps:**
1. Set Tool Output Limit to 8000 bytes (8 KB)
2. Send message: "Read a very large file" (or "Generate 100KB of output")
3. Observe output

**Expected Result:**
- ✅ Output is truncated at ~8KB
- ✅ Truncation message shown: "[Output truncated - exceeded maximum size]"
- ✅ No performance degradation
- ✅ Application remains responsive

---

### Test 3.6: Disable Truncation

**Steps:**
1. Open Settings → Safety Settings
2. Uncheck "Context Truncation Enabled"
3. Save settings
4. Trigger large output operation

**Expected Result:**
- ✅ Full output displayed (no truncation)
- ✅ No truncation message
- ✅ May cause performance issues with very large outputs (expected)

---

### Test 3.7: File Path Validation

**Steps:**
1. Send message: "Write to file: /etc/passwd" (Linux/Mac)
2. Or: "Write to file: C:\\Windows\\System32\\test.txt" (Windows)

**Expected Result:**
- ✅ Operation blocked or requires confirmation
- ✅ Warning about writing to system directory
- ✅ If confirmed, operation may still fail due to permissions (expected)

---

## Error Handling Testing

### Test 4.1: Invalid API Key

**Steps:**
1. Configure invalid API key: `sk-invalid123`
2. Send message to AI
3. Observe error handling

**Expected Result:**
- ✅ Error message displayed in chat
- ✅ Error is user-friendly (not raw exception)
- ✅ Suggests checking settings
- ✅ Application doesn't crash

---

### Test 4.2: Network Error

**Steps:**
1. Set Base URL to invalid endpoint: `https://invalid.url.com/v1`
2. Send message to AI
3. Observe error handling

**Expected Result:**
- ✅ Connection error displayed
- ✅ Error indicates network problem
- ✅ Application remains responsive
- ✅ Can update settings without restart

---

### Test 4.3: Timeout Error

**Steps:**
1. Set Timeout to very low value: `0.1` seconds
2. Send complex message requiring long processing
3. Observe error handling

**Expected Result:**
- ✅ Timeout error after 0.1 seconds
- ✅ Error message explains timeout
- ✅ Suggests increasing timeout value
- ✅ Application doesn't hang

---

### Test 4.4: Corrupted Config File

**Steps:**
1. Close application
2. Open `~/.glyphx/config.json` (or OS equivalent)
3. Add invalid JSON: `{invalid: content}`
4. Launch application

**Expected Result:**
- ✅ Application launches successfully
- ✅ Uses default settings (config corruption handled gracefully)
- ✅ Warning logged about corrupted config
- ✅ Settings dialog shows defaults

---

### Test 4.5: Missing Permissions

**Steps:**
1. Try to write file in protected directory
2. Or try to execute restricted command

**Expected Result:**
- ✅ Permission error displayed
- ✅ Error message explains the issue
- ✅ No application crash
- ✅ Can retry with different path

---

## Integration Testing

### Test 5.1: New User Workflow

**Scenario:** First-time user configures GlyphX

**Steps:**
1. Delete config file: `~/.glyphx/config.json`
2. Launch application
3. Click Settings
4. Configure API key and preferred model
5. Adjust safety settings (increase output limit to 16 KB)
6. Save settings
7. Send test message to AI

**Expected Result:**
- ✅ Application works with no prior config
- ✅ Defaults are sensible
- ✅ Settings persist after save
- ✅ AI responds with configured settings
- ✅ Output respects 16 KB limit

---

### Test 5.2: Power User Workflow

**Scenario:** Advanced user wants maximum control

**Steps:**
1. Open Settings
2. Configure custom LLM endpoint
3. Set high output limit: 100 KB
4. Enable Agent mode by default
5. Disable context truncation
6. Save and test

**Expected Result:**
- ✅ All customizations work
- ✅ No artificial limitations
- ✅ Mode defaults to Agent on launch
- ✅ Large outputs display fully

---

### Test 5.3: Team/Enterprise Workflow

**Scenario:** Team lead configures safe defaults for team

**Steps:**
1. Configure conservative settings:
   - Output limit: 8 KB
   - Truncation: Enabled
   - Default mode: Chat
2. Save settings
3. Export config file
4. Distribute to team members
5. Team members launch with shared config

**Expected Result:**
- ✅ Config file is portable
- ✅ Team members get safe defaults
- ✅ Consistent behavior across team
- ✅ Users can still customize if needed

---

### Test 5.4: Cross-Platform Compatibility

**Steps:**
1. Configure settings on one platform (e.g., Windows)
2. Copy config file to another platform (e.g., Mac/Linux)
3. Launch application on second platform

**Expected Result:**
- ✅ Settings load correctly on different OS
- ✅ Paths are resolved correctly
- ✅ No OS-specific errors
- ✅ Consistent behavior across platforms

---

## Regression Testing

### Test 6.1: Existing Features Still Work

**Verify these features haven't regressed:**

- ✅ **Glyphs Tab:** Can create, edit, delete glyphs
- ✅ **History Tab:** Chat history persists and loads
- ✅ **Terminal:** Commands execute in terminal panel
- ✅ **AI Chat:** Basic Q&A works
- ✅ **File Operations:** Can read/write files (with safety checks)
- ✅ **Command History:** Up/down arrows cycle through history

---

### Test 6.2: Performance Validation

**Verify application is responsive:**

1. **Startup Time:** Application launches in < 3 seconds
2. **Settings Load:** Settings dialog opens instantly (< 500ms)
3. **Mode Switch:** Mode changes instantly (< 100ms)
4. **Command Validation:** No noticeable delay (<< 100ms)
5. **Output Truncation:** No lag with large outputs

**Expected Result:**
- ✅ All operations feel instant
- ✅ No UI freezing or stuttering
- ✅ Smooth user experience

---

### Test 6.3: Memory Usage

**Steps:**
1. Launch application
2. Perform typical operations (chat, settings, commands)
3. Monitor memory usage (Task Manager / Activity Monitor)
4. Use application for extended period (30+ minutes)

**Expected Result:**
- ✅ Memory usage stable (no memory leaks)
- ✅ No gradual performance degradation
- ✅ Application remains responsive over time

---

## Test Completion Checklist

### Pre-Release Verification

Before marking Step 5 complete, verify:

- [ ] All automated tests passing (100+ tests)
- [ ] All integration tests passing (13 tests)
- [ ] All performance benchmarks passing (14 tests)
- [ ] All manual tests in this guide completed
- [ ] No critical bugs found
- [ ] Documentation updated
- [ ] Settings persist correctly
- [ ] Safety features work as expected
- [ ] Error handling is graceful
- [ ] Cross-platform compatibility verified

---

## Known Limitations

Document any known issues or limitations:

1. **Tkinter on Some CI Systems:** Tkinter initialization may fail in headless environments (expected, GUI tests separated)
2. **Very Large Outputs:** Outputs > 1MB may cause temporary lag even with truncation disabled
3. **Windows Store Python:** Some Tkinter features may have limited functionality

---

## Reporting Issues

If you find issues during manual testing:

1. **Check Automated Tests:** Run `pytest glyphx/tests/` to see if issue is caught
2. **Document Steps:** Record exact steps to reproduce
3. **Capture Logs:** Include relevant log entries from `~/.glyphx/log.jsonl`
4. **Include Config:** Attach `config.json` if issue is settings-related
5. **Screenshot/Video:** Visual evidence is helpful for GUI issues

---

## Next Steps

After completing manual testing:

1. Create `STEP5_COMPLETION_SUMMARY.md` with results
2. Document any issues found and resolution
3. Update version number and changelog
4. Prepare for production release

---

**End of Manual Testing Guide**
