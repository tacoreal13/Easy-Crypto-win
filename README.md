# Miner Rig Control (Windows)

GUI control panel for GPU mining (Rigel) and/or CPU mining (XMRig) via unMineable,
with a slider to adjust GPU power limit on the fly.

## First-time setup on a new machine

1. Install Python 3 from https://python.org if it's not already installed
   (check "Add python.exe to PATH" during install; tkinter is bundled by default).
2. Clone or download this repo onto the machine.
3. Right-click `install.ps1` → **Run with PowerShell**.
   - If Windows blocks it, open PowerShell as Administrator once and run:
     `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
4. Choose GPU only / CPU only / Both when prompted.
5. Enter your BTC payout address and a worker name for this machine when asked.
6. Run the control panel:
   ```
   python miner_control.py
   ```
   You'll get one UAC prompt on launch (needed for GPU power-limit control) —
   after that, no more prompts, even when you move the slider.

## What install.ps1 does

- Downloads the latest Windows release of Rigel and/or XMRig straight from
  their official GitHub release pages (no bundled binaries in the repo).
- Creates `config.json` from `config.example.json` with your wallet/worker
  name filled in.

## Re-running on other machines

Same repo, same steps — clone it, run `install.ps1`, pick what this
particular machine should mine with (e.g. GPU only on your gaming rig, CPU
only on a laptop, both on your main desktop). Each machine gets its own
`config.json` and its own downloaded binaries in `bin\`, so nothing conflicts
between machines even though they're the same repo.

## Notes

- `config.json` and `bin\` are git-ignored (see `.gitignore`) so your wallet
  address and large binaries never get committed. Only the templates/scripts
  belong in the repo.
- If you ever want to update to a newer Rigel/XMRig version, just delete the
  `bin\rigel` or `bin\xmrig` folder and re-run `install.ps1` — it always
  pulls whatever is currently the latest release.
- Miner output shows up in its own console window (titled "Rigel-GPU-Miner"
  or "XMRig-CPU-Miner"), not inside the control panel itself — the panel
  just starts/stops/restarts them.
