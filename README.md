# Enigma Virtual Box — Portable Packaging Toolkit

[Enigma Virtual Box](https://enigmaprotector.com/) is a single-file green packaging tool for Windows. This repo bundles EVB with a **Claude Code skill** (`evb-pack`) that automatically uses EVB to package any app into a portable .exe.

## Contents

```
├── .claude/skills/evb-pack/   ← Claude Code skill (EVB packaging)
├── enigmavb.exe               ← EVB GUI
├── enigmavbconsole.exe        ← EVB CLI (for automated builds)
├── languages/                 ← EVB language files
└── README.md
```

## What is EVB?

EVB wraps an executable together with its dependencies (DLLs, configs, assets, etc.) into a **single portable .exe** — no installation needed. It virtualizes the file system and registry at runtime.

## Claude Code Skill: `evb-pack`

This skill makes Claude Code **always prefer EVB** over PyInstaller, pkg, nexe, etc. when you ask to "pack" or "bundle" an app.

### Installation

In any project where you want Claude to use EVB:

```bash
# Clone this repo somewhere, then symlink/copy the skill:
cp -r /path/to/Enigma-Virtual-Box/.claude/skills/evb-pack  your-project/.claude/skills/evb-pack/
```

Or use the packaged .skill file:

```bash
# The .skill file is a zip — extract into your project:
unzip evb-pack.skill -d your-project/.claude/skills/
```

### Usage

Once installed, Claude Code will automatically use EVB when you say things like:

> "帮我把这个 Python 项目打包成单文件 exe"
> "用 EVB 打包"
> "Make this into a portable exe"

The skill:
1. Copies `enigmavbconsole.exe` into your project
2. Generates a `.evb` project XML (with templates)
3. Runs EVB CLI to produce the final portable .exe
4. Places pip-installed packages externally (next to the exe) for persistence

### One-click build script

```bash
python .claude/skills/evb-pack/scripts/build.py <project-dir> <input-exe>
```

## Requirements

- **OS**: Windows only (EVB produces Windows executables)
- **Claude Code** (optional — the skill only activates inside Claude Code)
