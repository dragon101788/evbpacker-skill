/// test-config - 验证通过命令行解析配置参数的能力
fn main() {
    let args: Vec<String> = std::env::args().collect();
    println!("=== test-config ===");

    for arg in &args[1..] {
        if let Some(kv) = arg.split_once('=') {
            println!("  {} = {}", kv.0, kv.1);
        } else {
            println!("  flag: {}", arg);
        }
    }

    // 输出环境变量 PATH 前几个条目验证虚拟化
    let path = std::env::var("PATH").unwrap_or_default();
    let paths: Vec<&str> = path.split(';').collect();
    println!("  PATH 条目数: {}", paths.len());
    for p in paths.iter().take(3) {
        println!("    PATH[0]: {}", p);
    }
}
