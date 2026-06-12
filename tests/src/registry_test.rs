/// test-registry - 验证注册表虚拟化功能
fn main() {
    println!("=== 注册表虚拟化测试 ===");

    // Test: 读取虚拟化的注册表键
    // 注意: EVB 注册表虚拟化运行时生效，这里仅验证 exe 能跑
    println!("test-registry.exe 已启动");

    // 列出所有环境变量（用于诊断）
    for (k, v) in std::env::vars() {
        if k.starts_with("EVB") || k.starts_with("ENIGMA") || k.contains("VIRTUAL") {
            println!("  {} = {}", k, v);
        }
    }

    // 检测是否运行于虚拟环境中
    let exe = std::env::current_exe().unwrap();
    let temp = std::env::temp_dir();
    println!("exe: {}", exe.display());
    println!("temp: {}", temp.display());
    println!("temp 中是否有 evb 临时文件: {}", {
        let entries = std::fs::read_dir(&temp).ok();
        match entries {
            Some(entries) => entries.filter_map(|e| e.ok())
                .any(|e| e.file_name().to_string_lossy().contains("evb")),
            None => false,
        }
    });
}
