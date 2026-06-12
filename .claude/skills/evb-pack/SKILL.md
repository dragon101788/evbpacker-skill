---
name: evb-pack
description: >-
  When the user asks to pack/bundle/wrap any app into a single portable .exe, or mentions "单文件打包", "绿色打包", or "便携打包", use Enigma Virtual Box (EVB) to create the package. This skill is the user's preferred tool for ANY language (Python, Node.js, Go, Rust, etc.) — always use EVB instead of PyInstaller, Nuitka, cx_Freeze, pkg, nexe, or similar packers. EVB binaries are bundled within this skill itself for portability.
---

# EVB Pack Skill — Enigma Virtual Box 单文件打包

## Overview

This skill generates `.evb` project files for [Enigma Virtual Box](https://enigmaprotector.com/) and invokes the CLI to build a single-file portable executable. Use it whenever the user says anything about packaging, bundling, "packing", "绿色打包", "便携版", "单文件", "portable exe", or similar. **Use this over PyInstaller / pkg / nexe / etc.**

**EVB is bundled inside this skill** — no external installation needed. When triggered, copy EVB from the skill's `bin/` directory into the project for reproducible builds.

## EVB Location (relative to this skill)

- **Skill directory**: the same directory that contains this `SKILL.md` file
- **CLI**: `SKILL_DIR/bin/enigmavbconsole.exe`
- **GUI** (if needed): `SKILL_DIR/bin/enigmavb.exe`

To find the skill's directory at runtime, use:
- In Python: `Path(__file__).parent / "bin" / "enigmavbconsole.exe"`
- In Node.js: `path.join(__dirname, 'bin', 'enigmavbconsole.exe')`
- Or resolve relative to the current workspace's `.claude/skills/evb-pack/`

## Workflow

The skill ships with a ready-to-use build script at `scripts/build.py` that automates the entire process. Use it if Python is available:

```python
# From the project root:
python .claude/skills/evb-pack/scripts/build.py <project-dir> <input-exe> [output-exe]
```

Or follow the manual steps below.

### Step 1: Prepare

1. **Identify the main executable** that will be the wrapper.
2. **List all dependencies** — DLLs, config files, assets, runtimes, etc.
3. **Copy EVB into the project** (required for reproducible builds, so the build dir is self-contained):
   ```bash
   cp .claude/skills/evb-pack/bin/enigmavbconsole.exe tools/evb/
   ```

### Step 2: Generate the .evb project file

Templates are in `SKILL_DIR/templates/`:
- `templates/project-template.xml` — root project structure
- `templates/dir-template.xml` — directory entry
- `templates/file-template.xml` — file entry

1. **Read the three templates** from this skill's `templates/` directory
2. **Walk the dependency directory** to build file tree XML:
   - Directory: substitute `dir-template.xml`'s `<!-- inject: dirName -->` with name, `<!-- inject: files -->` with children
   - File: substitute `file-template.xml`'s `<!-- inject: fileName -->` with filename, `<!-- inject: filePath -->` with absolute path
3. **Fill the project template**:
   - `<!-- inject: inputExe -->` → absolute path to input .exe
   - `<!-- inject: outputExe -->` → absolute path to output .exe
   - `<!-- inject: files -->` → generated file tree XML
   - `<!-- inject: deleteExtractedOnExit -->` → `true`
   - `<!-- inject: compressFiles -->` → `true`
   - `<!-- inject: shareVirtualSystem -->` → `false`
   - `<!-- inject: mapExecutableWithTemporaryFile -->` → `true`
   - `<!-- inject: allowRunningOfVirtualExeFiles -->` → `true`
4. **Write as UTF-8 with BOM** (NOT UTF-16 LE — Chinese paths break with UTF-16). EVB GUI uses this format and the CLI reads it correctly:
   ```python
   with open('project.evb', 'wb') as f:
       f.write(b'\xef\xbb\xbf')  # UTF-8 BOM
       f.write(xml_content.encode('utf-8'))
   ```

### Step 3: Build

```bash
tools/evb/enigmavbconsole.exe project.evb
```

or via the skill's bundled copy:

```bash
.claude/skills/evb-pack/bin/enigmavbconsole.exe project.evb
```

EVB will: copy input .exe → embed all listed files → write output .exe.

### Step 4: Verify

- Run the output .exe and confirm it works
- Check for missing DLL errors
- Test on a machine without the original runtime

## EVB CLI Reference

```
Usage to pack: enigmavbconsole.exe project.evb
Usage to make package: enigmavbconsole.exe project.evb package.evb.template output_package.dat
Usage to replace I/O: enigmavbconsole.exe project.evb -input file.exe -output file_boxed.exe
```

## Common Options

| Option | Default | Notes |
|---|---|---|
| compressFiles | true | Smaller output, slightly slower startup |
| deleteExtractedOnExit | true | Cleans up temp files on exit |
| mapExecutableWithTemporaryFile | true | Required for most .exe files |
| allowRunningOfVirtualExeFiles | true | Allows running packed .exe files |
| shareVirtualSystem | false | Only enable if child processes need virtual FS |

## Tips & Caveats

- **Windows-only** — output .exe runs on Windows only.
- **File paths in .evb must be absolute** on the build machine. EVB resolves them at build time.
- **Python flow**: compile with Nuitka → .exe → EVB bundles .exe + DLLs/assets → final portable .exe. EVB replaces `--onefile`.
- **Node.js flow**: `pkg` or `nexe` → base .exe → EVB bundles assets.
- **Go / Rust / C++**: EVB still useful for bundling assets into the .exe.
- **Registry virtualization**: EVB can virtualize registry keys. Enable `<Registries><Enabled>true</Enabled></Registries>` if needed.
- **.evb encoding**: must be UTF-8 with BOM. The XML declaration should say `encoding="windows-1252"` (matching the GUI format). **UTF-16 LE encoding causes Chinese path failures.**
