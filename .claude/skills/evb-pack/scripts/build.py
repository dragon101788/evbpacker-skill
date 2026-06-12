"""Enigma Virtual Box (EVB) 单文件打包工具

功能:
  - 自动生成 .evb 项目文件并打包
  - 支持文件虚拟化、注册表虚拟化、选项配置
  - 支持特殊路径变量、文件操作类型、过滤器
  - 支持 Windows 中文路径（UTF-8 with BOM 编码）

用法:
  python build.py <项目目录> <主程序.exe> [输出文件.exe] [选项...]

示例:
  python build.py D:\\MyApp D:\\MyApp\\app.exe
  python build.py D:\\MyApp D:\\MyApp\\app.exe D:\\app_portable.exe
"""
import os, sys, shutil, subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Callable

SKILL_DIR = Path(__file__).parent.parent
EVB_CLI   = SKILL_DIR / "bin" / "enigmavbconsole.exe"


# ─── EVB 高级功能速查 ──────────────────────────────────────────────────────
#
# 【文件操作类型 Action】
#   0 = Virtual（仅内存虚拟，不写磁盘）—— 默认推荐，性能最好
#   1 = Extract Always（始终解压到临时目录）
#   2 = Extract if Not Present（目标文件不存在时才解压）
#
# 【文件夹变量】—— 用于 <Name> 和虚拟路径映射
#   %DEFAULT FOLDER%          = exe 所在目录
#   %SYSTEM FOLDER%           = C:\Windows\System32
#   %WINDOWS FOLDER%          = C:\Windows
#   %TEMP FOLDER%             = 用户临时目录
#   %ApplicationData FOLDER%  = %APPDATA% (Roaming)
#   %Local, ApplicationData FOLDER% = %LOCALAPPDATA%
#   %Program Files FOLDER%    = %ProgramFiles%
#   %My Documents FOLDER%     = Documents
#   %AllUsers, ApplicationData FOLDER% = ProgramData
#
# 【文件 Type 类型】
#   2 = 文件
#   3 = 文件夹
#
# 【注册表操作类型 Registry Type】
#   1 = 键（Key），可包含子项
#   0 = REG_SZ 值
#   3 = REG_BINARY 值
#
# 【EVB 选项】
#   compressFiles  : 启用压缩（减小体积，但首次启动稍慢）
#   deleteExtractedOnExit : 退出时清理临时解压文件
#   mapExecutableWithTemporaryFile : 虚拟 exe/dll 用临时文件映射（推荐开启）
#   allowRunningOfVirtualExeFiles  : 允许执行虚拟 exe
#   shareVirtualSystem : 共享虚拟文件系统给子进程
#
# 📌 .evb 编码: 必须用 UTF-8 with BOM，XML 声明 encoding="windows-1252"
#   这是 GUI 生成的格式，也只有这个格式能正确处理中文路径。
#   不要用 UTF-16 LE！中文路径会报 "File does not exist"。
# ──────────────────────────────────────────────────────────────────────────────

# ─── 数据类型 ──────────────────────────────────────────────────────────────
@dataclass
class EvbOptions:
    """打包选项"""
    compress_files: bool = True
    delete_extracted_on_exit: bool = True
    share_virtual_system: bool = False
    map_executable_with_temp: bool = True
    allow_running_virtual_exe: bool = True
    hide_files_dialogs: bool = False

@dataclass
class RegistryKey:
    """注册表键"""
    name: str
    type: int = 1           # 1=key, 0=REG_SZ, 3=REG_BINARY
    virtual: bool = True
    value: str = ""
    value_type: int = 0     # 0=REG_SZ
    children: list = field(default_factory=list)

@dataclass
class FileEntry:
    """文件条目"""
    source: Path              # 源文件绝对路径
    dest_name: str = ""       # 虚拟目录中的文件名（默认用原名）
    dest_folder: str = "%DEFAULT FOLDER%"  # 目标虚拟文件夹
    action: int = 0           # 0=虚拟, 1=始终解压, 2=不存在时解压
    overwrite_datetime: bool = False
    overwrite_attributes: bool = False
    pass_commandline: bool = False
    activex: bool = False
    activex_install: bool = False

@dataclass
class EvbProject:
    """EVB 项目配置"""
    input_exe: Path
    output_exe: Path
    files: list = field(default_factory=list)          # 扁平文件列表（含目录结构）
    registry: list = field(default_factory=list)       # 注册表键列表
    registries_enabled: bool = False                   # 启用注册表虚拟化
    packaging_enabled: bool = False                    # 启用 Package Builder
    options: EvbOptions = field(default_factory=EvbOptions)
    file_filter: Optional[Callable] = None             # 自定义过滤器


# ─── 核心构建函数 ──────────────────────────────────────────────────────────

def _escape(xml_text: str) -> str:
    """转义 XML 特殊字符"""
    return (xml_text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;"))


def to_evb_xml(proj: EvbProject) -> str:
    """将 EvbProject 编译为 .evb XML 字符串"""

    def _file_entry(fe: FileEntry) -> str:
        src_path = str(fe.source.resolve())
        name = fe.dest_name or fe.source.name
        return f"""          <File>
            <Type>2</Type>
            <Name>{_escape(name)}</Name>
            <File>{_escape(src_path)}</File>
            <ActiveX>{'True' if fe.activex else 'False'}</ActiveX>
            <ActiveXInstall>{'True' if fe.activex_install else 'False'}</ActiveXInstall>
            <Action>{fe.action}</Action>
            <OverwriteDateTime>{'True' if fe.overwrite_datetime else 'False'}</OverwriteDateTime>
            <OverwriteAttributes>{'True' if fe.overwrite_attributes else 'False'}</OverwriteAttributes>
            <PassCommandLine>{'True' if fe.pass_commandline else 'False'}</PassCommandLine>
          </File>"""

    def _registry_xml(key: RegistryKey, indent: int = 8) -> str:
        """生成注册表 XML"""
        pad = " " * indent
        if key.type == 1:  # 键
            children = "".join(_registry_xml(c, indent + 2) for c in key.children)
            return f'{pad}<Registry><Type>1</Type><Virtual>{"True" if key.virtual else "False"}</Virtual><Name>{_escape(key.name)}</Name><ValueType>0</ValueType><Value/><Registries>{children}{pad}</Registries></Registry>\n'
        else:  # 值
            return f'{pad}<Registry><Type>{key.type}</Type><Virtual>{"True" if key.virtual else "False"}</Virtual><Name>{_escape(key.name)}</Name><ValueType>{key.value_type}</ValueType><Value>{_escape(key.value)}</Value><Registries/></Registry>\n'

    # ── 文件树构建 ──
    # EVB 的文件结构是双层 <Files>: 外层的 Enabled/DeleteExtractedOnExit/CompressFiles
    # 内层是 %DEFAULT FOLDER% 根目录
    file_entries = "\n".join(_file_entry(fe) for fe in proj.files)

    # ── 注册表 ──
    reg_entries = "".join(_registry_xml(k) for k in proj.registry)

    # ── 选项 ──
    opts = proj.options

    # ── 构建 XML ──
    lines = [
        '<?xml version="1.0" encoding="windows-1252"?>',
        '<>',
        f'  <InputFile>{_escape(str(proj.input_exe.resolve()))}</InputFile>',
        f'  <OutputFile>{_escape(str(proj.output_exe.resolve()))}</OutputFile>',
        '  <Files>',
        f'    <Enabled>True</Enabled>',
        f'    <DeleteExtractedOnExit>{"True" if opts.delete_extracted_on_exit else "False"}</DeleteExtractedOnExit>',
        f'    <CompressFiles>{"True" if opts.compress_files else "False"}</CompressFiles>',
        '    <Files>',
        '      <File>',
        '        <Type>3</Type>',
        '        <Name>%DEFAULT FOLDER%</Name>',
        '        <Action>0</Action>',
        '        <OverwriteDateTime>False</OverwriteDateTime>',
        '        <OverwriteAttributes>False</OverwriteAttributes>',
        '        <Files>',
        file_entries,
        '        </Files>',
        '      </File>',
        '    </Files>',
        '  </Files>',
        '  <Registries>',
        f'    <Enabled>{"True" if proj.registries_enabled else "False"}</Enabled>',
        '    <Registries>' if reg_entries or proj.registries_enabled else '',
    ]
    if reg_entries:
        lines.append(reg_entries)
    if proj.registries_enabled or reg_entries:
        lines.append('    </Registries>')
    lines += [
        '  </Registries>',
        '  <Packaging>',
        f'    <Enabled>{"True" if proj.packaging_enabled else "False"}</Enabled>',
        '  </Packaging>',
        '  <Options>',
        f'    <ShareVirtualSystem>{"True" if opts.share_virtual_system else "False"}</ShareVirtualSystem>',
        f'    <MapExecutableWithTemporaryFile>{"True" if opts.map_executable_with_temp else "False"}</MapExecutableWithTemporaryFile>',
        f'    <AllowRunningOfVirtualExeFiles>{"True" if opts.allow_running_virtual_exe else "False"}</AllowRunningOfVirtualExeFiles>',
        '  </Options>',
        '</>',
    ]

    return "\r\n".join(lines)


def build_evb(project_dir, input_exe, output_exe=None, pack_dir=None,
              options: EvbOptions = None, skip_names=None,
              file_filter=None):
    """生成 .evb 项目文件并调用 EVB 打包。

    参数:
        project_dir: 输出目录（.evb 和 enigmavbconsole.exe 放这里）
        input_exe:   要包裹的主执行文件
        output_exe:  输出的便携版 exe 路径
        pack_dir:    需要打包的目录（默认 = input_exe 所在目录）
        options:     EvbOptions 实例，自定义打包选项
        skip_names:  跳过不打包的文件名集合
        file_filter: 自定义文件过滤函数 fn(filepath) -> bool
    """
    project_dir = Path(project_dir).resolve()
    input_exe   = Path(input_exe).resolve()
    pack_dir    = Path(pack_dir).resolve() if pack_dir else input_exe.parent
    skip_names  = skip_names or {"enigmavbconsole.exe", "project.evb", ".gitkeep"}
    options     = options or EvbOptions()

    if not input_exe.exists():
        raise FileNotFoundError(f"主程序不存在: {input_exe}")

    if not EVB_CLI.exists():
        raise FileNotFoundError(f"EVB CLI 不存在: {EVB_CLI}")

    if output_exe is None:
        output_exe = project_dir / f"{input_exe.stem}_boxed.exe"
    else:
        output_exe = Path(output_exe).resolve()

    # ── 扫描文件 ──
    print(f">> 扫描: {pack_dir}")
    proj = EvbProject(
        input_exe=input_exe,
        output_exe=output_exe,
        options=options,
    )

    for name in sorted(os.listdir(pack_dir)):
        fp = pack_dir / name
        if not fp.is_file() or name in skip_names:
            continue
        if file_filter and not file_filter(fp):
            continue
        # 主程序自动放到根虚拟目录
        fe = FileEntry(source=fp)
        proj.files.append(fe)

    print(f"   找到 {len(proj.files)} 个文件")

    # ── 生成 XML ──
    xml = to_evb_xml(proj)

    # ── 写入 .evb（UTF-8 with BOM，这是 EVB 读取中文路径唯一正确的方式）──
    project_dir.mkdir(parents=True, exist_ok=True)
    evb_file = project_dir / "project.evb"
    with open(evb_file, "wb") as f:
        f.write(b'\xef\xbb\xbf')   # UTF-8 BOM
        f.write(xml.encode('utf-8'))
    print(f">> .evb 文件: {evb_file}")
    # 复制 EVB CLI
    evb_local = project_dir / "enigmavbconsole.exe"
    shutil.copy2(EVB_CLI, evb_local)

    # 运行 EVB（用 subprocess 传参数列表，不走 cmd.exe）
    print(f">> 运行 EVB 打包...")
    result = subprocess.run(
        [str(evb_local), "project.evb"],
        cwd=str(project_dir),
        capture_output=True, text=True,
        errors="replace"
    )
    if result.stdout:
        for line in result.stdout.splitlines():
            if any(kw in line for kw in ['Starting', 'Compress', 'Build', 'Error', 'success', 'saved']):
                print(f"  {line.strip()}")
    if result.stderr:
        for line in result.stderr.splitlines():
            print(f"  ERR: {line.strip()}", file=sys.stderr)

    if result.returncode != 0:
        raise RuntimeError(f"EVB 打包失败 (exit code {result.returncode})")

    if output_exe.exists():
        mb = output_exe.stat().st_size / (1024*1024)
        print(f"\n== 成功: {output_exe} ({mb:.1f} MB)")
    else:
        raise RuntimeError("打包完成后未找到输出文件")

    return output_exe


# ─── 便捷辅助函数 ──────────────────────────────────────────────────────────

def create_registry_from_file(reg_path: str) -> list:
    """从 .reg 文件解析注册表条目（基本解析）。"""
    keys = []
    reg_path = Path(reg_path)
    if not reg_path.exists():
        print(f"⚠  .reg 文件不存在: {reg_path}")
        return keys

    with open(reg_path, encoding='utf-16-le', errors='replace') as f:
        content = f.read()

    current_key = None
    for line in content.splitlines():
        line = line.strip()
        if line.startswith('[') and line.endswith(']'):
            key_path = line[1:-1]
            parts = key_path.split('\\')
            # 简化：只取最末键名
            current_key = RegistryKey(name=parts[-1], type=1, virtual=True)
            keys.append(current_key)
        elif '=' in line and current_key:
            name, value = line.split('=', 1)
            name = name.strip().strip('"')
            current_key.children.append(
                RegistryKey(name=name, type=0, virtual=True,
                           value=value.strip().strip('"'))
            )
    return keys


def set_option(key: str, value: str) -> EvbOptions:
    """通过命令行字符串设置选项。支持链式调用。

    参数:
        key: 选项名，如 compress, hide_files, temp_map, run_virtual, share, clean_exit
        value: "true"/"false" 或 "yes"/"no"
    """
    opts = EvbOptions()
    v = value.lower() in ("true", "yes", "1")
    mapping = {
        "compress": "compress_files",
        "hide_files": "hide_files_dialogs",
        "temp_map": "map_executable_with_temp",
        "run_virtual": "allow_running_virtual_exe",
        "share": "share_virtual_system",
        "clean_exit": "delete_extracted_on_exit",
    }
    attr = mapping.get(key.lower())
    if attr and hasattr(opts, attr):
        setattr(opts, attr, v)
    else:
        valid = ", ".join(mapping.keys())
        print(f"⚠  未知选项 '{key}'，有效选项: {valid}")
    return opts


# ─── 命令行入口 ────────────────────────────────────────────────────────────

def _print_options_help():
    """打印 EVB 选项帮助"""
    print()
    print("EVB 选项 (通过 -o key=value 设置):")
    print("  compress=true|false        启用压缩 (默认 true)")
    print("  clean_exit=true|false      退出清理临时文件 (默认 true)")
    print("  temp_map=true|false        临时文件映射 exe/dll (默认 true)")
    print("  run_virtual=true|false     允许执行虚拟 exe (默认 true)")
    print("  share=true|false           共享虚拟系统给子进程 (默认 false)")
    print("  hide_files=true|false      隐藏文件防对话框枚举 (默认 false)")
    print()
    print("特殊文件夹变量 (用于虚拟路径 <Name>):")
    print("  %%DEFAULT FOLDER%%         = exe 所在目录")
    print("  %%SYSTEM FOLDER%%          = C:\\Windows\\System32")
    print("  %%WINDOWS FOLDER%%         = C:\\Windows")
    print("  %%TEMP FOLDER%%            = 用户临时目录")
    print("  %%ApplicationData FOLDER%% = %%APPDATA%%")
    print("  %%Program Files FOLDER%%   = %%ProgramFiles%%")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help", "/?"):
        print(__doc__)
        _print_options_help()
        sys.exit(0)

    project_dir = Path(sys.argv[1])
    input_exe   = Path(sys.argv[2])
    output_exe  = Path(sys.argv[3]) if len(sys.argv) >= 4 else None

    # 解析选项
    opts = EvbOptions()
    for arg in sys.argv[3:]:
        if arg.startswith("-o"):
            parts = arg[2:].split("=", 1)
            if len(parts) == 2:
                opts = set_option(parts[0].strip(), parts[1].strip())

    pack_dir = input_exe.parent
    try:
        out = build_evb(project_dir, input_exe, output_exe,
                        pack_dir=pack_dir, options=opts)
    except Exception as e:
        print(f"\n== 错误: {e}")
        sys.exit(1)
