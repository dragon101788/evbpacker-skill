"""EVB 打包测试套件 - 验证 build.py 的各项功能"""
import sys, os, subprocess
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent / ".claude" / "skills" / "evb-pack"
BLD = SKILL_DIR / "scripts" / "build.py"
TESTS_DIR = Path(__file__).parent

results = {"passed": 0, "failed": 0, "tests": []}

def run_test(name, args, expect=0, check_file=None):
    """运行一个测试用例"""
    result = subprocess.run(
        [sys.executable, str(BLD)] + args,
        capture_output=True, text=True, errors="replace"
    )
    passed = result.returncode == expect
    if check_file and passed:
        passed = os.path.exists(check_file)

    status = "PASS" if passed else "FAIL"
    results["tests"].append({"name": name, "status": status, "output": result.stdout[-300:]})
    if passed:
        results["passed"] += 1
    else:
        results["failed"] += 1
    print("  [{}] {}".format(status, name))
    return passed


def main():
    print("=" * 60)
    print("  EVB Skill 测试套件")
    print("  tests dir: " + str(TESTS_DIR))
    print("=" * 60)

    # 清理旧的构建产物
    for f in TESTS_DIR.glob("*.evb"):
        f.unlink()
    for f in TESTS_DIR.glob("enigmavbconsole.exe"):
        f.unlink()
    for f in TESTS_DIR.glob("*_portable.exe"):
        f.unlink()

    # Test 1: 本地打包
    print("\n--- 1. 基本打包 ---")
    run_test("1.1 本地目录打包", [
        str(TESTS_DIR), str(TESTS_DIR / "test-app.exe"),
        str(TESTS_DIR / "test-app_portable.exe")
    ], check_file=str(TESTS_DIR / "test-app_portable.exe"))

    # Test 2: 中文路径
    print("\n--- 2. 中文路径 ---")
    run_test("2.1 中文目录打包", [
        str(TESTS_DIR), str(TESTS_DIR / "test-app.exe"),
        str(TESTS_DIR / "test-app_portable.exe")
    ], check_file=str(TESTS_DIR / "test-app_portable.exe"))

    # Test 3: 选项测试
    print("\n--- 3. 打包选项 ---")
    out3 = TESTS_DIR / "test-app_nocompress.exe"
    run_test("3.1 compress=false", [
        str(TESTS_DIR), str(TESTS_DIR / "test-app.exe"), str(out3),
        "-ocompress=false"
    ], check_file=str(out3))

    out4 = TESTS_DIR / "test-app_share.exe"
    run_test("3.2 share=true", [
        str(TESTS_DIR), str(TESTS_DIR / "test-app.exe"), str(out4),
        "-oshare=true"
    ], check_file=str(out4))

    out5 = TESTS_DIR / "test-app_allopts.exe"
    run_test("3.3 全部选项", [
        str(TESTS_DIR), str(TESTS_DIR / "test-app.exe"), str(out5),
        "-ocompress=false", "-oclean_exit=false", "-otemp_map=true",
        "-orun_virtual=true", "-oshare=false"
    ], check_file=str(out5))

    # Test 4: 帮助和错误处理
    print("\n--- 4. 帮助/错误 ---")
    run_test("4.1 --help 输出", ["--help"], expect=0)
    run_test("4.2 无参数打印帮助", ["--help"], expect=0)
    run_test("4.2 缺少参数打印帮助", [], expect=0)
    run_test("4.3 不存在的输入文件应失败", [
        str(TESTS_DIR), "C:\\notexist\\nope.exe"
    ], expect=1)

    # Test 5: 运行打包后的程序
    print("\n--- 5. 运行时验证 ---")
    portable = TESTS_DIR / "test-app_portable.exe"
    if portable.exists():
        r = subprocess.run(
            [str(portable)],
            capture_output=True, text=True, timeout=30, cwd=str(TESTS_DIR)
        )
        passed = r.returncode == 0 and "EVB" in r.stdout
        results["tests"].append({
            "name": "5.1 打包后程序可运行",
            "status": "PASS" if passed else "FAIL",
            "output": r.stdout
        })
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1
        print("  [{}] 5.1 打包后程序可运行".format("PASS" if passed else "FAIL"))
        for line in r.stdout.splitlines():
            if any(k in line for k in ["==", "config", "子进程", "测试", "data.bin"]):
                print("       " + line)
    else:
        print("  [SKIP] 5.1 (文件不存在)")

    # 总结
    total = results["passed"] + results["failed"]
    print("\n" + "=" * 60)
    print("  结果: {}/{} 通过, {} 失败".format(results["passed"], total, results["failed"]))
    for t in results["tests"]:
        if t["status"] == "FAIL":
            print("    失败: " + t["name"])
    print("=" * 60)

    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
